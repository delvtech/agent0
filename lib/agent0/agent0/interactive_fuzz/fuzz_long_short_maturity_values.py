"""Script to verify that longs and shorts which are closed at maturity supply the correct amounts."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from typing import NamedTuple, Sequence

import numpy as np
from fixedpointmath import FixedPoint
from hyperlogs import ExtendedJSONEncoder
from hypertypes.fixedpoint_types import CheckpointFP

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.hyperdrive.interactive.chain import LocalChain
from agent0.hyperdrive.interactive.event_types import CloseLong, CloseShort, OpenLong, OpenShort
from agent0.interactive_fuzz.helpers import generate_trade_list, open_random_trades, setup_fuzz

# main script has a lot of stuff going on
# pylint: disable=too-many-locals


def main(argv: Sequence[str] | None = None):
    """Primary entrypoint.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    # Setup the experiment
    parsed_args = parse_arguments(argv)
    fuzz_long_short_maturity_values(*parsed_args)


def fuzz_long_short_maturity_values(num_trades: int, chain_config: LocalChain.Config | None = None):
    """Does fuzzy invariant checks on closing longs and shorts past maturity.

    Parameters
    ----------
    num_trades: int
        Number of trades to perform during the fuzz tests.
    chain_config: LocalChain.Config, optional
        Configuration options for the local chain.

    Raises
    ------
    AssertionError
        If the invariant checks fail during the tests an error will be raised.
    """

    log_filename = ".logging/fuzz_long_short_maturity_values.log"
    # Parameters for local chain initialization, defines defaults in constructor
    # set a large block time so i can manually control when it ticks
    # TODO: set block time really high after contracts deployed:
    # chain_config = LocalChain.Config(block_time=1_000_000)
    chain, random_seed, rng, interactive_hyperdrive = setup_fuzz(
        log_filename, chain_config=chain_config
    )  # pylint: disable=unused-variable
    signer = interactive_hyperdrive.init_agent(eth=FixedPoint(100))

    # Generate a list of agents that execute random trades
    trade_list = generate_trade_list(num_trades, rng, interactive_hyperdrive)

    # Open some trades
    trade_events = open_random_trades(trade_list, chain, rng, interactive_hyperdrive, advance_time=False)

    # Starting checkpoint is automatically created by sending transactions
    starting_checkpoint = interactive_hyperdrive.hyperdrive_interface.current_pool_state.checkpoint

    # Advance the time to a little more than the position duration
    position_duration = interactive_hyperdrive.hyperdrive_interface.pool_config.position_duration
    chain.advance_time(position_duration + 30, create_checkpoints=False)

    # Create a checkpoint
    interactive_hyperdrive.hyperdrive_interface.create_checkpoint(signer.agent)

    # Get the maturity checkpoint for the previously created checkpoint
    maturity_checkpoint = interactive_hyperdrive.hyperdrive_interface.current_pool_state.checkpoint

    # Advance time again
    extra_time = int(np.floor(rng.uniform(low=0, high=position_duration)))
    chain.advance_time(extra_time, create_checkpoints=False)

    # Close the trades one at a time, check invariants
    for index, (agent, trade) in enumerate(trade_events):
        logging.info("index=%s\n", index)
        if isinstance(trade, OpenLong):
            close_event = agent.close_long(maturity_time=trade.maturity_time, bonds=trade.bond_amount)
        elif isinstance(trade, OpenShort):
            close_event = agent.close_short(maturity_time=trade.maturity_time, bonds=trade.bond_amount)
        else:
            assert False

        if invariant_check_failed(
            trade, close_event, starting_checkpoint, maturity_checkpoint, random_seed, interactive_hyperdrive, chain
        ):
            chain.cleanup()
            raise AssertionError(f"Testing failed; see logs in {log_filename}")

    chain.cleanup()


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    num_trades: int
    chain_config: LocalChain.Config


def namespace_to_args(namespace: argparse.Namespace) -> Args:
    """Converts argprase.Namespace to Args.

    Arguments
    ---------
    namespace: argparse.Namespace
        Object for storing arg attributes.

    Returns
    -------
    Args
        Formatted arguments
    """
    # TODO: replace this func with Args(**namespace)?
    return Args(num_trades=namespace.num_trades, chain_config=LocalChain.Config(chain_port=namespace.chain_port))


def parse_arguments(argv: Sequence[str] | None = None) -> Args:
    """Parses input arguments.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.

    Returns
    -------
    Args
        Formatted arguments
    """
    parser = argparse.ArgumentParser(description="Runs a loop to check Hyperdrive invariants at each block.")
    parser.add_argument(
        "--num_trades",
        type=int,
        default=5,
        help="The number of random trades to open.",
    )
    parser.add_argument(
        "--chain_port",
        type=int,
        default=10000,
        help="The number of random trades to open.",
    )
    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv
    return namespace_to_args(parser.parse_args())


def invariant_check_failed(
    open_trade_event: OpenLong | OpenShort,
    close_trade_event: CloseLong | CloseShort,
    starting_checkpoint: CheckpointFP,
    maturity_checkpoint: CheckpointFP,
    random_seed: int,
    interactive_hyperdrive: InteractiveHyperdrive,
    chain: LocalChain,
) -> bool:
    """Check the pool state invariants.

    Arguments
    ---------
    initial_vault_shares: FixedPoint
        The number of vault shares owned by the Hyperdrive pool when it was deployed.
    random_seed: int
        Random seed used to run the experiment.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    chain: LocalChain
        An instantiated LocalChain object.

    Returns
    -------
    bool
        If true, at least one of the checks failed.
    """
    failed = False
    pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()

    if isinstance(open_trade_event, OpenLong) and isinstance(close_trade_event, CloseLong):
        # 0.05 would be a 5% fee.
        flat_fee_percent = interactive_hyperdrive.hyperdrive_interface.pool_config.fees.flat

        # assert with trade values
        # base out should be equal to bonds in minus the flat fee.
        actual_base_amount = close_trade_event.base_amount
        expected_base_amount_from_event = (
            close_trade_event.bond_amount - close_trade_event.bond_amount * flat_fee_percent
        )
        # assert with event values
        if actual_base_amount != expected_base_amount_from_event:
            logging.critical(
                "actual_base_amount=%s != expected_base_amount_from_close_event=%s, difference_in_wei=%s",
                actual_base_amount,
                expected_base_amount_from_event,
                abs(actual_base_amount.scaled_value - expected_base_amount_from_event.scaled_value),
            )
            failed = True

        expected_base_amount_from_trade = open_trade_event.bond_amount - open_trade_event.bond_amount * flat_fee_percent
        if actual_base_amount != expected_base_amount_from_trade:
            logging.critical(
                "actual_base_amount=%s != expected_base_amount_from_trade=%s, difference_in_wei=%s",
                actual_base_amount,
                expected_base_amount_from_trade,
                abs(actual_base_amount.scaled_value - expected_base_amount_from_trade.scaled_value),
            )
            failed = True

    elif isinstance(open_trade_event, OpenShort) and isinstance(close_trade_event, CloseShort):
        # get the share prices
        open_share_price = starting_checkpoint.share_price
        closing_share_price = maturity_checkpoint.share_price

        # interested accrued in shares = (c1 / c0 + flat_fee) * dy - c1 * dz
        flat_fee_percent = interactive_hyperdrive.hyperdrive_interface.pool_config.fees.flat

        # get the share amount, c1 * dz part of the equation.
        share_reserves_delta = open_trade_event.bond_amount
        flat_fee = open_trade_event.bond_amount * flat_fee_percent
        share_reserves_delta_plus_flat_fee = share_reserves_delta + flat_fee

        # get the final interest accrued
        interest_accrued = (
            open_trade_event.bond_amount * (closing_share_price / open_share_price + flat_fee_percent)
            - share_reserves_delta_plus_flat_fee
        )

        actual_base_amount = close_trade_event.base_amount
        if actual_base_amount != interest_accrued:
            logging.critical(
                "actual_base_amount=%s != interest_accrued=%s, difference_in_wei=%s",
                actual_base_amount,
                interest_accrued,
                abs(actual_base_amount.scaled_value - interest_accrued.scaled_value),
            )
            failed = True
    else:
        raise ValueError("Invalid types for open/close trade events")

    if failed:
        dump_state_dir = chain.save_state(save_prefix="fuzz_long_short_maturity_values")
        logging.info(
            "random_seed = %s\npool_config = %s\n\npool_info = %s\n\nlatest_checkpoint = %s\n\nadditional_info = %s",
            random_seed,
            json.dumps(asdict(pool_state.pool_config), indent=2, cls=ExtendedJSONEncoder),
            json.dumps(asdict(pool_state.pool_info), indent=2, cls=ExtendedJSONEncoder),
            json.dumps(asdict(pool_state.checkpoint), indent=2, cls=ExtendedJSONEncoder),
            json.dumps(
                {
                    "dump_state_dir": dump_state_dir,
                    "hyperdrive_address": interactive_hyperdrive.hyperdrive_interface.hyperdrive_contract.address,
                    "base_token_address": interactive_hyperdrive.hyperdrive_interface.base_token_contract.address,
                    "spot_price": interactive_hyperdrive.hyperdrive_interface.calc_spot_price(pool_state),
                    "fixed_rate": interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate(pool_state),
                    "variable_rate": pool_state.variable_rate,
                    "vault_shares": pool_state.vault_shares,
                },
                indent=2,
                cls=ExtendedJSONEncoder,
            ),
        )

    return failed


if __name__ == "__main__":
    main()

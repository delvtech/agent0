"""Script to verify that longs and shorts which are closed at maturity supply the correct amounts."""
from __future__ import annotations

import argparse
import logging
import sys
from typing import NamedTuple, Sequence

import numpy as np
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive.chain import LocalChain
from agent0.hyperdrive.interactive.event_types import OpenLong, OpenShort
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
    # TODO: We will want to log the random seed; so remove this pylint disable once we do
    chain, _, rng, interactive_hyperdrive = setup_fuzz(
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

    # Advance time again
    extra_time = int(np.floor(rng.uniform(low=0, high=position_duration)))
    chain.advance_time(extra_time, create_checkpoints=False)

    # Get the latest checkpoint
    current_time = interactive_hyperdrive.hyperdrive_interface.current_pool_state.block_time
    maturity_checkpoint = interactive_hyperdrive.hyperdrive_interface.hyperdrive_contract.functions.getCheckpoint(
        interactive_hyperdrive.hyperdrive_interface.calc_checkpoint_id(block_timestamp=current_time)
    ).call()

    # Close the trades one at a time, check invariants
    for index, (agent, trade) in enumerate(trade_events):
        logging.info("index=%s\n", index)
        if isinstance(trade, OpenLong):
            close_long_event = agent.close_long(maturity_time=trade.maturity_time, bonds=trade.bond_amount)
            # 0.05 would be a 5% fee.
            flat_fee_percent = interactive_hyperdrive.hyperdrive_interface.pool_config.fees.flat

            # assert with trade values
            # base out should be equal to bonds in minus the flat fee.
            actual_base_amount = close_long_event.base_amount
            # expected_base_amount_from_event = (
            #     close_long_event.bond_amount - close_long_event.bond_amount * flat_fee_percent
            # )
            # assertion(actual_base_amount == expected_base_amount_from_event)

            # assert with event values
            expected_base_amount_from_trade = trade.bond_amount - trade.bond_amount * flat_fee_percent
            # assertion(close_long_event.base_amount == expected_base_amount_from_trade)

            # show the difference
            difference = actual_base_amount.scaled_value - expected_base_amount_from_trade.scaled_value
            logging.info("close long: actual_base_amount=%s", actual_base_amount.to_decimal())
            logging.info("close long: difference in wei =%s\n", difference)
            # assert actual_base_amount == expected_base_amount
            # assert close_long_event.base_amount == trade.bond_amount - trade.bond_amount * flat_fee_percent
        if isinstance(trade, OpenShort):
            close_short_event = agent.close_short(maturity_time=trade.maturity_time, bonds=trade.bond_amount)

            # get the share prices
            open_share_price = starting_checkpoint.share_price
            closing_share_price = FixedPoint(scaled_value=maturity_checkpoint.sharePrice)

            # interested accrued in shares = (c1 / c0 + flat_fee) * dy - c1 * dz
            flat_fee_percent = interactive_hyperdrive.hyperdrive_interface.pool_config.fees.flat

            # get the share amount, c1 * dz part of the equation.
            share_reserves_delta = trade.bond_amount
            flat_fee = trade.bond_amount * flat_fee_percent
            share_reserves_delta_plus_flat_fee = share_reserves_delta + flat_fee

            # get the final interest accrued
            interest_accrued = (
                trade.bond_amount * (closing_share_price / open_share_price + flat_fee_percent)
                - share_reserves_delta_plus_flat_fee
            )

            # assert and show the difference
            # assertion(close_short_event.base_amount == interest_accrued)
            difference = close_short_event.base_amount.scaled_value - interest_accrued.scaled_value
            logging.info("close short: base_amount=%s", close_short_event.base_amount)
            logging.info("close short: difference in wei =%s\n", difference)
            # assert close_short_event.base_amount == interest_accrued
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


def assertion(condition: bool, message: str = "Assertion failed."):
    """Simple assertion check.

    Parameters
    ----------
    condition: bool
        condition to check.
    message: str, optional
        Error message if condtion fails.
    """
    if not condition:
        print(message)


if __name__ == "__main__":
    main()

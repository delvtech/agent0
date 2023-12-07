"""Script for fuzzing profit values on immediately opening & closing a long or short."""
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
from numpy.random._generator import Generator

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.interactive_fuzz.helpers import setup_fuzz


def main(argv: Sequence[str] | None = None):
    """Primary entrypoint.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    parsed_args = parse_arguments(argv)
    fuzz_profit_check(*parsed_args)


def fuzz_profit_check(chain_config: LocalChain.Config | None = None):
    """Fuzzes invariant checks for profit from long and short positions.

    Parameters
    ----------
    chain_config: LocalChain.Config, optional
        Configuration options for the local chain.

    Raises
    ------
    AssertionError
        If the invariant checks fail during the tests an error will be raised.
    """

    # Setup the environment
    log_filename = ".logging/fuzz_profit_check.log"
    chain, random_seed, rng, interactive_hyperdrive = setup_fuzz(log_filename, chain_config)

    # Get a random trade amount
    trade_amount = FixedPoint(
        scaled_value=int(
            np.floor(
                rng.uniform(
                    low=interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount.scaled_value,
                    high=int(1e23),
                )
            )
        )
    )

    # Generate funded trading agent
    long_agent = interactive_hyperdrive.init_agent(base=trade_amount, eth=FixedPoint(100), name="alice")
    # Open a long
    open_long_event = long_agent.open_long(base=trade_amount)
    # Let some time pass, as long as it is less than a checkpoint
    # This means that the open & close will get pro-rated to the same spot
    advance_time_before_checkpoint(chain, rng, interactive_hyperdrive)
    # Close the long
    close_long_event = long_agent.close_long(
        maturity_time=open_long_event.maturity_time, bonds=open_long_event.bond_amount
    )

    # Generate funded trading agent
    short_agent = interactive_hyperdrive.init_agent(base=trade_amount, eth=FixedPoint(100), name="bob")
    # Open a short
    # Set trade amount to the new wallet position (due to losing money from the previous open/close)
    trade_amount = short_agent.wallet.balance.amount
    open_short_event = short_agent.open_short(bonds=trade_amount)
    # Let some time pass, as long as it is less than a checkpoint
    # This means that the open & close will get pro-rated to the same spot
    advance_time_before_checkpoint(chain, rng, interactive_hyperdrive)
    # Close the short
    close_short_event = short_agent.close_short(
        maturity_time=open_short_event.maturity_time, bonds=open_short_event.bond_amount
    )

    # Ensure that the prior trades did not result in a profit
    check_data = {
        "trade_amount": trade_amount,
        "long_agent": long_agent,
        "short_agent": short_agent,
        "long_events": {"open": open_long_event, "close": close_long_event},
        "short_events": {"open": open_short_event, "close": close_short_event},
    }
    if invariant_check_failed(check_data, random_seed, interactive_hyperdrive, chain):
        chain.cleanup()
        raise AssertionError(f"Testing failed; see logs in {log_filename}")
    chain.cleanup()


def advance_time_before_checkpoint(
    chain: LocalChain, rng: Generator, interactive_hyperdrive: InteractiveHyperdrive
) -> None:
    """Advance time on the chain a random amount that is less than the next checkpoint time.

    Arguments
    ---------
    chain: LocalChain
        An instantiated LocalChain.
    rng: `Generator <https://numpy.org/doc/stable/reference/random/generator.html>`_
        The numpy Generator provides access to a wide range of distributions, and stores the random state.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    """
    current_block_time = interactive_hyperdrive.hyperdrive_interface.get_block_timestamp(
        interactive_hyperdrive.hyperdrive_interface.get_current_block()
    )
    last_checkpoint_time = interactive_hyperdrive.hyperdrive_interface.calc_checkpoint_id(current_block_time)
    next_checkpoint_time = (
        last_checkpoint_time + interactive_hyperdrive.hyperdrive_interface.pool_config.checkpoint_duration
    )
    advance_upper_bound = next_checkpoint_time - current_block_time - 2  # minus 2 seconds to avoid edge cases
    # Only advance time if the upper bound is positive
    # Would be negative if we are already very close to the next checkpoint time
    if advance_upper_bound >= 0:
        checkpoint_info = chain.advance_time(
            rng.integers(low=0, high=advance_upper_bound),
            create_checkpoints=True,  # we don't want to create one, but only because we haven't advanced enough
        )
        # do a final check to make sure that the checkpoint didn't happen
        assert len(checkpoint_info[interactive_hyperdrive]) == 0, "Checkpoint was created when it should not have been."


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

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
    return Args(
        chain_config=LocalChain.Config(chain_port=namespace.chain_port),
    )


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
    check_data,
    random_seed,
    interactive_hyperdrive,
    chain: LocalChain,
):
    """Check the pool state invariants.

    Arguments
    ---------
    check_data: dict[str, Any]
        The trade data to check.
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
    if check_data["long_events"]["close"].base_amount >= check_data["long_events"]["open"].base_amount:
        logging.critical(
            (
                "LONG: Amount returned on closing was too large.\n"
                "base_amount_returned=%s should not be >= base_amount_proided=%s"
            ),
            check_data["long_events"]["close"].base_amount,
            check_data["long_events"]["open"].base_amount,
        )
        failed = True
    if check_data["long_agent"].wallet.balance.amount >= check_data["trade_amount"]:
        logging.critical(
            "LONG: Agent made a profit when the should not have.\nagent_balance=%s should not be >= trade_amount=%s",
            check_data["long_agent"].wallet.balance.amount,
            check_data["trade_amount"],
        )
        failed = True
    if check_data["short_events"]["close"].base_amount >= check_data["short_events"]["open"].base_amount:
        logging.critical(
            (
                "SHORT: Amount returned on closing was too large.\n"
                "base_amount_returned=%s should not be >= base_amount_proided=%s"
            ),
            check_data["short_events"]["close"].base_amount,
            check_data["short_events"]["open"].base_amount,
        )
        failed = True
    if check_data["short_agent"].wallet.balance.amount >= check_data["trade_amount"]:
        logging.critical(
            "SHORT: Agent made a profit when the should not have.\nagent_balance=%s should not be >= trade_amount=%s",
            check_data["short_agent"].wallet.balance.amount,
            check_data["trade_amount"],
        )
        failed = True

    if failed:
        dump_state_dir = chain.save_state(save_prefix="fuzz_profit_check")

        pool_state = interactive_hyperdrive.hyperdrive_interface.current_pool_state
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

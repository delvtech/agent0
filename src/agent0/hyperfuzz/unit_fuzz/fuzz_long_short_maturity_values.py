"""Script to verify that longs and shorts which are closed at maturity supply the correct amounts.

# Test procedure
- spin up local chain, deploy hyperdrive with fees
- advance time to ensure we are in the middle of a checkpoint
- execute random trades
  - from [open_long, open_short]
  - trade amount in uniform[min_trade_amount, max_trade_amount) base
  - advance one block (12 sec) between each trade.
- advance time past the position duration, into a new checkpoint, create a checkpoint
- close the trades one at a time in random order, run invariance checks after each close action

# Invariance checks (these should be True):
if trade was open and close a long:
  - base out == bonds in minus flat fee
if trade was open and close a short:
  - base out == interest accrued
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Any, NamedTuple, Sequence

import numpy as np
from fixedpointmath import FixedPoint, isclose

from agent0.core.hyperdrive.crash_report import build_crash_trade_result, log_hyperdrive_crash_report
from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive
from agent0.ethpy.hyperdrive.event_types import CloseLong, CloseShort, OpenLong, OpenShort
from agent0.hyperfuzz import FuzzAssertionException
from agent0.hypertypes.fixedpoint_types import CheckpointFP

from .helpers import advance_time_after_checkpoint, execute_random_trades, setup_fuzz

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


def fuzz_long_short_maturity_values(
    num_trades: int,
    long_maturity_vals_epsilon: float,
    short_maturity_vals_epsilon: float,
    chain_config: LocalChain.Config,
    steth: bool = False,
    pause_on_fail: bool = False,
):
    """Does fuzzy invariant checks on closing longs and shorts past maturity.

    Parameters
    ----------
    num_trades: int
        Number of trades to perform during the fuzz tests.
    long_maturity_vals_epsilon: float
        The allowed error for maturity values equality tests for longs.
    short_maturity_vals_epsilon: float
        The allowed error for maturity values equality tests for shorts.
    chain_config: LocalChain.Config, optional
        Configuration options for the local chain.
    steth: bool
        Whether to use steth instead of erc4626
    pause_on_fail: bool
        If True, pause on test failure.
    """
    # pylint: disable=too-many-arguments

    # Parameters for local chain initialization, defines defaults in constructor
    # set a large block time so i can manually control when it ticks
    # TODO: set block time really high after contracts deployed:
    # chain_config = LocalChain.Config(block_time=1_000_000)
    chain, random_seed, rng, hyperdrive_pool = setup_fuzz(
        chain_config, fuzz_test_name="fuzz_long_short_maturity_values", steth=steth
    )
    signer = chain.init_agent(eth=FixedPoint(100), pool=hyperdrive_pool)

    # Add a small amount to ensure we're not at the edge of a checkpoint
    # This prevents the latter step of `chain.advance_time(position_duration+30)` advancing past a checkpoint
    # Also prevents `open_random_trades` from passing the create checkpoint barrier
    logging.info("Advance time...")
    advance_time_after_checkpoint(chain, hyperdrive_pool)

    # Open some trades
    logging.info("Open random trades...")
    trade_events = execute_random_trades(num_trades, chain, rng, hyperdrive_pool, advance_time=False)

    # Ensure all trades open are within the same checkpoint
    trade_maturity_times = []
    for agent, event in trade_events:
        trade_maturity_times.append(event.maturity_time)
    assert all(maturity_time == trade_maturity_times[0] for maturity_time in trade_maturity_times)

    # Starting checkpoint is automatically created by sending transactions
    starting_checkpoint = hyperdrive_pool.interface.current_pool_state.checkpoint

    # Advance the time to a little more than the position duration
    logging.info("Advance time...")
    position_duration = hyperdrive_pool.interface.pool_config.position_duration
    chain.advance_time(position_duration + 30, create_checkpoints=False)

    # Create a checkpoint
    logging.info("Create a checkpoint...")
    # Get the maturity checkpoint for the previously created checkpoint
    checkpoint_id = hyperdrive_pool.interface.calc_checkpoint_id()
    hyperdrive_pool.interface.create_checkpoint(signer.account, checkpoint_time=checkpoint_id)
    maturity_checkpoint = hyperdrive_pool.interface.current_pool_state.checkpoint

    # Ensure this maturity checkpoint is the maturity of all open positions
    for trade_maturity_time in trade_maturity_times:
        assert checkpoint_id == trade_maturity_time

    # Advance time again
    logging.info("Advance time...")
    extra_time = int(np.floor(rng.uniform(low=0, high=position_duration)))
    chain.advance_time(extra_time, create_checkpoints=False)

    # Randomize close trade order
    # Numpy rng allows lists to be passed in
    rng.shuffle(trade_events)  # type: ignore

    # Close the trades one at a time, check invariants
    for index, (agent, trade) in enumerate(trade_events):
        logging.info("closing trade %s out of %s\n", index, len(trade_events) - 1)
        if isinstance(trade, OpenLong):
            close_event = agent.close_long(maturity_time=trade.maturity_time, bonds=trade.bond_amount)
        elif isinstance(trade, OpenShort):
            close_event = agent.close_short(maturity_time=trade.maturity_time, bonds=trade.bond_amount)
        else:
            assert False

        try:
            invariant_check(
                trade,
                close_event,
                starting_checkpoint,
                maturity_checkpoint,
                long_maturity_vals_epsilon,
                short_maturity_vals_epsilon,
                hyperdrive_pool,
            )
        except FuzzAssertionException as error:
            dump_state_dir = chain.save_state(save_prefix="fuzz_long_short_maturity_values")
            # The additional information going into the crash report
            additional_info = {
                "fuzz_random_seed": random_seed,
                "dump_state_dir": dump_state_dir,
                "trade_events": hyperdrive_pool.get_trade_events(),
            }
            additional_info.update(error.exception_data)

            # The subset of information going into rollbar
            rollbar_data = {
                "fuzz_random_seed": random_seed,
                "dump_state_dir": dump_state_dir,
            }
            rollbar_data.update(error.exception_data)

            report = build_crash_trade_result(
                error, hyperdrive_pool.interface, agent.account, additional_info=additional_info
            )
            # Crash reporting already going to file in logging
            log_hyperdrive_crash_report(
                report,
                crash_report_to_file=True,
                crash_report_stdout_summary=False,
                crash_report_file_prefix="fuzz_long_short_maturity_values",
                log_to_rollbar=True,
                rollbar_log_level_threshold=chain_config.rollbar_log_level_threshold,
                rollbar_log_filter_func=chain_config.rollbar_log_filter_func,
                rollbar_data=rollbar_data,
            )
            if pause_on_fail:
                # We don't log info from logging, so we print to ensure this shows up
                print(
                    f"Pausing pool (pool:{hyperdrive_pool.hyperdrive_address} port:{chain_config.chain_port}) "
                    f"crash {repr(error)}"
                )
                while True:
                    time.sleep(1000000)

            chain.cleanup()
            raise error

    chain.cleanup()
    logging.info("Test passed!")


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    num_trades: int
    long_maturity_vals_epsilon: float
    short_maturity_vals_epsilon: float
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
    return Args(
        num_trades=namespace.num_trades,
        long_maturity_vals_epsilon=namespace.long_maturity_vals_epsilon,
        short_maturity_vals_epsilon=namespace.short_maturity_vals_epsilon,
        chain_config=LocalChain.Config(chain_port=namespace.chain_port, log_to_stdout=namespace.log_to_stdout),
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
        "--num_trades",
        type=int,
        default=5,
        help="The number of random trades to open.",
    )
    parser.add_argument(
        "--long_maturity_vals_epsilon",
        type=float,
        default=1e-14,
        help="The epsilon for long maturity expected value.",
    )
    parser.add_argument(
        "--short_maturity_vals_epsilon",
        type=float,
        default=1e-9,
        help="The epsilon for short maturity expected value.",
    )
    parser.add_argument(
        "--chain_port",
        type=int,
        default=10000,
        help="The number of random trades to open.",
    )
    parser.add_argument(
        "--log_to_stdout",
        type=bool,
        default=False,
        help="If True, log to stdout in addition to a file.",
    )
    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv
    return namespace_to_args(parser.parse_args())


# pylint: disable=too-many-arguments
def invariant_check(
    open_trade_event: OpenLong | OpenShort,
    close_trade_event: CloseLong | CloseShort,
    starting_checkpoint: CheckpointFP,
    maturity_checkpoint: CheckpointFP,
    long_maturity_vals_epsilon: float,
    short_maturity_vals_epsilon: float,
    interactive_hyperdrive: LocalHyperdrive,
) -> None:
    """Check the pool state invariants and throws an assertion exception if fails.

    Arguments
    ---------
    open_trade_event: OpenLong | OpenShort
        The OpenLong or OpenShort event that resulted from opening the position.
    close_trade_event: CloseLong | CloseShort
        The CloseLong or CloseShort event that resulted from closing the position.
    starting_checkpoint: CheckpointFP
        The starting checkpoint.
    maturity_checkpoint: CheckpointFP
        The maturity checkpoint.
    long_maturity_vals_epsilon: float
        The epsilon value for the maturity values for longs.
    short_maturity_vals_epsilon: float
        The epsilon value for the maturity values for shorts.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    """
    # pylint: disable=too-many-statements
    failed = False

    exception_message: list[str] = ["Fuzz Long/Short Maturity Values Invariant Check"]
    exception_data: dict[str, Any] = {}

    if isinstance(open_trade_event, OpenLong) and isinstance(close_trade_event, CloseLong):
        # Ensure we close the trade for all of the opened bonds
        assert close_trade_event.bond_amount == open_trade_event.bond_amount

        # 0.05 would be a 5% fee.
        flat_fee_percent = interactive_hyperdrive.interface.pool_config.fees.flat

        # base out should be equal to bonds in minus the flat fee.
        if interactive_hyperdrive.interface.hyperdrive_kind == interactive_hyperdrive.interface.HyperdriveKind.STETH:
            # If the underlying vault is steth, there's an inaccuracy with computing
            # the base amount via `lidoShares * vaultSharePrice`.
            # Instead, we do a contract call for the conversion for a more accurate value.

            # TODO to keep accounting accurate, we should keep all internal unit in lido shares,
            # and only convert on anything that is user facing. This isn't ideal however,
            # because while conversion from steth -> shares in inputs to trades (e.g., openLong)
            # is relatively straightforward, the conversion from shares -> steth in
            # analysis is not, and is especially complicated when analysis goes back in the past
            # (e.g., we want to show historical pnl in units of steth, but we need to know
            # the share price at the time index). This is especially complicated since
            # the raw number in steth is changing as well. One fix is to just keep all
            # user facing output units in lido shares, and add comments on any user
            # facing functions that the units in analysis and events are in lido shares.

            # Undo lido to steth conversion
            lido_shares = close_trade_event.amount / close_trade_event.vault_share_price
            # Use lido contract to make the conversion on the event block
            # Type narrowing
            assert interactive_hyperdrive.interface.vault_shares_token_contract is not None
            steth_amount_in_wei = (
                interactive_hyperdrive.interface.vault_shares_token_contract.functions.getPooledEthByShares(
                    lido_shares.scaled_value
                ).call(block_identifier=close_trade_event.block_number)
            )
            actual_long_base_amount = FixedPoint(scaled_value=steth_amount_in_wei)

        else:
            actual_long_base_amount = close_trade_event.amount

        expected_long_base_amount = close_trade_event.bond_amount - close_trade_event.bond_amount * flat_fee_percent

        # assert with close event bond amount
        if not isclose(
            actual_long_base_amount, expected_long_base_amount, abs_tol=FixedPoint(str(long_maturity_vals_epsilon))
        ):
            difference_in_wei = abs(actual_long_base_amount.scaled_value - expected_long_base_amount.scaled_value)
            exception_message.append("The base out does not equal the bonds in minus the flat fee.")
            exception_message.append(
                f"{actual_long_base_amount=} != {expected_long_base_amount=}, {difference_in_wei=}"
            )
            exception_data["invariance_check:actual_long_base_amount"] = actual_long_base_amount
            exception_data["invariance_check:expected_long_base_amount"] = expected_long_base_amount
            exception_data["invariance_check:long_base_amount_difference_in_wei"] = difference_in_wei
            failed = True

    elif isinstance(open_trade_event, OpenShort) and isinstance(close_trade_event, CloseShort):
        # Ensure we close the trade for all of the opened bonds
        assert close_trade_event.bond_amount == open_trade_event.bond_amount

        # get the share prices
        open_vault_share_price = starting_checkpoint.vault_share_price
        closing_vault_share_price = maturity_checkpoint.vault_share_price

        # interested accrued in shares = (c1 / c0 + flat_fee) * dy - c1 * dz
        flat_fee_percent = interactive_hyperdrive.interface.pool_config.fees.flat

        # get the share amount, c1 * dz part of the equation.
        share_reserves_delta = open_trade_event.bond_amount
        flat_fee = open_trade_event.bond_amount * flat_fee_percent
        share_reserves_delta_plus_flat_fee = share_reserves_delta + flat_fee

        # get the final interest accrued
        expected_short_base_amount = (
            open_trade_event.bond_amount * (closing_vault_share_price / open_vault_share_price + flat_fee_percent)
            - share_reserves_delta_plus_flat_fee
        )

        actual_short_base_amount = close_trade_event.amount
        if not isclose(
            actual_short_base_amount, expected_short_base_amount, abs_tol=FixedPoint(str(short_maturity_vals_epsilon))
        ):
            difference_in_wei = abs(actual_short_base_amount.scaled_value - expected_short_base_amount.scaled_value)
            exception_message.append(
                "The expected base returned (interest accrued) does not match the event's reported base returned."
            )
            exception_message.append(
                f"{actual_short_base_amount=} != {expected_short_base_amount=}, {difference_in_wei=}"
            )
            exception_data["invariance_check:actual_short_base_amount"] = actual_short_base_amount
            exception_data["invariance_check:expected_short_base_amount"] = expected_short_base_amount
            exception_data["invariance_check:short_base_amount_difference_in_wei"] = difference_in_wei
            failed = True

    else:
        raise ValueError("Invalid types for open/close trade events")

    # Check vault shares after trades matures
    pool_state = interactive_hyperdrive.interface.get_hyperdrive_state()
    expected_vault_shares = (
        pool_state.pool_info.share_reserves
        + (
            pool_state.pool_info.shorts_outstanding
            + (pool_state.pool_info.shorts_outstanding * pool_state.pool_config.fees.flat)
        )
        / pool_state.pool_info.vault_share_price
        + pool_state.gov_fees_accrued
        + pool_state.pool_info.withdrawal_shares_proceeds
        + pool_state.pool_info.zombie_share_reserves
    )
    actual_vault_shares = pool_state.vault_shares

    if actual_vault_shares < expected_vault_shares:
        difference_in_wei = abs(expected_vault_shares.scaled_value - actual_vault_shares.scaled_value)
        exception_message.append(
            f"{actual_vault_shares=} is expected to be greater than {expected_vault_shares=} after mature. "
            f"{difference_in_wei=}. "
        )
        exception_data["invariance_check:expected_vault_shares"] = expected_vault_shares
        exception_data["invariance_check:actual_vault_shares"] = actual_vault_shares
        exception_data["invariance_check:vault_shares_difference_in_wei"] = difference_in_wei
        failed = True

    if failed:
        logging.critical("\n".join(exception_message))
        raise FuzzAssertionException(*exception_message, exception_data=exception_data)


if __name__ == "__main__":
    main()

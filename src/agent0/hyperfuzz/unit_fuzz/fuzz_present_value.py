"""Script to confirm present value and LP share price invariance.

# Test procedure
- spin up local chain, deploy hyperdrive without fees
- given trade list [open_long, close_long, open_short, close_short, add_liquidity, remove_liquidity]
  - trade amount in uniform[min_trade_amount, max_trade_amount) base
  - execute the trade and allow the block to tick (12 seconds)
  - check invariances after each trade

# Invariance checks (these should be True):
- the following state values should equal:
  - for any trade, LP share price shouldn't change by more than 0.1%
  - for any trade, present value should always be >= idle
  - open or close trades shouldn't affect PV within 0.1
  - removing liquidity shouldn't result in the PV increasing (it should decrease)
  - adding liquidity shouldn't result in the PV decreasing (it should increase)
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import asdict
from typing import Any, NamedTuple, Sequence

import numpy as np
from fixedpointmath import FixedPoint, isclose

from agent0.core.hyperdrive import HyperdriveActionType
from agent0.core.hyperdrive.crash_report import build_crash_trade_result, log_hyperdrive_crash_report
from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive
from agent0.hyperfuzz import FuzzAssertionException

from .helpers import setup_fuzz

# tests have lots of stuff
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements


def main(argv: Sequence[str] | None = None):
    """Primary entrypoint.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    # Setup the experiment
    parsed_args = parse_arguments(argv)
    fuzz_present_value(*parsed_args)


def fuzz_present_value(
    test_epsilon: float,
    chain_config: LocalChain.Config,
):
    """Does fuzzy invariant checks for opening and closing longs and shorts.

    Parameters
    ----------
    test_epsilon: float
        The allowed error for present value equality tests.
    chain_config: LocalChain.Config, optional
        Configuration options for the local chain.
    """
    chain, random_seed, rng, interactive_hyperdrive = setup_fuzz(
        chain_config,
        curve_fee=FixedPoint(0),
        flat_fee=FixedPoint(0),
        governance_lp_fee=FixedPoint(0),
        governance_zombie_fee=FixedPoint(0),
        fuzz_test_name="fuzz_present_value",
    )

    initial_pool_state = interactive_hyperdrive.interface.current_pool_state
    check_data: dict[str, Any] = {
        "initial_lp_share_price": initial_pool_state.pool_info.lp_share_price,
        "initial_present_value": interactive_hyperdrive.interface.calc_present_value(initial_pool_state),
    }
    agent = chain.init_agent(base=FixedPoint("1e10"), eth=FixedPoint(1_000), pool=interactive_hyperdrive)

    # Execute the trades and check invariances for each trade
    for trade_type in [
        HyperdriveActionType.OPEN_LONG,
        HyperdriveActionType.CLOSE_LONG,
        HyperdriveActionType.OPEN_SHORT,
        HyperdriveActionType.CLOSE_SHORT,
        HyperdriveActionType.ADD_LIQUIDITY,
        HyperdriveActionType.REMOVE_LIQUIDITY,
    ]:
        # Keep the agent flush
        if agent.get_wallet().balance.amount < FixedPoint("1e10"):
            agent.add_funds(base=FixedPoint("1e10") - agent.get_wallet().balance.amount)

        # Set up trade amount bounds
        min_trade = interactive_hyperdrive.interface.pool_config.minimum_transaction_amount
        max_budget = agent.get_wallet().balance.amount
        trade_amount = None

        # Execute the trade
        match trade_type:
            case HyperdriveActionType.OPEN_LONG:
                max_trade = interactive_hyperdrive.interface.calc_max_long(
                    max_budget, interactive_hyperdrive.interface.current_pool_state
                )
                trade_amount = FixedPoint(
                    scaled_value=int(np.floor(rng.uniform(low=min_trade.scaled_value, high=max_trade.scaled_value)))
                )
                trade_event = agent.open_long(base=trade_amount)
            case HyperdriveActionType.CLOSE_LONG:
                maturity_time, open_trade = next(iter(agent.get_wallet().longs.items()))
                trade_event = agent.close_long(maturity_time=maturity_time, bonds=open_trade.balance)
            case HyperdriveActionType.OPEN_SHORT:
                max_trade = interactive_hyperdrive.interface.calc_max_short(
                    max_budget, interactive_hyperdrive.interface.current_pool_state
                )
                trade_amount = FixedPoint(
                    scaled_value=int(np.floor(rng.uniform(low=min_trade.scaled_value, high=max_trade.scaled_value)))
                )
                trade_event = agent.open_short(trade_amount)
            case HyperdriveActionType.CLOSE_SHORT:
                maturity_time, open_trade = next(iter(agent.get_wallet().shorts.items()))
                trade_event = agent.close_short(maturity_time=maturity_time, bonds=open_trade.balance)
            case HyperdriveActionType.ADD_LIQUIDITY:
                # recompute initial present value for liquidity actions
                check_data["initial_present_value"] = interactive_hyperdrive.interface.calc_present_value(
                    interactive_hyperdrive.interface.current_pool_state
                )
                trade_amount = FixedPoint(
                    scaled_value=int(
                        np.floor(
                            rng.uniform(low=min_trade.scaled_value, high=agent.get_wallet().balance.amount.scaled_value)
                        )
                    )
                )
                trade_event = agent.add_liquidity(trade_amount)
            case HyperdriveActionType.REMOVE_LIQUIDITY:
                # recompute initial present value for liquidity actions
                check_data["initial_present_value"] = interactive_hyperdrive.interface.calc_present_value(
                    interactive_hyperdrive.interface.current_pool_state
                )
                trade_amount = agent.get_wallet().lp_tokens
                trade_event = agent.remove_liquidity(agent.get_wallet().lp_tokens)
            case _:
                raise ValueError(f"Invalid {trade_type=}")

        # run invariance check
        check_data["trade_type"] = trade_type
        try:
            invariant_check(check_data, test_epsilon, interactive_hyperdrive)
        except FuzzAssertionException as error:
            dump_state_dir = chain.save_state(save_prefix="fuzz_present_value")

            # The additional information going into the crash report
            additional_info = {
                "fuzz_random_seed": random_seed,
                "dump_state_dir": dump_state_dir,
                "trade_events": interactive_hyperdrive.get_trade_events(),
            }
            additional_info.update(check_data)  # add check_data fields
            additional_info.update(error.exception_data)

            # The subset of information going into rollbar
            rollbar_data = {
                "fuzz_random_seed": random_seed,
                "trade_type": trade_type,
                "trade_amount": trade_amount,
                "initial_present_value": check_data["initial_present_value"],
                "initial_lp_share_price": check_data["initial_lp_share_price"],
                "dump_state_dir": dump_state_dir,
            }
            for key, value in asdict(trade_event).items():
                key = "event_" + key
                rollbar_data[key] = value
            rollbar_data.update(error.exception_data)

            report = build_crash_trade_result(
                error, interactive_hyperdrive.interface, agent.account, additional_info=additional_info
            )
            # Crash reporting already going to file in logging
            log_hyperdrive_crash_report(
                report,
                crash_report_to_file=True,
                crash_report_file_prefix="fuzz_present_value",
                log_to_rollbar=True,
                rollbar_data=rollbar_data,
            )
            chain.cleanup()
            raise error
    chain.cleanup()
    logging.info("Test passed!")


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    test_epsilon: float
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
        test_epsilon=namespace.test_epsilon,
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
        "--test_epsilon",
        type=float,
        default=1e-4,
        help="The allowed error for present value and share price equality tests.",
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


def invariant_check(
    check_data: dict[str, Any],
    test_epsilon: float,
    interactive_hyperdrive: LocalHyperdrive,
) -> None:
    """Check the pool state invariants and throws an assertion exception if fails.

    Arguments
    ---------
    check_data: dict[str, Any]
        The trade data to check.
    test_epsilon: float
        The allowed error for present value equality tests.
        It is a float representing the proportional error tolerated.
        For example, test_epsilon = 0.01 means the actual_value must be within 1% of the expected_value.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    """
    # pylint: disable=too-many-statements
    failed = False
    exception_message: list[str] = ["Fuzz Present Value Invariant Check"]
    exception_data: dict[str, Any] = {}
    pool_state = interactive_hyperdrive.interface.get_hyperdrive_state()

    # LP share price
    # for any trade, LP share price shouldn't change by more than 0.1%
    initial_lp_share_price = FixedPoint(check_data["initial_lp_share_price"])
    current_lp_share_price = pool_state.pool_info.lp_share_price
    test_tolerance = initial_lp_share_price * FixedPoint(str(test_epsilon))
    if not isclose(initial_lp_share_price, current_lp_share_price, abs_tol=test_tolerance):
        difference_in_wei = abs(initial_lp_share_price.scaled_value - current_lp_share_price.scaled_value)
        exception_message.append("LP share price increased by more than 0.1%.")
        exception_message.append(f"{initial_lp_share_price=} != {current_lp_share_price=}, {difference_in_wei=}")
        exception_data["invariance_check:initial_lp_share_price"] = initial_lp_share_price
        exception_data["invariance_check:current_lp_share_price"] = current_lp_share_price
        exception_data["invariance_check:lp_share_price_difference_in_wei"] = difference_in_wei
        failed = True

    # present value should always be >= idle
    # idle shares are the shares that are not reserved by open positions
    # TODO: Add calculate_idle_share_reserves to hyperdrivepy and use that here.
    current_present_value = interactive_hyperdrive.interface.calc_present_value(pool_state)
    idle_shares = interactive_hyperdrive.interface.get_idle_shares(pool_state)
    if current_present_value < idle_shares:
        difference_in_wei = abs(current_present_value.scaled_value - idle_shares.scaled_value)
        exception_message.append("The present value is not greater than or equal to the idle.")
        exception_message.append(f"{current_present_value=} < {idle_shares=}, {difference_in_wei=}")
        exception_data["invariance_check:idle_shares"] = idle_shares
        exception_data["invariance_check:current_present_value"] = current_present_value
        exception_data["invariance_check:present_value_difference_in_wei"] = difference_in_wei
        failed = True

    # Present value
    initial_present_value = FixedPoint(check_data["initial_present_value"])
    # open or close trades shouldn't affect PV within 0.1%
    if check_data["trade_type"] in [
        HyperdriveActionType.OPEN_LONG,
        HyperdriveActionType.CLOSE_LONG,
        HyperdriveActionType.OPEN_SHORT,
        HyperdriveActionType.CLOSE_SHORT,
    ]:
        test_tolerance = initial_present_value * FixedPoint(str(test_epsilon))
        if not isclose(initial_present_value, current_present_value, abs_tol=test_tolerance):
            difference_in_wei = abs(initial_present_value.scaled_value - current_present_value.scaled_value)
            exception_message.append("Opening or closing trades affects the present value more than 0.1%.")
            exception_message.append(f"{initial_present_value=} != {current_present_value=}, {difference_in_wei=}")
            exception_data["invariance_check:initial_present_value"] = initial_present_value
            exception_data["invariance_check:current_present_value"] = current_present_value
            exception_data["invariance_check:present_value_difference_in_wei"] = difference_in_wei
            failed = True

    # adding liquidity shouldn't result in the PV decreasing (it should increase)
    if check_data["trade_type"] == HyperdriveActionType.ADD_LIQUIDITY:
        if current_present_value < initial_present_value:  # it decreased == bad
            difference_in_wei = abs(current_present_value.scaled_value - initial_present_value.scaled_value)
            exception_message.append("Adding liquidity resulted in the present value decreasing.")
            exception_message.append(f"{current_present_value=} < {initial_present_value=}, {difference_in_wei=}")
            exception_data["invariance_check:initial_present_value"] = initial_present_value
            exception_data["invariance_check:current_present_value"] = current_present_value
            exception_data["invariance_check:present_value_difference_in_wei"] = difference_in_wei
            failed = True

    # removing liquidity shouldn't result in the PV increasing (it should decrease)
    if check_data["trade_type"] == HyperdriveActionType.REMOVE_LIQUIDITY:
        if current_present_value > initial_present_value:  # it increased == bad
            difference_in_wei = abs(current_present_value.scaled_value - initial_present_value.scaled_value)
            exception_message.append("Removing liquidity resulted in the present value increasing.")
            exception_message.append(f"{current_present_value=} > {initial_present_value=}, {difference_in_wei=}")
            exception_data["invariance_check:initial_present_value"] = initial_present_value
            exception_data["invariance_check:current_present_value"] = current_present_value
            exception_data["invariance_check:present_value_difference_in_wei"] = difference_in_wei
            failed = True

    if failed:
        logging.critical("\n".join(exception_message))
        raise FuzzAssertionException(*exception_message, exception_data=exception_data)


if __name__ == "__main__":
    main()

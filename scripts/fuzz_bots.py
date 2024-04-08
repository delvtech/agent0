"""Runs random bots against the local chain for fuzz testing."""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
import sys
from typing import Callable, NamedTuple, ParamSpec, Sequence, TypeVar

from fixedpointmath import FixedPoint
from web3.types import RPCEndpoint

from agent0 import IChain, IHyperdrive, PolicyZoo
from agent0.core.base.make_key import make_private_key
from agent0.core.hyperdrive.interactive.i_hyperdrive_agent import IHyperdriveAgent
from agent0.ethpy import build_eth_config
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar

# Crash behavior
STOP_CHAIN_ON_CRASH = False
# Number of bots
NUM_RANDOM_AGENTS = 2
NUM_RANDOM_HOLD_AGENTS = 2
# The amount of base tokens & ETH each bot receives
BASE_BUDGET_PER_BOT = FixedPoint("10_000_000")
ETH_BUDGET_PER_BOT = FixedPoint("1_000")
# The slippage tolerance for trades
SLIPPAGE_TOLERANCE = FixedPoint("0.01")  # 1% slippage


# Async runner helper
P = ParamSpec("P")
R = TypeVar("R")


async def _async_runner(
    funcs: list[Callable[P, R]],
    *args: P.args,
    **kwargs: P.kwargs,
) -> list[R]:
    """Helper function that runs a list of passed in functions asynchronously.

    WARNING: this assumes all functions passed in are thread safe, use at your own risk.

    TODO args and kwargs likely should also be a list for passing in separate arguments.

    Arguments
    ---------
    funcs: list[Callable[P, R]]
        List of functions to run asynchronously
    *args: P.args
        Positional arguments for the functions
    **kwargs: P.kwargs
        Keyword arguments for the functions

    Returns
    -------
    list[R]
        List of results
    """

    # We launch all functions in threads using the `to_thread` function.
    # This allows the underlying functions to use non-async waits.

    # Runs all functions passed in and gathers results
    gather_result: list[R | BaseException] = await asyncio.gather(
        *[asyncio.to_thread(func, *args, **kwargs) for func in funcs], return_exceptions=True
    )

    # Error checking
    # TODO we can add retries here
    out_result: list[R] = []
    for result in gather_result:
        if isinstance(result, BaseException):
            raise result
        out_result.append(result)

    return out_result


def run_fuzz_bots(argv: Sequence[str] | None = None) -> None:
    """Runs fuzz bots

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    parsed_args = parse_arguments(argv)

    # Get config and addresses
    eth_config = build_eth_config(dotenv_file="eth.env")
    hyperdrive_addresses = IHyperdrive.get_deployed_hyperdrive_addresses(eth_config.artifacts_uri)
    if parsed_args.pool not in hyperdrive_addresses:
        raise ValueError(
            f"Pool {parsed_args.pool} not recognized. Available options are {list(hyperdrive_addresses.keys())}"
        )
    hyperdrive_address = hyperdrive_addresses[parsed_args.pool]

    log_to_rollbar = initialize_rollbar("localfuzzbots_" + parsed_args.pool)

    # Make sure the bots have at least 10% of their budget after each trade
    minimum_avg_agent_base = BASE_BUDGET_PER_BOT / FixedPoint(10)

    rng_seed = random.randint(0, 10000000)

    # Connect to the chain
    chain = IChain(eth_config.rpc_uri)

    hyperdrive_config = IHyperdrive.Config(
        preview_before_trade=True,
        rng_seed=rng_seed,
        log_to_rollbar=log_to_rollbar,
        rollbar_log_prefix="fuzzbots",
        crash_log_level=logging.CRITICAL,
        crash_report_additional_info={"rng_seed": rng_seed},
    )
    hyperdrive_pool = IHyperdrive(chain, hyperdrive_address, hyperdrive_config)

    # Initialize agents
    agents: list[IHyperdriveAgent] = []
    for _ in range(NUM_RANDOM_AGENTS):
        # Initialize & fund agent using a random private key
        agent: IHyperdriveAgent = hyperdrive_pool.init_agent(
            private_key=make_private_key(),
            policy=PolicyZoo.random,
            policy_config=PolicyZoo.random.Config(
                slippage_tolerance=SLIPPAGE_TOLERANCE,
                trade_chance=FixedPoint("0.8"),
                randomly_ignore_slippage_tolerance=True,
            ),
        )
        agents.append(agent)

    for _ in range(NUM_RANDOM_HOLD_AGENTS):
        agent: IHyperdriveAgent = hyperdrive_pool.init_agent(
            private_key=make_private_key(),
            policy=PolicyZoo.random_hold,
            policy_config=PolicyZoo.random_hold.Config(
                slippage_tolerance=SLIPPAGE_TOLERANCE,
                trade_chance=FixedPoint("0.8"),
                randomly_ignore_slippage_tolerance=True,
                max_open_positions=2_000,
            ),
        )
        agents.append(agent)

    # Add funds asynchronously
    logging.info("Funding bots...")
    asyncio.run(
        _async_runner(
            [agent.add_funds for agent in agents],
            base=BASE_BUDGET_PER_BOT,
            eth=ETH_BUDGET_PER_BOT,
        )
    )

    logging.info("Setting max approval...")
    # Set max approval asynchronously
    asyncio.run(
        _async_runner(
            [agent.set_max_approval for agent in agents],
        )
    )

    # Make trades until the user or agents stop us
    logging.info("Trading...")
    while True:
        # Execute the agent policies asynchronously
        try:
            asyncio.run(
                _async_runner(
                    [agent.execute_policy_action for agent in agents],
                )
            )
        # Don't stop chain if the user interrupts
        except KeyboardInterrupt:
            sys.exit()
        # if bots crash, we us an RPC to stop mining anvil
        except Exception as exc:  # pylint: disable=broad-exception-caught
            if STOP_CHAIN_ON_CRASH:
                hyperdrive_pool.interface.web3.provider.make_request(
                    method=RPCEndpoint("evm_setIntervalMining"), params=[0]
                )
                raise exc
            # Ignore crashes, we want the bot to keep trading
            # These errors will get logged regardless

        # Check agent funds and refund if necessary
        for agent in agents:
            # Update agent funds
            if minimum_avg_agent_base is not None:
                if (
                    sum(agent.wallet.balance.amount for agent in agents) / FixedPoint(len(agents))
                    < minimum_avg_agent_base
                ):
                    asyncio.run(
                        _async_runner(
                            [agent.add_funds for agent in agents],
                            base=BASE_BUDGET_PER_BOT,
                            eth=ETH_BUDGET_PER_BOT,
                        )
                    )


class Args(NamedTuple):
    """Command line arguments for the checkpoint bot."""

    pool: str


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
    return Args(pool=namespace.pool)


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
    parser = argparse.ArgumentParser(description="Runs random bots.")
    # TODO read this from the register or pass in pool address
    parser.add_argument(
        "--pool",
        type=str,
        default="erc4626_hyperdrive",
        help='The logical name of the pool to connect to. Options are "erc4626_hyperdrive" and "stethhyperdrive".',
    )
    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv
    return namespace_to_args(parser.parse_args())


if __name__ == "__main__":
    run_fuzz_bots()

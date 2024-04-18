"""Runs random bots against a remote chain for fuzz testing."""

from __future__ import annotations

import argparse
import logging
import random
import sys
from typing import NamedTuple, Sequence

from web3.types import RPCEndpoint

from agent0 import IChain, IHyperdrive
from agent0.ethpy import build_eth_config
from agent0.hyperfuzz.system_fuzz import run_fuzz_bots
from agent0.hyperlogs import setup_logging
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar

# Crash behavior
STOP_CHAIN_ON_CRASH = False


def main(argv: Sequence[str] | None = None) -> None:
    """Runs fuzz bots.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    parsed_args = parse_arguments(argv)

    # TODO consolidate setup into single function

    # Get config and addresses
    eth_config = build_eth_config()
    hyperdrive_addresses = IHyperdrive.get_deployed_hyperdrive_addresses(eth_config.artifacts_uri)
    if parsed_args.pool not in hyperdrive_addresses:
        raise ValueError(
            f"Pool {parsed_args.pool} not recognized. Available options are {list(hyperdrive_addresses.keys())}"
        )
    hyperdrive_address = hyperdrive_addresses[parsed_args.pool]

    log_to_rollbar = initialize_rollbar("remotefuzzbots_" + parsed_args.pool)
    setup_logging(
        log_stdout=True,
    )

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

    raise_error_on_crash = False
    if STOP_CHAIN_ON_CRASH:
        raise_error_on_crash = True

    try:
        run_fuzz_bots(
            hyperdrive_pool,
            check_invariance=False,
            raise_error_on_crash=raise_error_on_crash,
            log_to_rollbar=log_to_rollbar,
            run_async=True,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        if STOP_CHAIN_ON_CRASH:
            hyperdrive_pool.interface.web3.provider.make_request(
                method=RPCEndpoint("evm_setIntervalMining"), params=[0]
            )
        # If `run_fuzz_bots` exits, it's because we're wanting it to exit on crash
        # so we reraise the orig exception here
        raise exc


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
    main()

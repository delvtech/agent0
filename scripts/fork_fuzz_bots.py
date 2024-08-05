"""Runs random bots against a forked chain."""

from __future__ import annotations

import argparse
import logging
import random
import sys
from typing import NamedTuple, Sequence

import numpy as np
from fixedpointmath import FixedPoint

from agent0 import LocalChain, LocalHyperdrive
from agent0.hyperfuzz.system_fuzz import run_fuzz_bots
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar

# We define a dict of whales, keyed by the token contract addr,
# with the value as the whale address.
# Note that if a pool is missing in this mapping, we will try to
# call `mint` on the trading token to fund.
SEPOLIA_WHALE_ADDRESSES = {
    # We ignore DAI since the underlying base token is mintable
    # EZETH
    "0xDD0D63E304F3D9d9E54d8945bE95011867c80E4f": "0x54A93937EE00838d659795b9bbbe904a00DdF278"
}
# The static block we fork at
# TODO


def main(argv: Sequence[str] | None = None) -> None:
    """Runs local fuzz bots.

    Arguments
    ---------
    argv: Sequence[str]
        A sequence containing the uri to the database server.
    """
    # TODO consolidate setup into single function and clean up.
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-locals

    parsed_args = parse_arguments(argv)

    rpc_uri = parsed_args.rpc_uri
    registry_address = parsed_args.registry_addr

    log_to_rollbar = initialize_rollbar("forkfuzzbots")

    # Negative rng_seed means default
    if parsed_args.rng_seed < 0:
        rng_seed = random.randint(0, 10000000)
    else:
        rng_seed = parsed_args.rng_seed
    rng = np.random.default_rng(rng_seed)

    chain_config = LocalChain.Config(
        log_level_threshold=logging.WARNING,
        preview_before_trade=True,
        log_to_rollbar=log_to_rollbar,
        rollbar_log_prefix="forkfuzzbots",
        rng=rng,
        crash_log_level=logging.ERROR,
        crash_report_additional_info={"rng_seed": rng_seed},
        gas_limit=int(1e6),  # Plenty of gas limit for transactions
    )
    # Build interactive local hyperdrive
    chain = LocalChain(fork_uri=rpc_uri, config=chain_config)

    # Get list of deployed pools on initial iteration
    deployed_pools = LocalHyperdrive.get_hyperdrive_pools_from_registry(chain, registry_address)

    while True:
        # Check for new pools
        latest_block = chain.block_data()
        latest_block_number = latest_block.get("number", None)
        if latest_block_number is None:
            raise AssertionError("Block has no number.")

        # TODO we may want to refork every once in awhile in case new pools are deployed.
        # For now, we assume this script gets restarted.

        # FIXME the function below funds agents via `mint` function,
        # this doesn't work on a fork. Find whales for these tokens and
        # fund this way.

        run_fuzz_bots(
            chain,
            hyperdrive_pools=deployed_pools,
            check_invariance=False,  # We don't check invariance here
            raise_error_on_failed_invariance_checks=False,
            raise_error_on_crash=False,
            log_to_rollbar=log_to_rollbar,
            ignore_raise_error_func=None,
            run_async=False,
            random_advance_time=False,
            random_variable_rate=False,
            lp_share_price_test=False,
            base_budget_per_bot=FixedPoint(1000),
            whale_accounts=SEPOLIA_WHALE_ADDRESSES,
        )

        chain.cleanup()


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    registry_addr: str
    rpc_uri: str
    rng_seed: int


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
        registry_addr=namespace.registry_addr,
        rpc_uri=namespace.rpc_uri,
        rng_seed=namespace.rng_seed,
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
        "--registry-addr",
        type=str,
        default="",
        help="The address of the registry.",
    )

    parser.add_argument(
        "--rpc-uri",
        type=str,
        default="",
        help="The RPC URI of the chain.",
    )

    parser.add_argument(
        "--rng-seed",
        type=int,
        default=-1,
        help="The random seed to use for the fuzz run.",
    )

    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv

    return namespace_to_args(parser.parse_args())


if __name__ == "__main__":
    main()

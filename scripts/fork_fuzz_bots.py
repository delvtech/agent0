"""Runs random bots against a forked chain."""

from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from typing import NamedTuple, Sequence

import numpy as np
from fixedpointmath import FixedPoint
from pypechain.core import FailedTransaction, PypechainCallException
from web3.exceptions import ContractCustomError

from agent0 import LocalChain, LocalHyperdrive
from agent0.hyperfuzz import FuzzAssertionException
from agent0.hyperfuzz.system_fuzz import run_fuzz_bots
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar, log_rollbar_message

# We define a dict of whales, keyed by the token contract addr,
# with the value as the whale address.
# Note that if a token is missing in this mapping, we will try to
# call `mint` on the trading token to fund.
SEPOLIA_WHALE_ADDRESSES = {
    # Note all base tokens are mintable up to 500, so we don't need whales here
}
# TODO set the static block we fork at, in case whales change


def _fuzz_ignore_errors(exc: Exception) -> bool:
    """Function defining errors to ignore for pausing chain during fuzzing."""
    # pylint: disable=too-many-return-statements
    # pylint: disable=too-many-branches
    # Ignored fuzz exceptions
    if isinstance(exc, FuzzAssertionException):
        # LP rate invariance check
        if (
            len(exc.args) >= 2
            and exc.args[0] == "Continuous Fuzz Bots Invariant Checks"
            and "lp_rate=" in exc.args[1]
            and "is expected to be >= vault_rate=" in exc.args[1]
        ):
            return True

        # Large circuit breaker check
        if (
            len(exc.args) >= 2
            and exc.args[0] == "Continuous Fuzz Bots Invariant Checks"
            and "Large trade has caused the rate circuit breaker to trip." in exc.args[1]
        ):
            return True

        # There's a known issue with the underlying steth pool on sepolia,
        # due to the deployed mock steth. Hence, we ignore the LP rate invariance check
        # for sepolia when fuzzing.
        if (
            # Only ignore steth pools
            "STETH" in exc.exception_data["pool_name"]
            and len(exc.args) >= 2
            and exc.args[0] == "Continuous Fuzz Bots Invariant Checks"
            and "actual_vault_shares=" in exc.args[1]
            and "is expected to be greater than expected_vault_shares=" in exc.args[1]
        ):
            return True

    # Contract call exceptions
    elif isinstance(exc, PypechainCallException):
        orig_exception = exc.orig_exception
        if orig_exception is None:
            return False

        # Insufficient liquidity error
        if (
            isinstance(orig_exception, ContractCustomError)
            and "ContractCustomError('InsufficientLiquidity')" in exc.args
        ):
            return True

        # Circuit breaker triggered error
        if (
            isinstance(orig_exception, ContractCustomError)
            and "ContractCustomError('CircuitBreakerTriggered')" in exc.args
        ):
            return True

        # DistributeExcessIdle error
        if (
            isinstance(orig_exception, ContractCustomError)
            and "ContractCustomError('DistributeExcessIdleFailed')" in exc.args
        ):
            return True

        # MinimumTransactionAmount error
        if (
            isinstance(orig_exception, ContractCustomError)
            and "ContractCustomError('MinimumTransactionAmount')" in exc.args
        ):
            return True

        # DecreasedPresentValueWhenAddingLiquidity error
        if (
            isinstance(orig_exception, ContractCustomError)
            and "ContractCustomError('DecreasedPresentValueWhenAddingLiquidity')" in exc.args
        ):
            return True

        # Closing long results in fees exceeding long proceeds
        if len(exc.args) > 1 and "Closing the long results in fees exceeding long proceeds" in exc.args[0]:
            return True

        # Status == 0
        if (
            # Lots of conditions to check
            # pylint: disable=too-many-boolean-expressions
            isinstance(orig_exception, list)
            and len(orig_exception) > 1
            and isinstance(orig_exception[0], FailedTransaction)
            # FIXME check for this
            and len(orig_exception[0].args) > 0
            and "Receipt has status of 0" in orig_exception[0].args[0]
        ):
            return True

    return False


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

    raise_error_on_fail = False
    if parsed_args.pause_on_invariance_fail:
        raise_error_on_fail = True

    # Negative rng_seed means default
    if parsed_args.rng_seed < 0:
        rng_seed = random.randint(0, 10000000)
    else:
        rng_seed = parsed_args.rng_seed
    rng = np.random.default_rng(rng_seed)

    # Empty string means default
    if parsed_args.chain_host == "":
        chain_host = None
    else:
        chain_host = parsed_args.chain_host

    # Negative chain port means default
    if parsed_args.chain_port < 0:
        chain_port = 1111
    else:
        chain_port = parsed_args.chain_port

    chain_config = LocalChain.Config(
        chain_host=chain_host,
        chain_port=chain_port,
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
    log_message = f"Running fuzzing on pools {[p.name for p in deployed_pools]}..."
    logging.info(log_message)
    log_rollbar_message(message=log_message, log_level=logging.INFO)

    while True:
        # Check for new pools
        latest_block = chain.block_data()
        latest_block_number = latest_block.get("number", None)
        if latest_block_number is None:
            raise AssertionError("Block has no number.")

        # TODO we may want to refork every once in awhile in case new pools are deployed.
        # For now, we assume this script gets restarted.

        try:
            run_fuzz_bots(
                chain,
                hyperdrive_pools=deployed_pools,
                check_invariance=True,
                raise_error_on_failed_invariance_checks=raise_error_on_fail,
                raise_error_on_crash=raise_error_on_fail,
                log_to_rollbar=log_to_rollbar,
                ignore_raise_error_func=_fuzz_ignore_errors,
                run_async=False,
                # TODO advance time and randomize variable rates
                random_advance_time=False,
                random_variable_rate=False,
                lp_share_price_test=False,
                # TODO all base tokens are mintable up to 500 base
                # If we want more, we need to put minting in a loop.
                base_budget_per_bot=FixedPoint(500),
                whale_accounts=SEPOLIA_WHALE_ADDRESSES,
            )
        except Exception as e:  # pylint: disable=broad-except
            logging.error(
                "Pausing port:%s on crash %s",
                chain.config.chain_port,
                repr(e),
            )
            while True:
                time.sleep(1000000)

        chain.cleanup()


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    pause_on_invariance_fail: bool
    registry_addr: str
    chain_host: str
    chain_port: int
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
        pause_on_invariance_fail=namespace.pause_on_invariance_fail,
        chain_host=namespace.chain_host,
        chain_port=namespace.chain_port,
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
        "--pause-on-invariance-fail",
        default=False,
        action="store_true",
        help="Pause execution on invariance failure.",
    )

    parser.add_argument(
        "--chain-host",
        type=str,
        default="",
        help="The host to bind for the anvil chain. Defaults to 127.0.0.1.",
    )
    parser.add_argument(
        "--chain-port",
        type=int,
        default=-1,
        help="The port to run anvil on.",
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

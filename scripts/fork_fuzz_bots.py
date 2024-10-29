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
from web3 import Web3
from web3.exceptions import ContractCustomError

from agent0 import LocalChain, LocalHyperdrive
from agent0.hyperfuzz import FuzzAssertionException
from agent0.hyperfuzz.fork_fuzz import accrue_interest_fork
from agent0.hyperfuzz.system_fuzz import run_fuzz_bots
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar, log_rollbar_exception, log_rollbar_message

# We define a dict of whales, keyed by the token contract addr,
# with the value as the whale address.
# Note that if a token is missing in this mapping, we will try to
# call `mint` on the trading token to fund.
MAINNET_WHALE_ADDRESSES = {
    # stETH
    "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84": "0x7F39C581F595B53C5CB19BD0B3F8DA6C935E2CA0",
    # DAI
    "0x6B175474E89094C44Da98b954EedeAC495271d0F": "0xf6e72Db5454dd049d0788e411b06CfAF16853042",
    # rETH
    "0xae78736Cd615f374D3085123A210448E74Fc6393": "0xCc9EE9483f662091a1de4795249E24aC0aC2630f",
    # ezETH
    "0xbf5495Efe5DB9ce00f80364C8B423567e58d2110": "0x22E12A50e3ca49FB183074235cB1db84Fe4C716D",
    # eETH
    "0x35fA164735182de50811E8e2E824cFb9B6118ac2": "0xCd5fE23C85820F7B72D0926FC9b05b43E359b7ee",
    # USDC
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": "0x37305B1cD40574E4C5Ce33f8e8306Be057fD7341",
    # USDA
    "0x0000206329b97DB379d5E1Bf586BbDB969C63274": "0xEc0B13b2271E212E1a74D55D51932BD52A002961",
    # USDS
    "0xdC035D45d973E3EC169d2276DDab16f1e407384F": "0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD",
    # sUSDe
    "0x9D39A5DE30e57443BfF2A8307A4256c8797A3497": "0xb99a2c4C1C4F1fc27150681B740396F6CE1cBcF5",
}

GNOSIS_WHALE_ADDRESSES = {
    # wstETH
    "0x6C76971f98945AE98dD7d4DFcA8711ebea946eA6": "0x458cD345B4C05e8DF39d0A07220feb4Ec19F5e6f",
}

LINEA_WHALE_ADDRESSES = {
    # wrsETH
    "0xD2671165570f41BBB3B0097893300b6EB6101E6C": "0x4DCb388488622e47683EAd1a147947140a31e485",
    # ezETH
    "0x2416092f143378750bb29b79eD961ab195CcEea5": "0x0684FC172a0B8e6A65cF4684eDb2082272fe9050",
}

BASE_WHALE_ADDRESSES = {
    # cbETH
    "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22": "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb",
    # USDC
    "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913": "0xF977814e90dA44bFA03b6295A0616a897441aceC",
    # Yield token of Moonwell USDC
    "0xc1256Ae5FF1cf2719D4937adb3bbCCab2E00A2Ca": "0x49E96E255bA418d08E66c35b588E2f2F3766E1d0",
    # mwEURC
    "0xf24608E0CCb972b0b0f4A6446a0BBf58c701a026": "0xAB198020F3B9Fa0187eAF5B5Cd09E407bE0E6F3F",
    # stkWELL
    "0xe66E3A37C3274Ac24FE8590f7D84A2427194DC17": "0x5E564c1905fFF9724621542f58d61BE0405C4879",
    # snARS
    "0xC1F4C75e8925A67BE4F35D6b1c044B5ea8849a58": "0x54423d0A5c4e3a6Eb8Bd12FDD54c1e6b42D52Ebe",
}

# We build an outer lookup based on chain id
WHALE_ADDRESSES = {
    # Ethereum
    1: MAINNET_WHALE_ADDRESSES,
    # Gnosis
    100: GNOSIS_WHALE_ADDRESSES,
    # Linea
    59144: LINEA_WHALE_ADDRESSES,
    # Base
    8453: BASE_WHALE_ADDRESSES,
}


def _fuzz_ignore_logging_to_rollbar(exc: Exception) -> bool:
    """Function defining errors to not log to rollbar during fuzzing.

    These are the two most common errors we see in local fuzz testing. These are
    known issues due to random bots not accounting for these cases, so we don't log them to
    rollbar.
    """
    if isinstance(exc, PypechainCallException):
        orig_exception = exc.orig_exception
        if orig_exception is None:
            return False

        # Insufficient liquidity error
        if isinstance(orig_exception, ContractCustomError) and exc.decoded_error == "InsufficientLiquidity()":
            return True

        # Circuit breaker triggered error
        if isinstance(orig_exception, ContractCustomError) and exc.decoded_error == "CircuitBreakerTriggered()":
            return True

    return False


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

    # Contract call exceptions
    elif isinstance(exc, PypechainCallException):
        orig_exception = exc.orig_exception
        if orig_exception is None:
            return False

        # Insufficient liquidity error
        if isinstance(orig_exception, ContractCustomError) and exc.decoded_error == "InsufficientLiquidity()":
            return True

        # Circuit breaker triggered error
        if isinstance(orig_exception, ContractCustomError) and exc.decoded_error == "CircuitBreakerTriggered()":
            return True

        # DistributeExcessIdle error
        if isinstance(orig_exception, ContractCustomError) and exc.decoded_error == "DistributeExcessIdleFailed()":
            return True

        # MinimumTransactionAmount error
        if isinstance(orig_exception, ContractCustomError) and exc.decoded_error == "MinimumTransactionAmount()":
            return True

        # DecreasedPresentValueWhenAddingLiquidity error
        if (
            isinstance(orig_exception, ContractCustomError)
            and exc.decoded_error == "DecreasedPresentValueWhenAddingLiquidity()"
        ):
            return True

        # Closing long results in fees exceeding long proceeds
        if len(exc.args) > 1 and "Closing the long results in fees exceeding long proceeds" in exc.args[0]:
            return True

        # Status == 0
        if (
            isinstance(orig_exception, FailedTransaction)
            and len(orig_exception.args) > 0
            and "Receipt has status of 0" in orig_exception.args[0]
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

    if parsed_args.db_port < 0:
        db_port = 2222
    else:
        db_port = parsed_args.db_port

    chain_config = LocalChain.Config(
        chain_host=chain_host,
        chain_port=chain_port,
        db_port=db_port,
        log_level_threshold=logging.WARNING,
        preview_before_trade=True,
        log_to_rollbar=log_to_rollbar,
        rollbar_log_prefix="forkfuzzbots",
        rollbar_log_filter_func=_fuzz_ignore_logging_to_rollbar,
        rng=rng,
        crash_log_level=logging.ERROR,
        crash_report_additional_info={"rng_seed": rng_seed},
        gas_limit=int(3e6),  # Plenty of gas limit for transactions
        # In order to accrue interest correctly, mining a block on the fork must not advance time.
        # We advance time manually when fuzzing.
        # This option will mine blocks based on real time.
        block_timestamp_interval=None,
    )

    while True:
        # Build interactive local hyperdrive
        chain = LocalChain(fork_uri=rpc_uri, config=chain_config)

        chain_id = chain.chain_id
        # Select whale account based on chain id
        if chain_id in WHALE_ADDRESSES:
            # Ensure all whale account addresses are checksum addresses
            whale_accounts = {
                Web3.to_checksum_address(key): Web3.to_checksum_address(value)
                for key, value in WHALE_ADDRESSES[chain_id].items()
            }
        else:
            whale_accounts = {}

        # Get list of deployed pools on initial iteration
        deployed_pools = LocalHyperdrive.get_hyperdrive_pools_from_registry(chain, registry_address)

        log_message = f"Running fuzzing on pools {[p.name for p in deployed_pools]}..."
        logging.info(log_message)
        log_rollbar_message(message=log_message, log_level=logging.INFO)
        # Check for new pools
        latest_block = chain.block_data()
        latest_block_number = latest_block.get("number", None)
        if latest_block_number is None:
            raise AssertionError("Block has no number.")

        # We run fuzzbots for every num_iterations_per_episode,
        # after which we will refork and restart.
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
                random_advance_time=True,
                random_variable_rate=False,
                lp_share_price_test=False,
                base_budget_per_bot=FixedPoint(1_000),
                whale_accounts=whale_accounts,
                num_iterations=parsed_args.num_iterations_per_episode,
                accrue_interest_func=accrue_interest_fork,
                accrue_interest_rate=FixedPoint(0.05),
            )
        except Exception as e:  # pylint: disable=broad-except
            raise e
            log_rollbar_exception(
                rollbar_log_prefix="Fork FuzzBot: Unexpected error", exception=e, log_level=logging.ERROR
            )
            if parsed_args.pause_on_invariance_fail:
                logging.error(
                    "Pausing pool (chain:%s port:%s) on crash %s",
                    chain.name,
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
    db_port: int
    rpc_uri: str
    rng_seed: int
    num_iterations_per_episode: int


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
        db_port=namespace.db_port,
        rpc_uri=namespace.rpc_uri,
        rng_seed=namespace.rng_seed,
        num_iterations_per_episode=namespace.num_iterations_per_episode,
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
        "--db-port",
        type=int,
        default=-1,
        help="The port to run the postgres db on.",
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
    parser.add_argument(
        "--num-iterations-per-episode",
        default=300,
        help="The number of iterations to run for each random pool config.",
    )

    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv

    return namespace_to_args(parser.parse_args())


if __name__ == "__main__":
    main()

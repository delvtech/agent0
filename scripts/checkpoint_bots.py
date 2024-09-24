"""A checkpoint bot for Hyperdrive"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import logging
import os
import random
import sys
import threading
from functools import partial
from typing import NamedTuple, Sequence

from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from fixedpointmath import FixedPoint
from hyperdrivetypes import IHyperdriveContract
from web3 import Web3
from web3.types import Nonce

from agent0 import Chain, Hyperdrive
from agent0.core.base.make_key import make_private_key
from agent0.ethpy.base import get_account_balance, smart_contract_preview_transaction, smart_contract_transact
from agent0.ethpy.hyperdrive import get_hyperdrive_pool_config, get_hyperdrive_registry_from_artifacts
from agent0.ethpy.hyperdrive.interface._event_logs import EARLIEST_BLOCK_LOOKUP
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar, log_rollbar_exception, log_rollbar_message

# Checkpoint bot has a lot going on
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements

# The portion of the checkpoint that the bot will wait before attempting to
# mint a new checkpoint.
CHECKPOINT_WAITING_PERIOD = 0.5

# The threshold for warning low funds
# This variable is keyed by the chain id, valued with the threshold
# we should warn at.
# If not defined, it will default to `FixedPoint(0.1)`
DEFAULT_CHECKPOINT_BOT_LOW_ETH_THRESHOLD = FixedPoint(0.1)
CHECKPOINT_BOT_LOW_ETH_THRESHOLD = {
    # Linea
    59144: FixedPoint(0.01),
    # Base
    8453: FixedPoint(0.01),
}


FAIL_COUNT_THRESHOLD = 10


# Sets up async nonce manager
CURRENT_NONCE: int  # This global variable gets initialized in `main`
NONCE_LOCK = threading.Lock()


def async_get_nonce(web3: Web3, account: LocalAccount) -> Nonce:
    """Handles getting nonce from multiple threads.

    Arguments
    ---------
    web3: Web3
        The web3 instance.
    account: LocalAccount
        The account to get the nonce from.

    Returns
    -------
    int
        The nonce to use.

    """
    # Reference global variable here for handling nonce
    global CURRENT_NONCE  # pylint: disable=global-statement

    with NONCE_LOCK:
        base_nonce = web3.eth.get_transaction_count(account.address, "latest")
        if base_nonce > CURRENT_NONCE:
            out_nonce = base_nonce
            CURRENT_NONCE = base_nonce + 1
        else:
            out_nonce = CURRENT_NONCE
            CURRENT_NONCE += 1

    return Nonce(out_nonce)


def async_reset_nonce() -> None:
    """Resets the internal nonce counter."""
    # Reference global variable here for handling nonce
    global CURRENT_NONCE  # pylint: disable=global-statement

    with NONCE_LOCK:
        CURRENT_NONCE = 0


def does_checkpoint_exist(hyperdrive_contract: IHyperdriveContract, checkpoint_time: int) -> bool:
    """Checks whether or not a given checkpoint exists.

    Arguments
    ---------
    hyperdrive_contract: IHyperdriveContract
        The hyperdrive contract.
    checkpoint_time: int
        The checkpoint time in epoch seconds.

    Returns
    -------
    bool
        Whether or not the checkpoint exists.
    """
    checkpoint = hyperdrive_contract.functions.getCheckpoint(checkpoint_time).call()
    logging.info("%s", checkpoint)
    return checkpoint.vaultSharePrice > 0


async def run_checkpoint_bot(
    chain: Chain,
    pool_address: ChecksumAddress,
    sender: LocalAccount,
    pool_name: str,
    block_time: int = 1,
    block_timestamp_interval: int = 1,
    check_checkpoint: bool = False,
    block_to_exit: int | None = None,
    log_to_rollbar=False,
):
    """Runs the checkpoint bot.

    Arguments
    ---------
    chain: Chain
        The chain object.
    pool_address: ChecksumAddress
        The pool address.
    sender: LocalAccount
        The sender of the transaction.
    pool_name: str
        The name of the pool from `get_hyperdrive_addresses_from_registry`. Only used in logging.
    block_time: int
        The block time in seconds.
    block_timestamp_interval: int
        The block timestamp interval in seconds.
    check_checkpoint: bool
        Whether or not to check the checkpoint after it's been made.
    block_to_exit: int | None
        The block number to exit the loop.
    log_to_rollbar: bool
        Whether or not to log to rollbar.
    """
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-positional-arguments

    # TODO pull this function out and put into agent0
    web3 = chain._web3  # pylint: disable=protected-access

    hyperdrive_contract: IHyperdriveContract = IHyperdriveContract.factory(w3=web3)(pool_address)

    # Run the checkpoint bot. This bot will attempt to mint a new checkpoint
    # every checkpoint after a waiting period. It will poll very infrequently
    # to reduce the probability of needing to mint a checkpoint.
    config = get_hyperdrive_pool_config(hyperdrive_contract)
    checkpoint_duration = config.checkpoint_duration

    # Rollbar assumes any number longer than 2 integers is "data" and groups them together.
    # We want to ensure that the pool name is always in different groups, so we add
    # an underscore to any integers within the position duration string.
    # e.g.
    # `ERC4626Hyperdrive_14day` -> `ERC4_6_2_6_Hyperdrive_1_4_day`
    # `RETHHyperdrive_30day` -> `RETHHyperdrive_3_0_day`
    # TODO this might be done better on the rollbar side with creating a grouping fingerprint
    # TODO ERC4626 gets split up here, may want to only do this for the position duration string.
    pool_name = "".join([c + "_" if c.isdigit() else c for c in pool_name])

    fail_count = 0

    while True:
        # Check if we've reached the block to exit
        if block_to_exit is not None and chain.block_number() >= block_to_exit:
            logging.info("Exiting checkpoint bot...")
            break

        # We check for low funds in checkpoint bot
        chain_id = chain._web3.eth.chain_id  # pylint: disable=protected-access
        checkpoint_bot_eth_balance = FixedPoint(scaled_value=get_account_balance(web3, sender.address))
        if checkpoint_bot_eth_balance <= CHECKPOINT_BOT_LOW_ETH_THRESHOLD.get(
            chain_id, DEFAULT_CHECKPOINT_BOT_LOW_ETH_THRESHOLD
        ):
            log_rollbar_message(
                message=f"Low funds in checkpoint bot: {checkpoint_bot_eth_balance=}",
                log_level=logging.WARNING,
            )

        # Get the latest block time and check to see if a new checkpoint should
        # be minted. This bot waits for a portion of the checkpoint to reduce
        # the probability of needing a checkpoint. After the waiting period,
        # the bot will attempt to mint a checkpoint.
        latest_block = chain.block_data()
        timestamp = latest_block.get("timestamp", None)
        if timestamp is None:
            raise AssertionError(f"{latest_block=} has no timestamp")
        checkpoint_portion_elapsed = timestamp % checkpoint_duration
        checkpoint_time = timestamp - timestamp % checkpoint_duration
        enough_time_has_elapsed = checkpoint_portion_elapsed >= CHECKPOINT_WAITING_PERIOD * checkpoint_duration
        checkpoint_doesnt_exist = not does_checkpoint_exist(hyperdrive_contract, checkpoint_time)

        logging_str = (
            f"Pool {pool_name} for checkpointTime={checkpoint_time}: "
            "Checking if checkpoint needed. "
            f"{timestamp=} {checkpoint_portion_elapsed=} "
            f"{checkpoint_bot_eth_balance=}"
        )
        logging.info(logging_str)

        # Check to see if the pool is paused. We don't run checkpoint bots on this pool if it's paused.
        pause_events = hyperdrive_contract.events.PauseStatusUpdated.get_logs(
            from_block=EARLIEST_BLOCK_LOOKUP.get(chain_id, "earliest")
        )
        is_paused = False
        if len(list(pause_events)) > 0:
            # Get the latest pause event
            # TODO get_logs likely returns events in an ordered
            # fashion, but we iterate and find the latest one
            # just in case
            latest_pause_event = None
            max_block_number = 0
            for event in pause_events:
                if event["blockNumber"] > max_block_number:
                    max_block_number = event["blockNumber"]
                    latest_pause_event = event
            assert latest_pause_event is not None
            is_paused = latest_pause_event["args"]["isPaused"]

        if enough_time_has_elapsed and checkpoint_doesnt_exist and not is_paused:
            logging_str = f"Pool {pool_name} for {checkpoint_time=}: submitting checkpoint"
            logging.info(logging_str)

            # To prevent race conditions with the checkpoint bot submitting transactions
            # for multiple pools simultaneously, we wait a random amount of time before
            # actually submitting a checkpoint
            await asyncio.sleep(random.uniform(0, 5))

            # TODO: We will run into issues with the gas price being too low
            # with testnets and mainnet. When we get closer to production, we
            # will need to make this more robust so that we retry this
            # transaction if the transaction gets stuck.
            try:
                # 0 is the max iterations for distribute excess idle, where it will default to
                # the default max iterations
                fn_args = (checkpoint_time, 0)

                # Try preview call
                _ = smart_contract_preview_transaction(
                    hyperdrive_contract,
                    sender.address,
                    "checkpoint",
                    *fn_args,
                )

                receipt = smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    sender,
                    "checkpoint",
                    *fn_args,
                    nonce_func=partial(async_get_nonce, web3, sender),
                )
                # Reset fail count on successful transaction
                fail_count = 0

            # Catch all errors here and retry next iteration
            except Exception as e:  # pylint: disable=broad-except
                if fail_count < FAIL_COUNT_THRESHOLD:
                    logging_str = "Checkpoint transaction failed."
                    log_level = logging.WARNING
                else:
                    logging_str = f"Checkpoint transaction failed over {FAIL_COUNT_THRESHOLD} times."
                    log_level = logging.CRITICAL
                term_logging_str = logging_str + f" {repr(e)}"
                logging.log(log_level, term_logging_str)

                if log_to_rollbar:
                    log_rollbar_exception(
                        exception=e,
                        log_level=log_level,
                        rollbar_log_prefix=f"Pool {pool_name} for {checkpoint_time=}: {logging_str}",
                    )

                # If any transaction or preview failed, we reset our global nonce counter and depend on the chain's
                # counter on the next iteration.
                async_reset_nonce()

                fail_count += 1
                continue
            logging_str = (
                f"Pool {pool_name} for {checkpoint_time=}: "
                f"Checkpoint successfully mined with transaction_hash={receipt['transactionHash'].hex()}"
            )
            logging.info(logging_str)
            if log_to_rollbar:
                log_rollbar_message(
                    message=logging_str,
                    log_level=logging.INFO,
                )

            if check_checkpoint:
                # TODO: Add crash report
                assert receipt["status"] == 1, "Checkpoint failed."
                latest_block = chain.block_data()
                timestamp = latest_block.get("timestamp", None)
                if timestamp is None:
                    raise AssertionError(f"{latest_block=} has no timestamp")
                checkpoint_portion_elapsed = timestamp % checkpoint_duration
                checkpoint_time = timestamp - timestamp % checkpoint_duration

                enough_time_has_elapsed = checkpoint_portion_elapsed >= CHECKPOINT_WAITING_PERIOD * checkpoint_duration
                assert not enough_time_has_elapsed, "We shouldn't need a checkpoint if one was just created."

                checkpoint_exists = does_checkpoint_exist(hyperdrive_contract, checkpoint_time)
                assert checkpoint_exists, "Checkpoint should exist since it was just made."

        # Sleep for enough time that the block timestamp would have advanced
        # far enough to consider minting a new checkpoint.
        if checkpoint_portion_elapsed >= CHECKPOINT_WAITING_PERIOD * checkpoint_duration:
            sleep_duration = checkpoint_duration * (1 + CHECKPOINT_WAITING_PERIOD) - checkpoint_portion_elapsed
        else:
            sleep_duration = checkpoint_duration * CHECKPOINT_WAITING_PERIOD - checkpoint_portion_elapsed
        # Adjust sleep duration by the speedup factor
        adjusted_sleep_duration = sleep_duration / (block_timestamp_interval / block_time)
        logging_str = (
            f"Pool {pool_name}: Current time is {datetime.datetime.fromtimestamp(timestamp)}. "
            f"Sleeping for {adjusted_sleep_duration} seconds."
        )
        logging.info(logging_str)
        # No need to log sleeping info to rollbar here

        await asyncio.sleep(adjusted_sleep_duration)


async def main(argv: Sequence[str] | None = None) -> None:
    """Runs the checkpoint bot.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    # pylint: disable=too-many-branches

    # We reference the global variable here, and initialize this variable
    global CURRENT_NONCE  # pylint: disable=global-statement
    CURRENT_NONCE = 0

    parsed_args = parse_arguments(argv)

    rollbar_environment_name = "checkpoint_bot"
    log_to_rollbar = initialize_rollbar(rollbar_environment_name)

    # Initialize
    registry_address_env = None
    if parsed_args.infra:
        # TODO Abstract this method out for infra scripts
        # Get the rpc uri from env variable
        rpc_uri = os.getenv("RPC_URI", None)
        if rpc_uri is None:
            raise ValueError("RPC_URI is not set")

        chain = Chain(rpc_uri, Chain.Config(no_postgres=True))

        # Get the registry address from environment variable
        registry_address_env = os.getenv("REGISTRY_ADDRESS", None)
        if registry_address_env is None or registry_address_env == "":
            # If env is not set, get the registry address from artifacts
            artifacts_uri = os.getenv("ARTIFACTS_URI", None)
            if artifacts_uri is None:
                raise ValueError("ARTIFACTS_URI must be set if registry address is not set.")
            registry_address = get_hyperdrive_registry_from_artifacts(artifacts_uri)
        else:
            registry_address = registry_address_env

        # Get block time and block timestamp interval from env vars
        block_time = int(os.getenv("BLOCK_TIME", "12"))
        block_timestamp_interval = int(os.getenv("BLOCK_TIMESTAMP_INTERVAL", "12"))
    else:
        chain = Chain(parsed_args.rpc_uri, Chain.Config(no_postgres=True))
        registry_address = parsed_args.registry_addr
        block_time = 1
        block_timestamp_interval = 1

    # Look for `CHECKPOINT_BOT_KEY` env variable
    # If it exists, use the existing key and assume it's funded
    # If it doesn't exist, create a new key and fund it (assuming this is a local anvil chain)
    private_key = os.getenv("CHECKPOINT_BOT_KEY", None)
    if private_key is None or private_key == "":
        # Guardrail to make sure this isn't ran on non-local chain
        if registry_address_env is not None and registry_address_env != "":
            raise ValueError(
                "Refusing to run without `CHECKPOINT_BOT_KEY` with an explicit registry address. "
                "Need to provide `CHECKPOINT_BOT_KEY` if running on remote chain."
            )
        private_key = make_private_key()
        # We create an agent here to fund it eth
        agent = chain.init_agent(private_key=private_key)
        agent.add_funds(eth=FixedPoint(100_000))
        sender: LocalAccount = agent.account
    else:
        sender: LocalAccount = Account().from_key(private_key)

    # Loop for checkpoint bot across all registered pools
    while True:
        logging.info("Checking for new pools...")
        # Reset hyperdrive objs
        deployed_pools = Hyperdrive.get_hyperdrive_addresses_from_registry(chain, registry_address)

        # pylint: disable=protected-access
        checkpoint_bot_eth_balance = FixedPoint(scaled_value=get_account_balance(chain._web3, sender.address))
        log_message = f"Running checkpoint bots for pools {list(deployed_pools.keys())}. {checkpoint_bot_eth_balance=}"
        logging.info(log_message)
        log_rollbar_message(message=log_message, log_level=logging.INFO)

        block_to_exit = chain.block_number() + parsed_args.pool_check_sleep_blocks
        # NOTE we can't run these in background threads, because
        # checkpoint bots will never execute past the number of threads available
        # on a machine. Hence, we need `run_checkpoint_bot` to do non-blocking waits.
        _ = await asyncio.gather(
            *[
                run_checkpoint_bot(
                    chain=chain,
                    pool_address=pool_addr,
                    sender=sender,
                    pool_name=pool_name,
                    block_time=block_time,
                    block_timestamp_interval=block_timestamp_interval,
                    block_to_exit=block_to_exit,
                    log_to_rollbar=log_to_rollbar,
                )
                for pool_name, pool_addr in deployed_pools.items()
            ],
            return_exceptions=False,
        )


class Args(NamedTuple):
    """Command line arguments for the checkpoint bot."""

    pool_check_sleep_blocks: int
    infra: bool
    registry_addr: str
    rpc_uri: str


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
        pool_check_sleep_blocks=namespace.pool_check_sleep_blocks,
        infra=namespace.infra,
        registry_addr=namespace.registry_addr,
        rpc_uri=namespace.rpc_uri,
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
    parser = argparse.ArgumentParser(description="Runs a bot that creates checkpoints each checkpoint_duration.")
    parser.add_argument(
        "--pool-check-sleep-blocks",
        type=int,
        default=7200,  # 1 day for 12 second block time
        help="Number of blocks in between checking for new pools.",
    )

    parser.add_argument(
        "--infra",
        default=False,
        action="store_true",
        help="Infra mode, we get registry address from artifacts, and we fund a random account with eth as sender.",
    )

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

    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv
    return namespace_to_args(parser.parse_args())


# Run the checkpoint bot.
if __name__ == "__main__":
    # Wrap everything in a try catch to log any non-caught critical errors and log to rollbar
    try:
        asyncio.run(main())
    except Exception as exc:
        log_rollbar_exception(
            exception=exc, log_level=logging.CRITICAL, rollbar_log_prefix="Uncaught Critical Error in Checkpoint Bot:"
        )
        raise exc

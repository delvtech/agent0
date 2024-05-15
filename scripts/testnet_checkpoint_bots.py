"""A checkpoint bot for Hyperdrive"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import logging
import os
import sys
import time
from functools import partial
from typing import NamedTuple, Sequence

from eth_account.account import Account
from eth_typing import ChecksumAddress

from agent0 import Chain, Hyperdrive
from agent0.core.base import PolicyAgent
from agent0.ethpy.base import smart_contract_transact
from agent0.ethpy.hyperdrive import get_hyperdrive_pool_config
from agent0.hyperfuzz.system_fuzz.run_local_fuzz_bots import async_runner
from agent0.hypertypes import IHyperdriveContract

# Checkpoint bot has a lot going on
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements

# The portion of the checkpoint that the bot will wait before attempting to
# mint a new checkpoint.
CHECKPOINT_WAITING_PERIOD = 0.5


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


def run_checkpoint_bot(
    chain: Chain,
    pool_address: ChecksumAddress,
    sender: PolicyAgent,
    block_time: int = 1,
    block_timestamp_interval: int = 1,
    check_checkpoint: bool = False,
    block_to_exit: int | None = None,
    pool_name: str | None = None,
):
    """Runs the checkpoint bot.

    Arguments
    ---------
    chain: Chain
        The chain object.
    pool_address: ChecksumAddress
        The pool address.
    sender: PolicyAgent
        The sender of the transaction.
    block_time: int
        The block time in seconds.
    block_timestamp_interval: int
        The block timestamp interval in seconds.
    check_checkpoint: bool
        Whether or not to check the checkpoint after it's been made.
    block_to_exit: int | None
        The block number to exit the loop.
    pool_name: str | None
        The name of the pool. Only used for logging
    """
    # pylint: disable=too-many-arguments

    # TODO pull this function out and put into agent0, and use this function in
    # the infra version of checkpoint bot
    web3 = chain._web3  # pylint: disable=protected-access

    hyperdrive_contract: IHyperdriveContract = IHyperdriveContract.factory(w3=web3)(pool_address)

    # Run the checkpoint bot. This bot will attempt to mint a new checkpoint
    # every checkpoint after a waiting period. It will poll very infrequently
    # to reduce the probability of needing to mint a checkpoint.
    config = get_hyperdrive_pool_config(hyperdrive_contract)
    checkpoint_duration = config.checkpoint_duration

    while True:
        # Check if we've reached the block to exit
        if block_to_exit is not None and chain.block_number() >= block_to_exit:
            logging.info("Exiting checkpoint bot...")
            break

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

        logging.info(
            "pool_name=%s "
            "timestamp=%s checkpoint_portion_elapsed=%s checkpoint_time=%s "
            "need_checkpoint=%s checkpoint_doesnt_exist=%s",
            pool_name,
            timestamp,
            checkpoint_portion_elapsed,
            checkpoint_time,
            enough_time_has_elapsed,
            checkpoint_doesnt_exist,
        )

        if enough_time_has_elapsed and checkpoint_doesnt_exist:
            logging.info("Pool %s submitting a checkpoint for checkpointTime=%s...", pool_name, checkpoint_time)
            # TODO: We will run into issues with the gas price being too low
            # with testnets and mainnet. When we get closer to production, we
            # will need to make this more robust so that we retry this
            # transaction if the transaction gets stuck.
            try:
                # 0 is the max iterations for distribute excess idle, where it will default to
                # the default max iterations
                fn_args = (checkpoint_time, 0)
                receipt = smart_contract_transact(
                    web3,
                    hyperdrive_contract,
                    sender,
                    "checkpoint",
                    *fn_args,
                )
            except Exception as e:  # pylint: disable=broad-except
                logging.warning("Checkpoint transaction failed with exception=%s, retrying", e)
                # Catch all errors here and retry next iteration
                # TODO adjust wait period
                time.sleep(1)
                continue
            logging.info(
                "Checkpoint successfully mined with receipt=%s",
                receipt["transactionHash"].hex(),
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
        logging.info(
            "Pool name %s. Current time is %s. Sleeping for %s seconds ...",
            pool_name,
            datetime.datetime.fromtimestamp(timestamp),
            adjusted_sleep_duration,
        )
        time.sleep(adjusted_sleep_duration)


def main(argv: Sequence[str] | None = None) -> None:
    """Runs the checkpoint bot.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    # pylint: disable=too-many-branches

    parsed_args = parse_arguments(argv)

    # Initialize
    chain = Chain(parsed_args.rpc_uri)

    # We calculate how many blocks we should wait before checking for a new pool
    pool_check_num_blocks = parsed_args.pool_check_sleep_time // 12

    private_key = os.getenv("CHECKPOINT_BOT_KEY")
    sender = PolicyAgent(Account().from_key(private_key))

    while True:
        logging.info("Checking for new pools...")
        # Reset hyperdrive objs
        deployed_pools = Hyperdrive.get_hyperdrive_addresses_from_registry(chain, parsed_args.registry_addr)

        logging.info("Running for all pools...")

        # TODO because _async_runner only takes one set of arguments for all calls,
        # we make partial calls for each call. The proper fix here is to generalize
        # _async_runner to take separate arguments for each call.
        partials = [
            partial(run_checkpoint_bot, pool_address=pool_addr, pool_name=pool_name)
            for pool_name, pool_addr in deployed_pools.items()
        ]

        # Run checkpoint bots
        # We set return_exceptions to False to crash immediately if a thread fails
        asyncio.run(
            async_runner(
                return_exceptions=False,
                funcs=partials,
                chain=chain,
                sender=sender,
                block_to_exit=chain.block_number() + pool_check_num_blocks,
            )
        )


class Args(NamedTuple):
    """Command line arguments for the checkpoint bot."""

    pool_check_sleep_time: int
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
        pool_check_sleep_time=namespace.pool_check_sleep_time,
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
        "--pool-check-sleep-time",
        type=int,
        default=86400,  # 1 day
        help="Sleep time between checking for new pools, in seconds.",
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
    main()

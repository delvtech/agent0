"""A checkpoint bot for Hyperdrive"""

from __future__ import annotations

import argparse
import datetime
import logging
import os
import sys
import time
from typing import NamedTuple, Sequence

from eth_account.account import Account
from ethpy import EthConfig, build_eth_config
from ethpy.base import initialize_web3_with_http_provider, set_anvil_account_balance, smart_contract_transact
from ethpy.hyperdrive import fetch_hyperdrive_address_from_uri, get_hyperdrive_pool_config
from fixedpointmath import FixedPoint
from hyperlogs import setup_logging
from hypertypes import IERC4626HyperdriveContract

from agent0.base.agents import EthAgent
from agent0.base.config import EnvironmentConfig

# Checkpoint bot has a lot going on
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements

# The portion of the checkpoint that the bot will wait before attempting to
# mint a new checkpoint.
CHECKPOINT_WAITING_PERIOD = 0.5


def does_checkpoint_exist(hyperdrive_contract: IERC4626HyperdriveContract, checkpoint_time: int) -> bool:
    """Checks whether or not a given checkpoint exists.

    Arguments
    ---------
    hyperdrive_contract: IERC4626HyperdriveContract
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
    return checkpoint.sharePrice > 0


def get_config() -> tuple[EthConfig, EnvironmentConfig]:
    """Gets the hyperdrive configuration.

    Returns
    -------
    tuple[EthConfig, EnvironmentConfig]
        The output EthConfig and EnvironmentConfig objects.
    """
    # Get the configuration and initialize the web3 provider.
    eth_config = build_eth_config()

    # The configuration for the checkpoint bot halts on errors and logs to stdout.
    env_config = EnvironmentConfig(
        # Errors
        halt_on_errors=True,
        # Logging
        log_stdout=True,
        log_level=logging.INFO,
    )
    return (eth_config, env_config)


def main(argv: Sequence[str] | None = None) -> None:
    """Runs the checkpoint bot.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    parsed_args = parse_arguments(argv)
    eth_config, env_config = get_config()

    # Get environment variables for block time and block timestamp interval
    # TODO can't seem to get block time or block timestamp interval from anvil, so we get env vars passed in here
    # Real time, passed in anvil as `--block-time`
    block_time = os.environ.get("BLOCK_TIME")
    if block_time is None:
        block_time = 1
    else:
        block_time = int(block_time)
    # Interval between blocks, passed in anvil through RPC `anvil_setBlockTimestampInterval`
    block_timestamp_interval = os.environ.get("BLOCK_TIMESTAMP_INTERVAL")
    if block_timestamp_interval is None:
        block_timestamp_interval = 1
    else:
        block_timestamp_interval = int(block_timestamp_interval)

    web3 = initialize_web3_with_http_provider(eth_config.rpc_uri, reset_provider=False)

    # Setup logging
    setup_logging(
        log_filename=env_config.log_filename,
        max_bytes=env_config.max_bytes,
        log_level=env_config.log_level,
        delete_previous_logs=env_config.delete_previous_logs,
        log_stdout=env_config.log_stdout,
        log_format_string=env_config.log_formatter,
    )

    # Fund the checkpoint sender with some ETH.
    balance = FixedPoint(100).scaled_value
    sender = EthAgent(Account().create("CHECKPOINT_BOT"))
    set_anvil_account_balance(web3, sender.address, balance)
    logging.info("Successfully funded the sender=%s.", sender.address)

    # Get the Hyperdrive contract.
    # TODO replace this with the hyperdrive interface
    addresses = fetch_hyperdrive_address_from_uri(os.path.join(eth_config.artifacts_uri, "addresses.json"))
    hyperdrive_contract_address = web3.to_checksum_address(addresses.erc4626_hyperdrive)
    hyperdrive_contract: IERC4626HyperdriveContract = IERC4626HyperdriveContract.factory(w3=web3)(
        hyperdrive_contract_address
    )

    # Run the checkpoint bot. This bot will attempt to mint a new checkpoint
    # every checkpoint after a waiting period. It will poll very infrequently
    # to reduce the probability of needing to mint a checkpoint.
    config = get_hyperdrive_pool_config(hyperdrive_contract)
    checkpoint_duration = config.checkpoint_duration

    logging.info(
        "Checkpoint Duration: %s; Block time: %s; Block timestamp interval: %s",
        checkpoint_duration,
        block_time,
        block_timestamp_interval,
    )

    while True:
        # Get the latest block time and check to see if a new checkpoint should
        # be minted. This bot waits for a portion of the checkpoint to reduce
        # the probability of needing a checkpoint. After the waiting period,
        # the bot will attempt to mint a checkpoint.
        latest_block = web3.eth.get_block("latest")
        timestamp = latest_block.get("timestamp", None)
        if timestamp is None:
            raise AssertionError(f"{latest_block=} has no timestamp")
        checkpoint_portion_elapsed = timestamp % checkpoint_duration
        checkpoint_time = timestamp - timestamp % checkpoint_duration
        enough_time_has_elapsed = checkpoint_portion_elapsed >= CHECKPOINT_WAITING_PERIOD * checkpoint_duration
        checkpoint_doesnt_exist = not does_checkpoint_exist(hyperdrive_contract, checkpoint_time)

        logging.info(
            "timestamp=%s checkpoint_portion_elapsed=%s checkpoint_time=%s "
            "need_checkpoint=%s checkpoint_doesnt_exist=%s",
            timestamp,
            checkpoint_portion_elapsed,
            checkpoint_time,
            enough_time_has_elapsed,
            checkpoint_doesnt_exist,
        )

        if enough_time_has_elapsed and checkpoint_doesnt_exist:
            logging.info("Submitting a checkpoint for checkpointTime=%s...", checkpoint_time)
            # TODO: We will run into issues with the gas price being too low
            # with testnets and mainnet. When we get closer to production, we
            # will need to make this more robust so that we retry this
            # transaction if the transaction gets stuck.
            receipt = smart_contract_transact(
                web3,
                hyperdrive_contract,
                sender,
                "checkpoint",
                (checkpoint_time),
            )
            logging.info(
                "Checkpoint successfully mined with receipt=%s",
                receipt["transactionHash"].hex(),
            )
            if parsed_args.fuzz:
                # TODO: Add crash report
                assert receipt["status"] == 1, "Checkpoint failed."
                latest_block = web3.eth.get_block("latest")
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
            "Current time is %s. Sleeping for %s seconds ...",
            datetime.datetime.fromtimestamp(timestamp),
            adjusted_sleep_duration,
        )
        time.sleep(adjusted_sleep_duration)


class Args(NamedTuple):
    """Command line arguments for the checkpoint bot."""

    fuzz: bool


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
    return Args(fuzz=namespace.fuzz)


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
        "--fuzz",
        type=bool,
        default=False,
        help="If true, then add an assertion step to verify that the checkpoint was successful.",
    )
    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv
    return namespace_to_args(parser.parse_args())


# Run the checkpoint bot.
if __name__ == "__main__":
    main()

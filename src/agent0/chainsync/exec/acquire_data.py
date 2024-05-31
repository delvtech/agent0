"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""

from __future__ import annotations

import logging
import time
from typing import Callable

from eth_typing import BlockNumber, ChecksumAddress
from sqlalchemy.orm import Session

from agent0.chainsync import PostgresConfig
from agent0.chainsync.db.base import initialize_session
from agent0.chainsync.db.hyperdrive import (
    add_hyperdrive_addr_to_name,
    data_chain_to_db,
    get_latest_block_number_from_pool_info_table,
    init_data_chain_to_db,
)
from agent0.ethpy.hyperdrive import HyperdriveReadInterface

_SLEEP_AMOUNT = 1


# TODO cleanup
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
def acquire_data(
    start_block: int = 0,
    lookback_block_limit: int = 1000,
    interfaces: list[HyperdriveReadInterface] | None = None,
    rpc_uri: str | None = None,
    hyperdrive_addresses: list[ChecksumAddress] | dict[str, ChecksumAddress] | None = None,
    db_session: Session | None = None,
    postgres_config: PostgresConfig | None = None,
    exit_on_catch_up: bool = False,
    exit_callback_fn: Callable[[], bool] | None = None,
    suppress_logs: bool = False,
):
    """Execute the data acquisition pipeline.

    Arguments
    ---------
    start_block: int
        The starting block to filter the query on
    lookback_block_limit: int
        The maximum number of blocks to look back when filling in missing data
    interfaces: list[HyperdriveReadInterface] | None, optional
        A collection of Hyperdrive interface objects, each connected to a pool.
        If not set, will initialize one based on rpc_uri and hyperdrive_address.
    rpc_uri: str, optional
        The URI for the web3 provider to initialize the interface with. Not used if an interface
        is provided.
    hyperdrive_addresses: list[ChecksumAddress] | dict[str, ChecksumAddress] | None, optional
        A collection of Hyperdrive address, each pointing to an initialized pool.
        Can also be the output of `get_hyperdrive_addresses_from_registry`, which is a
        dictionary keyed by a logical name and a value of a hyperdrive address.
        If it's a dictionary, will add this mapping to the database.
        Not used if a list of interfaces is provided.
    db_session: Session | None
        Session object for connecting to db. If None, will initialize a new session based on
        postgres_config.
    postgres_config: PostgresConfig | None = None,
        PostgresConfig for connecting to db. If none, will set from .env.
    exit_on_catch_up: bool, optional
        If True, will exit after catching up to current block. Defaults to False.
    exit_callback_fn: Callable[[], bool] | None, optional
        A function that returns a boolean to call to determine if the script should exit.
        The function should return False if the script should continue, or True if the script should exit.
        Defaults to not set.
    suppress_logs: bool, optional
        If true, will suppress info logging from this function. Defaults to False.
    """
    # TODO implement logger instead of global logging to suppress based on module name.

    hyperdrive_name_mapping = None

    ## Initialization
    if interfaces is None:
        if hyperdrive_addresses is None or rpc_uri is None:
            # TODO when we start deploying the registry, this case should look for existing
            # pools in the registry and use those.
            raise ValueError("hyperdrive_address and rpc_uri must be provided if not providing interface")

        if isinstance(hyperdrive_addresses, dict):
            hyperdrive_name_mapping = hyperdrive_addresses
            hyperdrive_addresses = list(hyperdrive_addresses.values())

        interfaces = [
            HyperdriveReadInterface(hyperdrive_address, rpc_uri) for hyperdrive_address in hyperdrive_addresses
        ]

    if len(interfaces) == 0:
        raise ValueError("Must run data on at least one pool.")

    # postgres session
    db_session_init = False
    if db_session is None:
        db_session_init = True
        db_session = initialize_session(postgres_config, ensure_database_created=True)

    # Add mappings if set
    if hyperdrive_name_mapping is not None:
        for hyperdrive_name, hyperdrive_address in hyperdrive_name_mapping.items():
            add_hyperdrive_addr_to_name(hyperdrive_name, hyperdrive_address, db_session)

    ## Get starting point for restarts
    # Get last entry of pool info in db
    data_latest_block_number = get_latest_block_number_from_pool_info_table(db_session)
    # Using max of latest block in database or specified start block
    curr_write_block = max(start_block, data_latest_block_number + 1)

    latest_mined_block = int(interfaces[0].get_block_number(interfaces[0].get_current_block()))
    if (latest_mined_block - curr_write_block) > lookback_block_limit:
        curr_write_block = latest_mined_block - lookback_block_limit
        logging.warning(
            "Starting block is past lookback block limit, starting at block %s",
            curr_write_block,
        )

    ## Collect initial data
    init_data_chain_to_db(interfaces, db_session)

    # Main data loop
    # monitor for new blocks & add pool info per block
    if not suppress_logs:
        logging.info("Monitoring for pool info updates...")
    while True:
        latest_mined_block = interfaces[0].web3.eth.get_block_number()
        # Only execute if we are on a new block
        if latest_mined_block < curr_write_block:
            exit_callable = False
            if exit_callback_fn is not None:
                exit_callable = exit_callback_fn()
            if exit_on_catch_up or exit_callable:
                break
            time.sleep(_SLEEP_AMOUNT)
            continue
        # Backfilling for blocks that need updating
        for block_int in range(curr_write_block, latest_mined_block + 1):
            block_number: BlockNumber = BlockNumber(block_int)
            # Only print every 10 blocks
            if not suppress_logs and (block_number % 10) == 0:
                logging.info("Block %s", block_number)
            # Explicit check against loopback block limit
            if (latest_mined_block - block_number) > lookback_block_limit:
                # NOTE when this case happens, wallet information will no longer
                # be accurate, as we may have missed deltas on wallets
                # based on the blocks we skipped
                # TODO should directly query the chain for open positions
                # in this case
                logging.warning(
                    "Querying block_number %s out of %s, unable to keep up with chain block iteration",
                    block_number,
                    latest_mined_block,
                )
                continue
            data_chain_to_db(interfaces, block_number, db_session)
        curr_write_block = latest_mined_block + 1

    # Clean up resources on clean exit
    # If this function made the db session, we close it here
    if db_session_init:
        db_session.close()

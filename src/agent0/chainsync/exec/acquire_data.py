"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""

from __future__ import annotations

import logging
import time
from typing import Callable

from eth_typing import BlockNumber
from sqlalchemy.orm import Session

from agent0.chainsync import PostgresConfig
from agent0.chainsync.db.base import initialize_session
from agent0.chainsync.db.hyperdrive import (
    data_chain_to_db,
    get_latest_block_number_from_pool_info_table,
    init_data_chain_to_db,
)
from agent0.ethpy import EthConfig
from agent0.ethpy.hyperdrive import HyperdriveAddresses, HyperdriveReadInterface

_SLEEP_AMOUNT = 1


# TODO cleanup
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
def acquire_data(
    start_block: int = 0,
    lookback_block_limit: int = 1000,
    interface: HyperdriveReadInterface | None = None,
    eth_config: EthConfig | None = None,
    db_session: Session | None = None,
    postgres_config: PostgresConfig | None = None,
    contract_addresses: HyperdriveAddresses | None = None,
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
    interface: HyperdriveReadInterface | None, optional
        An initialized HyperdriveReadInterface object. If not set, will initialize one based on
        eth_config and contract_addresses.
    eth_config: EthConfig | None
        Configuration for URIs to the rpc and artifacts. If not set, will look for addresses
        in eth.env.
    db_session: Session | None
        Session object for connecting to db. If None, will initialize a new session based on
        postgres_config.
    postgres_config: PostgresConfig | None = None,
        PostgresConfig for connecting to db. If none, will set from postgres.env.
    contract_addresses: HyperdriveAddresses | None
        If set, will use these addresses instead of querying the artifact URI
        defined in eth_config.
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

    ## Initialization
    if interface is None:
        interface = HyperdriveReadInterface(eth_config, contract_addresses)

    # postgres session
    db_session_init = False
    if db_session is None:
        db_session_init = True
        db_session = initialize_session(postgres_config, ensure_database_created=True)

    ## Get starting point for restarts
    # Get last entry of pool info in db
    data_latest_block_number = get_latest_block_number_from_pool_info_table(db_session)
    # Using max of latest block in database or specified start block
    curr_write_block = max(start_block, data_latest_block_number + 1)

    latest_mined_block = int(interface.get_block_number(interface.get_current_block()))
    if (latest_mined_block - curr_write_block) > lookback_block_limit:
        curr_write_block = latest_mined_block - lookback_block_limit
        logging.warning(
            "Starting block is past lookback block limit, starting at block %s",
            curr_write_block,
        )

    ## Collect initial data
    init_data_chain_to_db(interface, db_session)

    # Main data loop
    # monitor for new blocks & add pool info per block
    if not suppress_logs:
        logging.info("Monitoring for pool info updates...")
    while True:
        latest_mined_block = interface.web3.eth.get_block_number()
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
            data_chain_to_db(interface, interface.get_block(block_number), db_session)
        curr_write_block = latest_mined_block + 1

    # Clean up resources on clean exit
    # If this function made the db session, we close it here
    if db_session_init:
        db_session.close()

"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""
from __future__ import annotations

import logging
import time

from chainsync.db.base import initialize_session
from chainsync.db.hyperdrive import get_latest_block_number_from_pool_info_table
from eth_typing import BlockNumber
from sqlalchemy.orm import Session

_SLEEP_AMOUNT = 1


def data_analysis(
    start_block: int = 0,
    db_session: Session | None = None,
    exit_on_catch_up: bool = False,
):
    """Execute the data acquisition pipeline.

    Arguments
    ---------
    start_block : int
        The starting block to filter the query on
    lookback_block_limit : int
        The maximum number of blocks to look back when filling in missing data
    eth_config: EthConfig | None
        Configuration for urls to the rpc and artifacts. If not set, will look for addresses
        in eth.env.
    db_session: Session | None
        Session object for connecting to db. If None, will initialize a new session based on
        postgres.env.
    contract_addresses: HyperdriveAddresses | None
        If set, will use these addresses instead of querying the artifact url
        defined in eth_config.
    exit_on_catch_up: bool
        If True, will exit after catching up to current block
    """
    # postgres session
    if db_session is None:
        db_session = initialize_session()

    ## Get starting point for restarts
    analysis_latest_block_number = get_latest_block_number_from_analysis(db_session)

    # Using max of latest block in database or specified start block
    block_number: BlockNumber = BlockNumber(max(start_block, analysis_latest_block_number))

    # Main data loop
    # monitor for new blocks & add pool info per block
    logging.info("Monitoring database for updates...")
    while True:
        latest_data_block_number = get_latest_block_number_from_pool_info_table(db_session)
        # Only execute if we are on a new block
        if latest_data_block_number <= block_number:
            time.sleep(_SLEEP_AMOUNT)
            if exit_on_catch_up:
                break
            continue
        # Backfilling for blocks that need updating
        for block_int in range(block_number + 1, latest_data_block_number + 1):
            block_number: BlockNumber = BlockNumber(block_int)
            logging.info("Block %s", block_number)
            data_to_analysis(block_number, db_session)
        time.sleep(_SLEEP_AMOUNT)

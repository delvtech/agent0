"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""
from __future__ import annotations

import logging
import os
import time

from chainsync.db.base import initialize_session
from chainsync.db.hyperdrive import (
    data_chain_to_db,
    get_latest_block_number_from_pool_info_table,
    init_data_chain_to_db,
)
from eth_typing import BlockNumber
from ethpy import EthConfig, build_eth_config
from ethpy.hyperdrive import get_web3_and_hyperdrive_contracts
from sqlalchemy.orm import Session

_SLEEP_AMOUNT = 1


def acquire_data(
    start_block: int,
    lookback_block_limit: int,
    eth_config: EthConfig | None = None,
    overwrite_db_session: Session | None = None,
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
    overwrite_db_session: Session | None
        Session object for connecting to db. If None, will initialize a new session based on
        postgres.env.
    """
    ## Initialization
    # eth config
    if eth_config is None:
        # Load parameters from env vars if they exist
        eth_config = build_eth_config()

    # postgres session
    if overwrite_db_session is not None:
        session = overwrite_db_session
    else:
        session = initialize_session()

    # Get web3 and contracts
    web3, base_contract, hyperdrive_contract = get_web3_and_hyperdrive_contracts(eth_config)

    ## Get starting point for restarts
    # Get last entry of pool info in db
    data_latest_block_number = get_latest_block_number_from_pool_info_table(session)
    # Using max of latest block in database or specified start block
    block_number: BlockNumber = BlockNumber(max(start_block, data_latest_block_number))
    # Make sure to not grab current block, as the current block is subject to change
    # Current block is still being built
    latest_mined_block = web3.eth.get_block_number() - 1
    lookback_block_limit = BlockNumber(lookback_block_limit)

    if (latest_mined_block - block_number) > lookback_block_limit:
        block_number = BlockNumber(latest_mined_block - lookback_block_limit)
        logging.warning("Starting block is past lookback block limit, starting at block %s", block_number)

    # Collect initial data
    init_data_chain_to_db(hyperdrive_contract, session)
    # This if statement executes only on initial run (based on data_latest_block_number check),
    # and if the chain has executed until start_block (based on latest_mined_block check)
    if data_latest_block_number < block_number < latest_mined_block:
        data_chain_to_db(web3, base_contract, hyperdrive_contract, block_number, session)

    # Main data loop
    # monitor for new blocks & add pool info per block
    logging.info("Monitoring for pool info updates...")
    while True:
        latest_mined_block = web3.eth.get_block_number() - 1
        # Only execute if we are on a new block
        if latest_mined_block <= block_number:
            time.sleep(_SLEEP_AMOUNT)
            continue
        # Backfilling for blocks that need updating
        for block_int in range(block_number + 1, latest_mined_block + 1):
            block_number: BlockNumber = BlockNumber(block_int)
            logging.info("Block %s", block_number)
            # Explicit check against loopback block limit
            if (latest_mined_block - block_number) > lookback_block_limit:
                logging.warning(
                    "Querying block_number %s out of %s, unable to keep up with chain block iteration",
                    block_number,
                    latest_mined_block,
                )
                continue
            data_chain_to_db(web3, base_contract, hyperdrive_contract, block_number, session)
        time.sleep(_SLEEP_AMOUNT)

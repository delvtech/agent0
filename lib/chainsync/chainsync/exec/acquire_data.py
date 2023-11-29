"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""
from __future__ import annotations

import logging
import time
import warnings

from eth_typing import BlockNumber
from ethpy import EthConfig
from ethpy.hyperdrive import HyperdriveAddresses
from ethpy.hyperdrive.api import HyperdriveInterface
from sqlalchemy.orm import Session

from chainsync.db.base import initialize_session
from chainsync.db.hyperdrive import (
    data_chain_to_db,
    get_latest_block_number_from_pool_info_table,
    init_data_chain_to_db,
)

_SLEEP_AMOUNT = 1

warnings.filterwarnings("ignore", category=UserWarning, module="web3.contract.base_contract")


# Lots of arguments
# pylint: disable=too-many-arguments
def acquire_data(
    start_block: int = 0,
    lookback_block_limit: int = 1000,
    eth_config: EthConfig | None = None,
    db_session: Session | None = None,
    contract_addresses: HyperdriveAddresses | None = None,
    exit_on_catch_up: bool = False,
):
    """Execute the data acquisition pipeline.

    Arguments
    ---------
    start_block: int
        The starting block to filter the query on
    lookback_block_limit: int
        The maximum number of blocks to look back when filling in missing data
    eth_config: EthConfig | None
        Configuration for URIs to the rpc and artifacts. If not set, will look for addresses
        in eth.env.
    db_session: Session | None
        Session object for connecting to db. If None, will initialize a new session based on
        postgres.env.
    contract_addresses: HyperdriveAddresses | None
        If set, will use these addresses instead of querying the artifact URI
        defined in eth_config.
    exit_on_catch_up: bool
        If True, will exit after catching up to current block
    """
    ## Initialization
    hyperdrive = HyperdriveInterface(eth_config, contract_addresses)
    # postgres session
    if db_session is None:
        db_session = initialize_session()

    ## Get starting point for restarts
    # Get last entry of pool info in db
    data_latest_block_number = get_latest_block_number_from_pool_info_table(db_session)
    # Using max of latest block in database or specified start block
    block_number: BlockNumber = BlockNumber(max(start_block, data_latest_block_number))
    # Make sure to not grab current block, as the current block is subject to change
    # Current block is still being built
    latest_mined_block = hyperdrive.get_block_number(hyperdrive.get_current_block())
    lookback_block_limit = BlockNumber(lookback_block_limit)
    if (latest_mined_block - block_number) > lookback_block_limit:
        block_number = BlockNumber(latest_mined_block - lookback_block_limit)
        logging.warning(
            "Starting block is past lookback block limit, starting at block %s",
            block_number,
        )

    ## Collect initial data
    init_data_chain_to_db(hyperdrive, db_session)
    # This if statement executes only on initial run (based on data_latest_block_number check),
    # and if the chain has executed until start_block (based on latest_mined_block check)
    if data_latest_block_number < block_number < latest_mined_block:
        data_chain_to_db(hyperdrive, hyperdrive.get_block(block_number), db_session)

    # Main data loop
    # monitor for new blocks & add pool info per block
    logging.info("Monitoring for pool info updates...")
    while True:
        latest_mined_block = hyperdrive.web3.eth.get_block_number()
        # Only execute if we are on a new block
        if latest_mined_block <= block_number:
            if exit_on_catch_up:
                break
            time.sleep(_SLEEP_AMOUNT)
            continue
        # Backfilling for blocks that need updating
        for block_int in range(block_number + 1, latest_mined_block + 1):
            block_number: BlockNumber = BlockNumber(block_int)
            # Only print every 10 blocks
            if (block_number % 10) == 0:
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
            data_chain_to_db(hyperdrive, hyperdrive.get_block(block_number), db_session)

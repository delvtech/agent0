"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""
from __future__ import annotations

import logging
import time

from chainsync.analysis import data_to_analysis
from chainsync.db.base import initialize_session
from chainsync.db.hyperdrive import get_latest_block_number_from_pool_info_table, get_pool_config
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
    # TODO
    # analysis_latest_block_number = get_latest_block_number_from_analysis(db_session)
    analysis_latest_block_number = 0

    # Using max of latest block in database or specified start block
    block_number = max(start_block, analysis_latest_block_number)

    # Get pool config
    # TODO this likely should return a pd.Series, not dataframe
    pool_config_df = None
    # Wait for pool config to exist to ensure acquire_data is up and running
    # Retry 10 times
    for _ in range(10):
        pool_config_df = get_pool_config(db_session, coerce_float=False)
        pool_config_len = len(pool_config_df)
        if pool_config_len == 0:
            time.sleep(_SLEEP_AMOUNT)
    if pool_config_df is None:
        raise ValueError("Error in getting pool config from db")
    assert len(pool_config_df) == 1
    pool_config = pool_config_df.iloc[0]

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
        # Does batch analysis on range(analysis_start_block, latest_data_block_number) blocks
        analysis_start_block = block_number + 1
        analysis_end_block = latest_data_block_number + 1
        data_to_analysis(analysis_start_block, analysis_end_block, db_session, pool_config)
        block_number = latest_data_block_number
        time.sleep(_SLEEP_AMOUNT)

"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""
from __future__ import annotations

import logging
import os
import time

from chainsync import PostgresConfig
from chainsync.analysis import data_to_analysis
from chainsync.db.base import initialize_session
from chainsync.db.hyperdrive import (
    PoolInfo,
    get_latest_block_number_from_analysis_table,
    get_latest_block_number_from_table,
    get_pool_config,
)
from ethpy import EthConfig, build_eth_config
from ethpy.hyperdrive import HyperdriveAddresses, fetch_hyperdrive_address_from_uri, get_web3_and_hyperdrive_contracts
from sqlalchemy.orm import Session

_SLEEP_AMOUNT = 1


def data_analysis(
    start_block: int = 0,
    eth_config: EthConfig | None = None,
    db_session: Session | None = None,
    postgres_config: PostgresConfig | None = None,
    contract_addresses: HyperdriveAddresses | None = None,
    exit_on_catch_up: bool = False,
):
    """Execute the data acquisition pipeline.

    Arguments
    ---------
    start_block: int
        The starting block to filter the query on
    eth_config: EthConfig | None
        Configuration for URIs to the rpc and artifacts. If not set, will look for addresses
        in eth.env.
    db_session: Session | None
        Session object for connecting to db. If None, will initialize a new session based on
        postgres.env.
    postgres_config: PostgresConfig | None = None,
        PostgresConfig for connecting to db. If none, will set from postgres.env.
    contract_addresses: HyperdriveAddresses | None
        If set, will use these addresses instead of querying the artifact URI
        defined in eth_config.
    exit_on_catch_up: bool
        If True, will exit after catching up to current block
    """
    ## Initialization
    # eth config
    if eth_config is None:
        # Load parameters from env vars if they exist
        eth_config = build_eth_config()

    # postgres session
    if db_session is None:
        db_session = initialize_session(postgres_config=postgres_config, ensure_database_created=True)

    # Get addresses either from artifacts URI defined in eth_config or from contract_addresses
    if contract_addresses is None:
        contract_addresses = fetch_hyperdrive_address_from_uri(os.path.join(eth_config.artifacts_uri, "addresses.json"))

    # Get hyperdrive contract
    _, _, _, hyperdrive_contract = get_web3_and_hyperdrive_contracts(eth_config, contract_addresses)

    ## Get starting point for restarts
    analysis_latest_block_number = get_latest_block_number_from_analysis_table(db_session)

    # Using max of latest block in database or specified start block
    block_number = max(start_block, analysis_latest_block_number)

    # Get pool config
    # TODO this likely should return a pd.Series, not dataframe
    pool_config_df = None
    # Wait for pool config on queries to db to exist to ensure acquire_data is up and running
    for _ in range(10):
        pool_config_df = get_pool_config(db_session, coerce_float=False)
        pool_config_len = len(pool_config_df)
        if pool_config_len == 0:
            time.sleep(_SLEEP_AMOUNT)
        else:
            break
    if pool_config_df is None:
        raise ValueError("Error in getting pool config from db")
    assert len(pool_config_df) == 1
    pool_config = pool_config_df.iloc[0]

    # Main data loop
    # monitor for new blocks & add pool info per block
    logging.info("Monitoring database for updates...")
    while True:
        latest_data_block_number = get_latest_data_block(db_session)
        # Only execute if we are on a new block
        if latest_data_block_number <= block_number:
            if exit_on_catch_up:
                break
            time.sleep(_SLEEP_AMOUNT)
            continue
        # Does batch analysis on range(analysis_start_block, latest_data_block_number) blocks
        # TODO do regular batching to sample for wallet information
        analysis_start_block = block_number + 1
        analysis_end_block = latest_data_block_number + 1
        logging.info("Running batch %s to %s", analysis_start_block, analysis_end_block)
        data_to_analysis(analysis_start_block, analysis_end_block, pool_config, db_session, hyperdrive_contract)
        block_number = latest_data_block_number


def get_latest_data_block(db_session: Session) -> int:
    """Gets the latest block the data pipeline has written
    Since there are multiple tables that analysis reads from,
    we query the latest block from all read tables and select the minimum
    block from the list.

    Arguments
    ---------
    db_session: Session
        The initialized db session.

    Returns
    -------
    int
        The latest block number from the PoolInfo table.
    """
    # Note to avoid race condition, we add pool info as the last update for the block
    latest_pool_info = get_latest_block_number_from_table(PoolInfo, db_session)

    return latest_pool_info

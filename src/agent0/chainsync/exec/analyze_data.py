"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""

from __future__ import annotations

from eth_typing import ChecksumAddress
from sqlalchemy.orm import Session
from tqdm import tqdm

from agent0.chainsync import PostgresConfig
from agent0.chainsync.analysis import db_to_analysis
from agent0.chainsync.db.base import initialize_session
from agent0.chainsync.db.hyperdrive import DBPoolInfo, get_latest_block_number_from_table
from agent0.ethpy.hyperdrive import HyperdriveReadInterface


def analyze_data(
    start_block: int = 0,
    interfaces: list[HyperdriveReadInterface] | None = None,
    rpc_uri: str | None = None,
    hyperdrive_addresses: list[ChecksumAddress] | dict[str, ChecksumAddress] | None = None,
    db_session: Session | None = None,
    postgres_config: PostgresConfig | None = None,
    calc_pnl: bool = True,
    backfill: bool = False,
    backfill_sample_period: int | None = None,
    backfill_progress_bar: bool = False,
):
    """Execute the data acquisition pipeline.

    Arguments
    ---------
    start_block: int, optional
        The starting block to run analysis on for backfilling.
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
        Not used if a list of interfaces is provided.
    db_session: Session | None
        Session object for connecting to db. If None, will initialize a new session based on
        .env.
    postgres_config: PostgresConfig | None = None,
        PostgresConfig for connecting to db. If none, will set from .env.
    calc_pnl: bool
        Whether to calculate pnl. Defaults to True.
    backfill: bool, optional
        If true, will fill in missing pool info data for every `backfill_sample_period` blocks. Defaults to True.
    backfill_sample_period: int | None, optional
        The sample frequency when backfilling. If None, will backfill every block.
    backfill_progress_bar: bool, optional
        If true, will show a progress bar when backfilling. Defaults to False.
    """
    # TODO cleanup
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-positional-arguments

    # TODO implement logger instead of global logging to suppress based on module name.

    if backfill_sample_period is None:
        backfill_sample_period = 1

    ## Initialization
    if interfaces is None:
        if hyperdrive_addresses is None or rpc_uri is None:
            # TODO when we start deploying the registry, this case should look for existing
            # pools in the registry and use those.
            raise ValueError("hyperdrive_address and rpc_uri must be provided if not providing interface")

        if isinstance(hyperdrive_addresses, dict):
            # No need for the mapping here, `acquire_data` takes care of adding these mappings to the db
            hyperdrive_addresses = list(hyperdrive_addresses.values())

        interfaces = [
            HyperdriveReadInterface(hyperdrive_address, rpc_uri) for hyperdrive_address in hyperdrive_addresses
        ]

    # postgres session
    db_session_init = False
    if db_session is None:
        db_session_init = True
        db_session = initialize_session(postgres_config=postgres_config, ensure_database_created=True)

    latest_mined_block = interfaces[0].web3.eth.get_block_number()
    if backfill:
        for block_number in tqdm(
            range(start_block, latest_mined_block + backfill_sample_period, backfill_sample_period),
            disable=not backfill_progress_bar,
        ):
            # Ensure block doesn't exceed current block
            if block_number > latest_mined_block:
                continue
            # Each table handles keeping track of appending to tables
            db_to_analysis(db_session, interfaces, block_number, calc_pnl)
    else:
        # Each table handles keeping track of appending to tables
        db_to_analysis(db_session, interfaces, latest_mined_block, calc_pnl)

    # Clean up resources on clean exit
    # If this function made the db session, we close it here
    if db_session_init:
        db_session.close()


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
    latest_pool_info = get_latest_block_number_from_table(DBPoolInfo, db_session)

    return latest_pool_info

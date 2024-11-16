"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""

from __future__ import annotations

import logging

from eth_typing import BlockNumber, ChecksumAddress
from sqlalchemy.orm import Session
from tqdm import tqdm

from agent0.chainsync import PostgresConfig
from agent0.chainsync.db.base import initialize_session
from agent0.chainsync.db.hyperdrive import (
    add_hyperdrive_addr_to_name,
    checkpoint_events_to_db,
    init_data_chain_to_db,
    pool_info_to_db,
    trade_events_to_db,
)
from agent0.ethpy.hyperdrive import HyperdriveReadInterface


def acquire_data(
    start_block: int = 0,
    lookback_block_limit: int | None = 3000,
    interfaces: list[HyperdriveReadInterface] | None = None,
    rpc_uri: str | None = None,
    hyperdrive_addresses: list[ChecksumAddress] | dict[str, ChecksumAddress] | None = None,
    db_session: Session | None = None,
    postgres_config: PostgresConfig | None = None,
    backfill=True,
    backfill_sample_period: int | None = None,
    backfill_progress_bar: bool = False,
):
    """Execute the data acquisition pipeline.

    Arguments
    ---------
    start_block: int
        The starting block to filter the query on
    lookback_block_limit: int, optional
        The maximum number of blocks to look back when filling in missing data.
        If None, will ignore lookback block limit.
        Defaults to 3000.
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
    # pylint: disable=too-many-statements
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-positional-arguments
    # TODO implement logger instead of global logging to suppress based on module name.

    if backfill_sample_period is None:
        backfill_sample_period = 1

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

    latest_mined_block = interfaces[0].web3.eth.get_block_number()
    if lookback_block_limit is not None and (latest_mined_block - start_block) > lookback_block_limit:
        start_block = latest_mined_block - lookback_block_limit
        logging.warning(
            "Starting block is past lookback block limit, starting at block %s",
            start_block,
        )

    ## Collect initial data
    init_data_chain_to_db(interfaces, db_session)

    # Add all trade events to the table
    # TODO there may be time and memory concerns here if we're spinning up from
    # scratch and there's lots of trades/pools.
    trade_events_to_db(interfaces, wallet_addr=None, db_session=db_session)

    # Add all checkpoint events to the table
    checkpoint_events_to_db(interfaces, db_session=db_session)

    # Backfilling for blocks that need updating
    # Note `data_chain_to_db` takes care of handling duplicate rows
    if backfill:
        for block_int in tqdm(
            range(start_block, latest_mined_block + 1, backfill_sample_period),
            disable=not backfill_progress_bar,
        ):
            block_number: BlockNumber = BlockNumber(block_int)
            # Explicit check against loopback block limit
            if lookback_block_limit is not None and (latest_mined_block - block_number) > lookback_block_limit:
                # NOTE when this case happens, wallet information will no longer
                # be accurate, as we may have missed deltas on wallets
                # based on the blocks we skipped
                # TODO should directly query the chain for open positions
                # in this case
                logging.warning(
                    (
                        "Querying block_number %s out of %s, unable to keep up with chain block iteration. "
                        "Wallet information may be inaccurate."
                    ),
                    block_number,
                    latest_mined_block,
                )
                continue

            # Ensure block doesn't exceed current block
            if block_number > latest_mined_block:
                continue

            pool_info_to_db(interfaces, block_number, db_session)
    else:
        pool_info_to_db(interfaces, latest_mined_block, db_session)

    # Clean up resources on clean exit
    # If this function made the db session, we close it here
    if db_session_init:
        db_session.close()

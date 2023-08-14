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
from elfpy.utils import logs as log_utils
from eth_typing import URI, BlockNumber
from eth_utils import address
from ethpy import build_eth_config
from ethpy.base import initialize_web3_with_http_provider, load_all_abis
from ethpy.hyperdrive import fetch_hyperdrive_address_from_url
from ethpy.hyperdrive.interface import get_hyperdrive_contract
from web3 import Web3
from web3.contract.contract import Contract

_SLEEP_AMOUNT = 1


def main(
    artifacts_url: str,
    rpc_url: URI | str,
    abi_dir: str,
    start_block: int,
    lookback_block_limit: int,
):
    """Execute the data acquisition pipeline.

    Arguments
    ---------
    artifacts_url: str
        The url of the artifacts server from which we get addresses.
    rpc_url: URI | str
        The url to the ethereum node
    abi_dir : str
        The path to the abi directory
    start_block : int
        The starting block to filter the query on
    lookback_block_limit : int
        The maximum number of blocks to look back when filling in missing data
    """
    ## Initialization
    # postgres session
    session = initialize_session()
    # web3 provider
    web3: Web3 = initialize_web3_with_http_provider(rpc_url, request_kwargs={"timeout": 60})
    # send a request to the local server to fetch the deployed contract addresses and
    # all Hyperdrive contract addresses from the server response
    addresses = fetch_hyperdrive_address_from_url(os.path.join(artifacts_url, "addresses.json"))
    abis = load_all_abis(abi_dir)
    # Contracts
    hyperdrive_contract = get_hyperdrive_contract(web3, abis, addresses)
    base_contract: Contract = web3.eth.contract(
        address=address.to_checksum_address(addresses.base_token), abi=abis["ERC20Mintable"]
    )

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


if __name__ == "__main__":
    # setup constants
    START_BLOCK = 0
    # Look back limit for backfilling
    LOOKBACK_BLOCK_LIMIT = 100000

    # Load parameters from env vars if they exist
    config = build_eth_config()

    log_utils.setup_logging(".logging/acquire_data.log", log_stdout=True)
    main(
        config.ARTIFACTS_URL,
        config.RPC_URL,
        config.ABI_DIR,
        START_BLOCK,
        LOOKBACK_BLOCK_LIMIT,
    )

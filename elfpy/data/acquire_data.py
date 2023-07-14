"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing"""
from __future__ import annotations

import logging
import time

from dotenv import load_dotenv
from eth_typing import URI, BlockNumber
from eth_utils import address
from web3 import Web3
from web3.contract.contract import Contract

from elfpy import eth, hyperdrive_interface
from elfpy.data import postgres
from elfpy.utils import logs as log_utils

# pylint: disable=too-many-arguments

# TODO fix too many branches by splitting out various things into functions
# pylint: disable=too-many-branches

RETRY_COUNT = 10


def main(
    contracts_url: str,
    ethereum_node: URI | str,
    abi_dir: str,
    start_block: int,
    lookback_block_limit: int,
    sleep_amount: int,
):
    """Main entry point for accessing contract & writing pool info"""
    # TODO: refactor this function, its waaay to big as indicated by these pylints
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements

    # initialize the postgres session
    session = postgres.initialize_session()
    # get web3 provider
    web3: Web3 = eth.initialize_web3_with_http_provider(ethereum_node, request_kwargs={"timeout": 60})

    # send a request to the local server to fetch the deployed contract addresses and
    # all Hyperdrive contract addresses from the server response
    addresses = hyperdrive_interface.fetch_hyperdrive_address_from_url(contracts_url)
    abis = eth.abi.load_all_abis(abi_dir)

    hyperdrive_contract = hyperdrive_interface.get_hyperdrive_contract(web3, abis, addresses)
    base_contract: Contract = web3.eth.contract(
        address=address.to_checksum_address(addresses.base_token), abi=abis["ERC20Mintable"]
    )

    # get pool config from hyperdrive contract
    pool_config = hyperdrive_interface.get_hyperdrive_config(hyperdrive_contract)
    postgres.add_pool_config(pool_config, session)

    # Get last entry of pool info in db
    data_latest_block_number = postgres.get_latest_block_number(session)
    # Using max of latest block in database or specified start block
    start_block = max(start_block, data_latest_block_number)
    # Parameterized start block number
    block_number: BlockNumber = BlockNumber(start_block)
    # Make sure to not grab current block, as the current block is subject to change
    # Current block is still being built
    latest_mined_block = web3.eth.get_block_number() - 1
    lookback_block_limit = BlockNumber(lookback_block_limit)

    if (latest_mined_block - block_number) > lookback_block_limit:
        block_number = BlockNumber(latest_mined_block - lookback_block_limit)
        logging.warning("Starting block is past lookback block limit, starting at block %s", block_number)

    # This if statement executes only on initial run (based on data_latest_block_number check),
    # and if the chain has executed until start_block (based on latest_mined_block check)
    if data_latest_block_number < block_number < latest_mined_block:
        # Query and add block_pool_info
        block_pool_info = hyperdrive_interface.get_hyperdrive_pool_info(web3, hyperdrive_contract, block_number)
        postgres.add_pool_infos([block_pool_info], session)

        # Query and add block transactions
        block_transactions = eth.transactions.fetch_transactions_for_block(web3, hyperdrive_contract, block_number)
        postgres.add_transactions(block_transactions, session)

    # monitor for new blocks & add pool info per block
    logging.info("Monitoring for pool info updates...")
    while True:
        latest_mined_block = web3.eth.get_block_number() - 1
        # if we are on a new block
        if latest_mined_block > block_number:
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

                # get_block_pool_info crashes randomly with ValueError on some intermediate block,
                # keep trying until it returns
                block_pool_info = None
                for _ in range(RETRY_COUNT):
                    try:
                        block_pool_info = hyperdrive_interface.get_hyperdrive_pool_info(
                            web3, hyperdrive_contract, block_number
                        )
                        break
                    except ValueError:
                        logging.warning("Error in get_block_pool_info, retrying")
                        time.sleep(1)
                        continue
                if block_pool_info:
                    postgres.add_pool_infos([block_pool_info], session)

                block_transactions = None
                for _ in range(RETRY_COUNT):
                    try:
                        block_transactions = eth.transactions.fetch_transactions_for_block(
                            web3, hyperdrive_contract, block_number
                        )
                        break
                    except ValueError:
                        logging.warning("Error in fetch_transactions_for_block, retrying")
                        time.sleep(1)
                        continue
                if block_transactions:
                    postgres.add_transactions(block_transactions, session)

                if block_transactions and block_pool_info:
                    wallet_info_for_transactions = hyperdrive_interface.get_wallet_info(
                        hyperdrive_contract, base_contract, block_number, block_transactions, block_pool_info
                    )
                    postgres.add_wallet_infos(wallet_info_for_transactions, session)

        time.sleep(sleep_amount)


if __name__ == "__main__":
    # setup constants
    CONTRACTS_URL = "http://localhost:80/addresses.json"
    ETHEREUM_NODE = "http://localhost:8545"
    ABI_DIR = "./hyperdrive_solidity/.build/"
    START_BLOCK = 0
    # Look back limit for backfilling
    LOOKBACK_BLOCK_LIMIT = 1000
    SLEEP_AMOUNT = 1

    # Get postgres env variables if exists
    load_dotenv()

    log_utils.setup_logging(".logging/acquire_data.log", log_stdout=True)
    main(
        CONTRACTS_URL,
        ETHEREUM_NODE,
        ABI_DIR,
        START_BLOCK,
        LOOKBACK_BLOCK_LIMIT,
        SLEEP_AMOUNT,
    )

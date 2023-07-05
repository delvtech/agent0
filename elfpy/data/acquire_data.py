"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing"""
from __future__ import annotations

import logging
import time

from eth_typing import URI, BlockNumber
from web3 import Web3

from elfpy.data import contract_interface, postgres
from elfpy.data.db_schema import PoolInfo, Transaction
from elfpy.utils import outputs as output_utils

# pylint: disable=too-many-arguments


def main(
    contracts_url: str,
    ethereum_node: URI | str,
    state_abi_file_path: str,
    transactions_abi_file_path: str,
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
    web3: Web3 = contract_interface.initialize_web3_with_http_provider(ethereum_node, request_kwargs={"timeout": 60})
    # send a request to the local server to fetch the deployed contract addresses and
    # load the deployed Hyperdrive contract addresses from the server response
    state_hyperdrive_contract = contract_interface.get_hyperdrive_contract(state_abi_file_path, contracts_url, web3)
    transactions_hyperdrive_contract = contract_interface.get_hyperdrive_contract(
        transactions_abi_file_path, contracts_url, web3
    )

    # get pool config from hyperdrive contract
    pool_config = contract_interface.get_hyperdrive_config(state_hyperdrive_contract)
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

    # This if statement executes only on initial run, and if the chain has executed until start_block
    if block_number > data_latest_block_number and block_number < latest_mined_block:
        # Query and add block_pool_info
        block_pool_info = contract_interface.get_block_pool_info(web3, state_hyperdrive_contract, block_number)
        postgres.add_pool_infos([block_pool_info], session)

        # Query and add block transactions
        block_transactions = contract_interface.fetch_transactions_for_block(
            web3, transactions_hyperdrive_contract, block_number
        )
        postgres.add_transactions(block_transactions, session)

    # monitor for new blocks & add pool info per block
    logging.info("Monitoring for pool info updates...")
    while True:
        pool_info: list[PoolInfo] = []
        transactions: list[Transaction] = []
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
                while True:
                    try:
                        block_pool_info = contract_interface.get_block_pool_info(
                            web3, state_hyperdrive_contract, block_number
                        )
                        break
                    except ValueError:
                        logging.warning("Error in get_block_pool_info, retrying")
                        time.sleep(0.1)
                        continue
                if block_pool_info:
                    pool_info.append(block_pool_info)

                block_transactions = contract_interface.fetch_transactions_for_block(
                    web3, transactions_hyperdrive_contract, block_number
                )
                if block_transactions:
                    transactions.extend(block_transactions)

            # Add to postgres
            postgres.add_pool_infos(pool_info, session)
            postgres.add_transactions(transactions, session)

        time.sleep(sleep_amount)


if __name__ == "__main__":
    # setup constants
    CONTRACTS_URL = "http://localhost:80/addresses.json"
    ETHEREUM_NODE = "http://localhost:8545"
    STATE_ABI_FILE_PATH = "./hyperdrive_solidity/.build/IHyperdrive.json"
    TRANSACTIONS_ABI_FILE_PATH = "./hyperdrive_solidity/.build/IHyperdrive.json"
    START_BLOCK = 0
    # Look back limit for backfilling
    LOOKBACK_BLOCK_LIMIT = 1000
    SLEEP_AMOUNT = 1
    output_utils.setup_logging(".logging/acquire_data.log", log_file_and_stdout=True)
    main(
        CONTRACTS_URL,
        ETHEREUM_NODE,
        STATE_ABI_FILE_PATH,
        TRANSACTIONS_ABI_FILE_PATH,
        START_BLOCK,
        LOOKBACK_BLOCK_LIMIT,
        SLEEP_AMOUNT,
    )

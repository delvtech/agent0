"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing"""
from __future__ import annotations

import json
import logging
import os
import time

from eth_typing import URI
from web3 import Web3
from web3.types import BlockData

from elfpy.data import contract_interface
from elfpy.utils import outputs as output_utils


def main(
    contracts_url: str,
    ethereum_node: URI | str,
    state_abi_file_path: str,
    transactions_abi_file_path: str,
    save_dir: str,
    sleep_amount: int,
):
    """Main entry point for accessing contract & writing pool info"""
    # pylint: disable=too-many-locals
    # get web3 provider
    web3_container: Web3 = contract_interface.setup_web3(ethereum_node)
    # send a request to the local server to fetch the deployed contract addresses and
    # load the deployed Hyperdrive contract addresses from the server response
    state_hyperdrive_contract = contract_interface.get_hyperdrive_contract(
        state_abi_file_path, contracts_url, web3_container
    )
    transactions_hyperdrive_contract = contract_interface.get_hyperdrive_contract(
        transactions_abi_file_path, contracts_url, web3_container
    )
    # get pool config from hyperdrive contract
    config_file = os.path.join(save_dir, "hyperdrive_config.json")
    contract_interface.hyperdrive_config_to_json(config_file, state_hyperdrive_contract)
    # write the initial pool info
    block: BlockData = web3_container.eth.get_block("latest")
    block_number: int = block.number
    latest_block_number: int = block_number
    pool_info = {}
    pool_info[latest_block_number] = contract_interface.get_block_pool_info(
        web3_container, state_hyperdrive_contract, block_number
    )
    pool_info_file = os.path.join(save_dir, "hyperdrive_pool_info.json")
    transaction_info_file = os.path.join(save_dir, "hyperdrive_transactions.json")
    with open(pool_info_file, mode="w", encoding="UTF-8") as file:
        json.dump(pool_info, file, indent=2, cls=output_utils.ExtendedJSONEncoder)
    transaction_info = {}
    # monitor for new blocks & add pool info per block
    logging.info("Monitoring for pool info updates...")
    while True:
        latest_block_number: int = web3_container.eth.get_block_number()
        # if we are on a new block
        if latest_block_number != block_number:
            # Backfilling for blocks that need updating
            for block_number in range(block_number + 1, latest_block_number + 1):
                logging.info("Block %s", block_number)
                pool_info[block_number] = contract_interface.get_block_pool_info(
                    web3_container, state_hyperdrive_contract, block_number
                )
            with open(pool_info_file, mode="w", encoding="UTF-8") as file:
                json.dump(pool_info, file, indent=2, cls=output_utils.ExtendedJSONEncoder)
                transaction_info[block_number] = contract_interface.fetch_transactions_for_block_range(
                    web3_container, transactions_hyperdrive_contract, block_number
                )
            with open(transaction_info_file, mode="w", encoding="UTF-8") as file:
                json.dump(transaction_info_file, file, indent=2, cls=output_utils.ExtendedJSONEncoder)
        time.sleep(sleep_amount)


if __name__ == "__main__":
    # setup constants
    CONTRACTS_URL = "http://localhost:80/addresses.json"
    ETHEREUM_NODE = "http://localhost:8545"
    SAVE_DIR = ".logging"
    STATE_ABI_FILE_PATH = "./hyperdrive_solidity/.build/IHyperdrive.json"
    TRANSACTIONS_ABI_FILE_PATH = "./hyperdrive_solidity/.build/Hyperdrive.json"
    SLEEP_AMOUNT = 5
    output_utils.setup_logging(".logging/acquire_data.log", log_file_and_stdout=True)
    main(
        CONTRACTS_URL,
        ETHEREUM_NODE,
        STATE_ABI_FILE_PATH,
        TRANSACTIONS_ABI_FILE_PATH,
        SAVE_DIR,
        SLEEP_AMOUNT,
    )

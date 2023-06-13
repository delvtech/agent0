"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing"""
from __future__ import annotations

# std lib
import logging
import time

# third party
from eth_typing import BlockNumber, URI
from web3 import Web3
import pandas as pd

# custom
from extract_data_logs import calculate_spot_price
from elfpy.data import contract_interface
from elfpy.utils import outputs as output_utils

# pylint: disable=too-many-arguments, invalid-name


def prepare_data(trades, pool):
    """Prepare data for analysis."""
    # remove all empty values from dicts
    trades = {k: v for k, v in trades.items() if v}
    pool = {k: v for k, v in pool.items() if v}
    # turn to dataframes
    pool_df = pd.DataFrame(pool).T
    pool_df["shareReserves"] = pool_df["shareReserves"].astype(float)
    pool_df["bondReserves"] = pool_df["bondReserves"].astype(float)
    pool_df["lpTotalSupply"] = pool_df["lpTotalSupply"].astype(float)
    pool_df["sharePrice"] = pool_df["sharePrice"].astype(float)
    pool_df["timestamp"] = pool_df["timestamp"].iloc[0]+pool_df["blockNumber"]*12
    pool_df["spot_price"] = calculate_spot_price(
        share_reserves=pool_df["shareReserves"],
        bond_reserves=pool_df["bondReserves"],
        lp_total_supply=pool_df["lpTotalSupply"],
    )
    txns, logs, receipts = [], [], []
    for block in trades.values():
        for txn in block:
            txns.append(txn["transaction"])  # 1 per txn
            logs.extend(
                {k: v for k, v in log.items() if k != "args"} | log["args"]
                for log in txn["logs"]
                if log["event"] not in ["Approval", "Initialize"]
            )
            receipts.append(txn["receipt"])  # 1 per txn
    print(f"{len(txns)=} {len(logs)=} {len(receipts)=}")
    # merge pool_info fields
    fields_to_add = ["blockNumber", "timestamp", "sharePrice", "shareReserves", "bondReserves", "lpTotalSupply"]
    logs_df = pd.merge(pd.DataFrame(logs), pool_df.loc[:, fields_to_add])
    return logs_df, pool_df


def save_data(logs_df, pool_df, config_df, save_folder):
    """Save data to csv."""
    logs_df.to_csv(f"{save_folder}/logs.csv", index=False)
    pool_df.to_csv(f"{save_folder}/pool.csv", index=False)
    config_df.to_csv(f"{save_folder}/pool_config.csv", index=False)


def main(
    contracts_url: str,
    ethereum_node: URI | str,
    save_folder: str,
    state_abi_file_path: str,
    transactions_abi_file_path: str,
    start_block: int,
    first_deployed_block: int,
    sleep_amount: float,
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
    pool_config = contract_interface.get_smart_contract_read_call(state_hyperdrive_contract, "getPoolConfig")
    pool_config["curve_fee"], pool_config["flat_fee"], pool_config["governance_fee"] = pool_config.pop("fees")
    config_df = pd.DataFrame(pool_config, index=[0])
    # initialize records
    pool_info = {}
    transaction_info = {}

    # monitor for new blocks & add pool info per block
    logging.info("Monitoring for pool info updates...")
    block_number: BlockNumber = BlockNumber(start_block)
    while True:
        latest_block_number = web3_container.eth.get_block_number()
        # if we are on a new block
        if latest_block_number != block_number:
            # Backfilling for blocks that need updating
            for block_int in range(block_number + 1, latest_block_number + 1):
                block_number: BlockNumber = BlockNumber(block_int)
                logging.info("Block %s", block_number)
                pool_info[block_number] = (
                    contract_interface.get_block_pool_info(web3_container, state_hyperdrive_contract, block_number)
                    if block_number >= first_deployed_block
                    else {}
                )
                block_transactions = contract_interface.fetch_transactions_for_block(
                    web3_container, transactions_hyperdrive_contract, block_number
                )
                if block_transactions is not None:
                    transaction_info[block_number] = block_transactions
            logs_df, pool_df = prepare_data(transaction_info, pool_info)
            save_data(logs_df, pool_df, config_df, save_folder)
        time.sleep(sleep_amount)


if __name__ == "__main__":
    # setup constants
    output_utils.setup_logging(".logging/acquire_data.log", log_file_and_stdout=True)
    main(
        contracts_url="http://localhost:80/addresses.json",
        ethereum_node="http://localhost:8545",
        save_folder=".logging",
        state_abi_file_path="./hyperdrive_solidity/.build/IHyperdrive.json",
        transactions_abi_file_path="./hyperdrive_solidity/.build/Hyperdrive.json",
        start_block=0,
        first_deployed_block=6,  # first block after full deployment
        sleep_amount=1,
    )

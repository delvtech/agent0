"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""
from __future__ import annotations

import logging
import time

from dotenv import load_dotenv
from eth_typing import URI, BlockNumber
from eth_utils import address
from web3 import Web3
from web3.contract.contract import Contract

from elfpy import eth, hyperdrive_interface
from elfpy.data import db_schema, postgres
from elfpy.markets.hyperdrive import hyperdrive_assets
from elfpy.utils import logs as log_utils

# pylint: disable=too-many-arguments

# TODO fix too many branches by splitting out various things into functions
# pylint: disable=too-many-branches

RETRY_COUNT = 10


# TODO: Rename this to something more accurate to what is happening, e.g. decode_hyperdrive_transactions
def get_wallet_info(
    hyperdrive_contract: Contract,
    base_contract: Contract,
    block_number: BlockNumber,
    transactions: list[db_schema.Transaction],
    pool_info: db_schema.PoolInfo,
) -> list[db_schema.WalletInfo]:
    """Retrieve wallet information at a given block given a transaction.

    Transactions are needed here to get
    (1) the wallet address of a transaction, and
    (2) the token id of the transaction

    Arguments
    ---------
    hyperdrive_contract : Contract
        The deployed hyperdrive contract instance.
    base_contract : Contract
        The deployed base contract instance
    block_number : BlockNumber
        The block number to query
    transactions : list[db_schema.Transaction]
        The list of transactions to get events from
    pool_info : db_schema.PoolInfo
        The associated pool info, used to extract share price

    Returns
    -------
    list[db_schema.WalletInfo]
        The list of WalletInfo objects ready to be inserted into postgres
    """
    # pylint: disable=too-many-locals
    out_wallet_info = []
    for transaction in transactions:
        wallet_addr = transaction.event_operator
        token_id = transaction.event_id
        token_prefix = transaction.event_prefix
        token_maturity_time = transaction.event_maturity_time
        if wallet_addr is None:
            continue
        # Query and add base tokens to walletinfo
        num_base_token_scaled = None
        for _ in range(RETRY_COUNT):
            try:
                num_base_token_scaled = base_contract.functions.balanceOf(wallet_addr).call(
                    block_identifier=block_number
                )
                break
            except ValueError:
                logging.warning("Error in getting base token balance, retrying")
                time.sleep(1)
                continue
        num_base_token = eth.convert_scaled_value(num_base_token_scaled)
        if (num_base_token is not None) and (wallet_addr is not None):
            out_wallet_info.append(
                db_schema.WalletInfo(
                    blockNumber=block_number,
                    walletAddress=wallet_addr,
                    baseTokenType="BASE",
                    tokenType="BASE",
                    tokenValue=num_base_token,
                )
            )
        # Query and add hyperdrive tokens to walletinfo
        if (token_id is not None) and (token_prefix is not None):
            base_token_type = hyperdrive_assets.AssetIdPrefix(token_prefix).name
            if (token_maturity_time is not None) and (token_maturity_time > 0):
                token_type = base_token_type + "-" + str(token_maturity_time)
                maturity_time = token_maturity_time
            else:
                token_type = base_token_type
                maturity_time = None
            num_custom_token_scaled = None
            for _ in range(RETRY_COUNT):
                try:
                    num_custom_token_scaled = hyperdrive_contract.functions.balanceOf(int(token_id), wallet_addr).call(
                        block_identifier=block_number
                    )
                except ValueError:
                    logging.warning("Error in getting custom token balance, retrying")
                    time.sleep(1)
                    continue
            num_custom_token = eth.convert_scaled_value(num_custom_token_scaled)
            if num_custom_token is not None:
                # Check here if token is short
                # If so, add share price from pool info to data
                share_price = None
                if (base_token_type) == "SHORT":
                    share_price = pool_info.sharePrice
                out_wallet_info.append(
                    db_schema.WalletInfo(
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType=base_token_type,
                        tokenType=token_type,
                        tokenValue=num_custom_token,
                        maturityTime=maturity_time,
                        sharePrice=share_price,
                    )
                )
    return out_wallet_info


def main(
    contracts_url: str,
    ethereum_node: URI | str,
    abi_dir: str,
    start_block: int,
    lookback_block_limit: int,
    sleep_amount: int,
):
    """Execute the data acquisition pipeline.

    Arguments
    ---------
    contracts_url : str
        The url of the artifacts server from which we get addresses.
    ethereum_node : URI | str
        The url to the ethereum node
    abi_dir : str
        The path to the abi directory
    start_block : int
        The starting block to filter the query on
    lookback_block_limit : int
        The maximum number of blocks to loko back when filling in missing data
    sleep_amount : int
        The amount of seconds to sleep between queries
    """
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
    pool_config = db_schema.PoolConfig(**hyperdrive_interface.get_hyperdrive_config(hyperdrive_contract))
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
        pool_info_dict = hyperdrive_interface.get_hyperdrive_pool_info(web3, hyperdrive_contract, block_number)
        # Set defaults
        # TODO: abstract this out: pull the conversion between the interface to the db object into various functions
        for key in db_schema.PoolInfo.__annotations__:
            if key not in pool_info_dict:
                pool_info_dict[key] = None
        block_pool_info = db_schema.PoolInfo(**pool_info_dict)
        postgres.add_pool_infos([block_pool_info], session)

        # Query and add block_checkpoint_info
        checkpoint_info_dict = hyperdrive_interface.get_hyperdrive_checkpoint_info(
            web3, hyperdrive_contract, block_number
        )
        # Set defaults
        for key in db_schema.CheckpointInfo.__annotations__:
            if key not in checkpoint_info_dict:
                checkpoint_info_dict[key] = None
        block_checkpoint_info = db_schema.CheckpointInfo(**checkpoint_info_dict)
        postgres.add_checkpoint_infos([block_checkpoint_info], session)
        # Query and add block transactions
        block_transactions = db_schema.fetch_transactions_for_block(web3, hyperdrive_contract, block_number)
        postgres.add_transactions(block_transactions, session)
    # monitor for new blocks & add pool info per block
    logging.info("Monitoring for pool info updates...")
    # TODO: fewer nested blocks!
    # pylint: disable=too-many-nested-blocks
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
                # keep querying until it returns to avoid random crashes with ValueError on some intermediate block
                block_pool_info = None
                for _ in range(RETRY_COUNT):
                    try:
                        pool_info_dict = hyperdrive_interface.get_hyperdrive_pool_info(
                            web3, hyperdrive_contract, block_number
                        )
                        # Set defaults
                        for key in db_schema.PoolInfo.__annotations__:
                            if key not in pool_info_dict:
                                pool_info_dict[key] = None
                        block_pool_info = db_schema.PoolInfo(**pool_info_dict)
                        break
                    except ValueError:
                        logging.warning("Error in get_hyperdrive_pool_info, retrying")
                        time.sleep(1)
                        continue
                if block_pool_info:
                    postgres.add_pool_infos([block_pool_info], session)

                # keep querying until it returns to avoid random crashes with ValueError on some intermediate block
                block_transactions = None
                for _ in range(RETRY_COUNT):
                    try:
                        block_transactions = db_schema.fetch_transactions_for_block(
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
                    wallet_info_for_transactions = get_wallet_info(
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

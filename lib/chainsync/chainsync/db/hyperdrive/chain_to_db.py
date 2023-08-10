"""Functions for gathering data from the chain and adding it to the db"""
import logging
import time

from eth_typing import BlockNumber
from ethpy.base import fetch_contract_transactions_for_block
from ethpy.hyperdrive import get_hyperdrive_checkpoint_info, get_hyperdrive_config, get_hyperdrive_pool_info
from sqlalchemy.orm import Session
from web3 import Web3
from web3.contract.contract import Contract

from .convert_data import (
    convert_checkpoint_info,
    convert_hyperdrive_transactions_for_block,
    convert_pool_config,
    convert_pool_info,
    get_wallet_info,
)
from .interface import (
    add_checkpoint_infos,
    add_pool_config,
    add_pool_infos,
    add_transactions,
    add_wallet_deltas,
    add_wallet_infos,
)

_RETRY_COUNT = 10
_RETRY_SLEEP_SECONDS = 1


def init_data_chain_to_db(
    hyperdrive_contract: Contract,
    session: Session,
) -> None:
    """Function to query and insert pool config to dashboard"""
    # get pool config from hyperdrive contract
    pool_config_dict = None
    for _ in range(_RETRY_COUNT):
        try:
            pool_config_dict = get_hyperdrive_config(hyperdrive_contract)
            break
        except ValueError:
            logging.warning("Error in getting pool config, retrying")
            time.sleep(_RETRY_SLEEP_SECONDS)
            continue
    if pool_config_dict is None:
        raise ValueError("Error in getting pool config")
    add_pool_config(convert_pool_config(pool_config_dict), session)


def data_chain_to_db(
    web3: Web3,
    base_contract: Contract,
    hyperdrive_contract: Contract,
    block_number: BlockNumber,
    session: Session,
) -> None:
    """Function to query and insert data to dashboard"""
    # Query and add block_pool_info
    pool_info_dict = None
    for _ in range(_RETRY_COUNT):
        try:
            pool_info_dict = get_hyperdrive_pool_info(web3, hyperdrive_contract, block_number)
            break
        except ValueError:
            logging.warning("Error in get_hyperdrive_pool_info, retrying")
            time.sleep(_RETRY_SLEEP_SECONDS)
            continue
    if pool_info_dict is None:
        raise ValueError("Error in getting pool info")
    block_pool_info = convert_pool_info(pool_info_dict)
    add_pool_infos([block_pool_info], session)

    # Query and add block_checkpoint_info
    checkpoint_info_dict = None
    for _ in range(_RETRY_COUNT):
        try:
            checkpoint_info_dict = get_hyperdrive_checkpoint_info(web3, hyperdrive_contract, block_number)
            break
        except ValueError:
            logging.warning("Error in get_hyperdrive_checkpoint_info, retrying")
            time.sleep(_RETRY_SLEEP_SECONDS)
            continue
    if checkpoint_info_dict is None:
        raise ValueError("Error in getting checkpoint info")
    block_checkpoint_info = convert_checkpoint_info(checkpoint_info_dict)
    add_checkpoint_infos([block_checkpoint_info], session)

    # Query and add block_transactions and wallet deltas
    block_transactions = None
    wallet_deltas = None
    for _ in range(_RETRY_COUNT):
        try:
            transactions = fetch_contract_transactions_for_block(web3, hyperdrive_contract, block_number)
            (
                block_transactions,
                wallet_deltas,
            ) = convert_hyperdrive_transactions_for_block(web3, hyperdrive_contract, transactions)
            break
        except ValueError:
            logging.warning("Error in fetch_contract_transactions_for_block, retrying")
            time.sleep(_RETRY_SLEEP_SECONDS)
            continue
    # This case only happens if fetch_contract_transactions throws an exception
    # e.g., the web3 call fails. fetch_contract_transactions_for_block will return
    # empty lists (which doesn't execute the if statement below) if there are no hyperdrive
    # transactions for the block
    if block_transactions is None or wallet_deltas is None:
        raise ValueError("Error in getting transactions")
    add_transactions(block_transactions, session)
    add_wallet_deltas(wallet_deltas, session)

    # Query and add wallet info
    # TODO put the wallet info query as an optional block,
    # and check these wallet values with what we get from the deltas
    wallet_info_for_transactions = None
    for _ in range(_RETRY_COUNT):
        try:
            wallet_info_for_transactions = get_wallet_info(
                hyperdrive_contract, base_contract, block_number, block_transactions, block_pool_info
            )
            break
        except ValueError:
            logging.warning("Error in fetch_contract_transactions_for_block, retrying")
            time.sleep(_RETRY_SLEEP_SECONDS)
            continue
    if wallet_info_for_transactions is None:
        raise ValueError("Error in getting wallet_info")
    add_wallet_infos(wallet_info_for_transactions, session)

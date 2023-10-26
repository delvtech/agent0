"""Functions for gathering data from the chain and adding it to the db"""
from decimal import Decimal

from eth_typing import BlockNumber
from ethpy.base import fetch_contract_transactions_for_block, smart_contract_read
from ethpy.hyperdrive import (
    get_hyperdrive_checkpoint,
    get_hyperdrive_pool_config,
    get_hyperdrive_pool_info,
    process_hyperdrive_checkpoint,
    process_hyperdrive_pool_config,
    process_hyperdrive_pool_info,
)
from fixedpointmath import FixedPoint
from sqlalchemy.orm import Session
from web3 import Web3
from web3.contract.contract import Contract

from .convert_data import (
    convert_checkpoint_info,
    convert_hyperdrive_transactions_for_block,
    convert_pool_config,
    convert_pool_info,
)
from .interface import add_checkpoint_infos, add_pool_config, add_pool_infos, add_transactions, add_wallet_deltas


def init_data_chain_to_db(
    hyperdrive_contract: Contract,
    session: Session,
) -> None:
    """Function to query and insert pool config to dashboard

    Arguments
    ---------
    hyperdrive_contract: Contract
        The hyperdrive contract
    session: Session
        The database session
    """
    # TODO: Use the hyperdrive API here
    pool_config_dict = convert_pool_config(
        process_hyperdrive_pool_config(get_hyperdrive_pool_config(hyperdrive_contract), hyperdrive_contract.address)
    )
    add_pool_config(pool_config_dict, session)


# TODO this function should likely be moved to ethpy
def get_variable_rate_from_contract(yield_contract: Contract, block_number: BlockNumber) -> int:
    """Function to get the variable rate from the yield contract at a given block.

    Arguments
    ---------
    yield_contract: Contract
        The underlying yield contract
    block_number: BlockNumber
        The block number to query
    """
    return smart_contract_read(yield_contract, "getRate", block_number=block_number)["value"]


def data_chain_to_db(
    web3: Web3,
    hyperdrive_contract: Contract,
    yield_contract: Contract,
    block_number: BlockNumber,
    session: Session,
) -> None:
    """Function to query and insert data to dashboard.

    Arguments
    ---------
    web3: Web3
        The web3 object
    hyperdrive_contract: Contract
        The hyperdrive contract
    yield_contract: Contract
        The underlying yield contract
    block_number: BlockNumber
        The block number to query
    session: Session
        The database session
    """
    # Query and add block_checkpoint_info
    timestamp = web3.eth.get_block(block_number).get("timestamp", None)
    if timestamp is None:
        raise AssertionError("timestamp can not be None")
    checkpoint_info_dict = process_hyperdrive_checkpoint(
        get_hyperdrive_checkpoint(hyperdrive_contract, timestamp), web3, block_number
    )
    block_checkpoint_info = convert_checkpoint_info(checkpoint_info_dict)
    add_checkpoint_infos([block_checkpoint_info], session)

    # Query and add block_transactions and wallet deltas
    block_transactions = None
    wallet_deltas = None
    transactions = fetch_contract_transactions_for_block(web3, hyperdrive_contract, block_number)
    (
        block_transactions,
        wallet_deltas,
    ) = convert_hyperdrive_transactions_for_block(web3, hyperdrive_contract, transactions)
    add_transactions(block_transactions, session)
    add_wallet_deltas(wallet_deltas, session)

    # Query and add block_pool_info
    # Adding this last as pool info is what we use to determine if this block is in the db for analysis
    pool_info_dict = None
    pool_info_dict = process_hyperdrive_pool_info(
        pool_info=get_hyperdrive_pool_info(hyperdrive_contract, block_number),
        web3=web3,
        hyperdrive_contract=hyperdrive_contract,
        position_duration=int(get_hyperdrive_pool_config(hyperdrive_contract)["positionDuration"]),
        block_number=block_number,
    )
    block_pool_info = convert_pool_info(pool_info_dict)

    # Add variable rate to this dictionary
    # TODO ideally we'd add this information to a separate table, along with other non-poolinfo data
    # but data exposed from the hyperdrive interface.
    variable_rate = get_variable_rate_from_contract(yield_contract, block_number)
    # Converts scaled integer to fixed point, ultimately to Decimal for database
    block_pool_info.variableRate = Decimal(str(FixedPoint(scaled_value=variable_rate)))

    add_pool_infos([block_pool_info], session)

"""Functions for gathering data from the chain and adding it to the db"""
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal

from ethpy.base import fetch_contract_transactions_for_block
from ethpy.hyperdrive.interface import HyperdriveReadInterface
from fixedpointmath import FixedPoint
from sqlalchemy.orm import Session
from web3.types import BlockData

from .convert_data import (
    convert_checkpoint_info,
    convert_hyperdrive_transactions_for_block,
    convert_pool_config,
    convert_pool_info,
)
from .interface import add_checkpoint_infos, add_pool_config, add_pool_infos, add_transactions, add_wallet_deltas


def init_data_chain_to_db(
    interface: HyperdriveReadInterface,
    session: Session,
) -> None:
    """Function to query and insert pool config to dashboard.

    Arguments
    ---------
    interface: HyperdriveInterface
        The hyperdrive interface object.
    session: Session
        The database session
    """
    pool_config_dict = asdict(interface.current_pool_state.pool_config)
    pool_config_dict["contract_address"] = interface.addresses
    fees = pool_config_dict["fees"]
    pool_config_dict["curve_fee"] = fees["curve"]
    pool_config_dict["flat_fee"] = fees["flat"]
    pool_config_dict["governance_fee"] = fees["governance"]
    pool_config_dict["inv_time_stretch"] = FixedPoint(1) / pool_config_dict["time_stretch"]
    pool_config_db_obj = convert_pool_config(pool_config_dict)
    add_pool_config(pool_config_db_obj, session)


def data_chain_to_db(interface: HyperdriveReadInterface, block: BlockData, session: Session) -> None:
    """Function to query and insert data to dashboard.

    Arguments
    ---------
    interface: HyperdriveInterface
        Interface for the market on which this agent will be executing trades (MarketActions).
    block: BlockData
        The block to query.
    session: Session
        The database session.
    """
    pool_state = interface.get_hyperdrive_state(block)

    # TODO there's a race condition here, if this script gets interrupted between
    # intermediate results and pool info, there will be duplicate rows for e.g.,
    # add_checkpoint_infos, wallet_deltas, etc.

    ## Query and add block_checkpoint_info
    checkpoint_dict = asdict(pool_state.checkpoint)
    checkpoint_dict["block_number"] = int(pool_state.block_number)
    checkpoint_dict["timestamp"] = datetime.fromtimestamp(int(pool_state.block_time))
    block_checkpoint_info = convert_checkpoint_info(checkpoint_dict)
    add_checkpoint_infos([block_checkpoint_info], session)

    ## Query and add block_transactions and wallet deltas
    block_transactions = None
    wallet_deltas = None
    transactions = fetch_contract_transactions_for_block(
        interface.web3, interface.hyperdrive_contract, pool_state.block_number
    )
    block_transactions, wallet_deltas = convert_hyperdrive_transactions_for_block(
        interface.web3, interface.hyperdrive_contract, transactions
    )
    add_transactions(block_transactions, session)
    add_wallet_deltas(wallet_deltas, session)

    ## Query and add block_pool_info
    # Adding this last as pool info is what we use to determine if this block is in the db for analysis
    pool_info_dict = asdict(pool_state.pool_info)
    pool_info_dict["block_number"] = int(pool_state.block_number)
    pool_info_dict["timestamp"] = datetime.utcfromtimestamp(pool_state.block_time)
    pool_info_dict["total_supply_withdrawal_shares"] = pool_state.total_supply_withdrawal_shares
    block_pool_info = convert_pool_info(pool_info_dict)
    # Add variable rate to this dictionary
    # TODO ideally we'd add this information to a separate table, along with other non-poolinfo data
    # but data exposed from the hyperdrive interface.
    # Converts to Decimal for database
    block_pool_info.variable_rate = Decimal(str(pool_state.variable_rate))
    add_pool_infos([block_pool_info], session)

"""Functions for gathering data from the chain and adding it to the db"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from fixedpointmath import FixedPoint
from sqlalchemy.orm import Session

from agent0.chainsync.df_to_db import df_to_db
from agent0.ethpy.base import EARLIEST_BLOCK_LOOKUP
from agent0.ethpy.hyperdrive import HyperdriveReadInterface

from .convert_data import convert_checkpoint_events, convert_pool_config, convert_pool_info, convert_trade_events
from .event_getters import get_event_logs_for_db
from .interface import (
    add_pool_config,
    add_pool_infos,
    get_latest_block_number_from_checkpoint_info_table,
    get_latest_block_number_from_pool_info_table,
    get_latest_block_number_from_trade_event,
)
from .schema import DBCheckpointInfo, DBTradeEvent


def init_data_chain_to_db(
    interfaces: list[HyperdriveReadInterface],
    session: Session,
) -> None:
    """Function to query and insert pool config to dashboard.

    Arguments
    ---------
    interfaces: list[HyperdriveReadInterface]
        A collection of Hyperdrive interface objects, each connected to a pool.
    session: Session
        The database session
    """
    for interface in interfaces:
        pool_config_dict = asdict(interface.current_pool_state.pool_config)
        pool_config_dict["hyperdrive_address"] = interface.hyperdrive_address
        fees = pool_config_dict["fees"]
        pool_config_dict["curve_fee"] = fees["curve"]
        pool_config_dict["flat_fee"] = fees["flat"]
        pool_config_dict["governance_lp_fee"] = fees["governance_lp"]
        pool_config_dict["governance_zombie_fee"] = fees["governance_zombie"]
        pool_config_dict["inv_time_stretch"] = FixedPoint(1) / pool_config_dict["time_stretch"]
        pool_config_db_obj = convert_pool_config(pool_config_dict)
        add_pool_config(pool_config_db_obj, session)


def pool_info_to_db(interfaces: list[HyperdriveReadInterface], block_number: int, session: Session) -> None:
    """Function to query and insert data to dashboard.

    Arguments
    ---------
    interfaces: list[HyperdriveReadInterface]
        A collection of Hyperdrive interface objects, each connected to a pool.
    block_number: int
        The block number to query the chain on.
    session: Session
        The database session.
    """
    assert len(interfaces) > 0
    # Block data should be the same for all interfaces
    block = interfaces[0].get_block(block_number)

    # No race conditions here if this script gets interrupted between
    # intermediate results and pool info.
    # Trade events table handles not duplicating rows.
    # Checkpoint info table handles duplicate entries with unique constraint on
    # checkpoint id and vault share price (although if pipeline goes down, there might be
    # missing data TODO)
    # Pool info table drives which blocks gets queried.

    for interface in interfaces:
        # TODO abstract this function out
        # Only add the pool info row if it's already not in the db
        hyperdrive_address = interface.hyperdrive_address
        if block_number <= get_latest_block_number_from_pool_info_table(session, hyperdrive_address=hyperdrive_address):
            continue

        # If the pool wasn't deployed at the query block, skip
        deploy_block = interface.get_deploy_block_number()
        # deploy_block may be None in cases where we have a local chain and we lose the past events
        # In this case, we don't skip and hope the pool is already deployed
        if deploy_block is not None and block_number < deploy_block:
            continue

        pool_state = interface.get_hyperdrive_state(block_data=block)

        ## Query and add block_pool_info
        # Adding this last as pool info is what we use to determine if this block is in the db for analysis
        pool_info_dict = asdict(pool_state.pool_info)
        pool_info_dict["hyperdrive_address"] = hyperdrive_address
        pool_info_dict["block_number"] = int(pool_state.block_number)
        pool_info_dict["timestamp"] = datetime.fromtimestamp(pool_state.block_time, timezone.utc)

        # Adding additional fields
        pool_info_dict["epoch_timestamp"] = pool_state.block_time
        pool_info_dict["total_supply_withdrawal_shares"] = pool_state.total_supply_withdrawal_shares
        pool_info_dict["gov_fees_accrued"] = pool_state.gov_fees_accrued
        pool_info_dict["hyperdrive_base_balance"] = pool_state.hyperdrive_base_balance
        pool_info_dict["hyperdrive_eth_balance"] = pool_state.hyperdrive_eth_balance
        # Some pools may not have an underlying vault shares contract.
        # We ignore this field in the db in this case.
        try:
            pool_info_dict["variable_rate"] = interface.get_variable_rate()
        except ValueError:
            pool_info_dict["variable_rate"] = None
        pool_info_dict["vault_shares"] = pool_state.vault_shares
        pool_info_dict["spot_price"] = interface.calc_spot_price(pool_state)
        pool_info_dict["fixed_rate"] = interface.calc_spot_rate(pool_state)

        block_pool_info = convert_pool_info(pool_info_dict)
        add_pool_infos([block_pool_info], session)


def checkpoint_events_to_db(
    interfaces: list[HyperdriveReadInterface],
    db_session: Session,
) -> None:
    """Function to query checkpoint events from all pools and add them to the db.

    Arguments
    ---------
    interfaces: list[HyperdriveReadInterface]
        A collection of Hyperdrive interface objects, each connected to a pool.
    db_session: Session
        The database session.
    """
    assert len(interfaces) > 0

    # Gather all events we care about here
    all_events: list[dict[str, Any]] = []

    for interface in interfaces:
        # Get the earliest block to get events from.
        # We need the latest block number for a given hyperdrive pool,
        # as we call this function per pool.

        # TODO can narrow this down to the last block we checked
        # For now, keep this as the latest entry of this wallet.

        # + 1 since the queries are inclusive

        # NOTE we get all numeric arguments in events as string to prevent precision loss

        from_block = get_latest_block_number_from_checkpoint_info_table(db_session, interface.hyperdrive_address) + 1

        # Don't look back earlier than the defined earliest block for this chain
        chain_id = interface.web3.eth.chain_id
        if chain_id in EARLIEST_BLOCK_LOOKUP:
            from_block = max(from_block, EARLIEST_BLOCK_LOOKUP[chain_id])

        all_events.extend(
            get_event_logs_for_db(
                interface,
                interface.hyperdrive_contract.events.CreateCheckpoint,
                trade_base_unit_conversion=False,
                from_block=from_block,
            )
        )

    events_df = convert_checkpoint_events(all_events)

    # Add to db
    if len(events_df) > 0:
        df_to_db(events_df, DBCheckpointInfo, db_session)


def trade_events_to_db(
    interfaces: list[HyperdriveReadInterface],
    wallet_addr: str | None,
    db_session: Session,
) -> None:
    """Function to query trade events from all pools and add them to the db.

    Arguments
    ---------
    interfaces: list[HyperdriveReadInterface]
        A collection of Hyperdrive interface objects, each connected to a pool.
    wallet_addr: str | None
        The wallet address to query. If None, will not filter events by wallet addr.
    db_session: Session
        The database session.
    """
    assert len(interfaces) > 0

    # Gather all events we care about here
    all_events: list[dict[str, Any]] = []

    for interface in interfaces:
        # Get the earliest block to get events from
        # We need the latest block number for a given hyperdrive pool,
        # as we call this function per pool.

        # TODO can narrow this down to the last block we checked
        # For now, keep this as the latest entry of this wallet.
        # + 1 since the queries are inclusive

        # NOTE we get all numeric arguments in events as string to prevent precision loss
        from_block = (
            get_latest_block_number_from_trade_event(
                db_session, wallet_address=wallet_addr, hyperdrive_address=interface.hyperdrive_address
            )
            + 1
        )

        # Don't look back earlier than the defined earliest block for this chain
        chain_id = interface.web3.eth.chain_id
        if chain_id in EARLIEST_BLOCK_LOOKUP:
            from_block = max(from_block, EARLIEST_BLOCK_LOOKUP[chain_id])

        # Look for transfer single events in both directions if wallet_addr is set
        if wallet_addr is not None:
            all_events.extend(
                get_event_logs_for_db(
                    interface,
                    interface.hyperdrive_contract.events.TransferSingle,
                    trade_base_unit_conversion=False,
                    from_block=from_block,
                    argument_filters={"to": wallet_addr},
                )
            )
            all_events.extend(
                get_event_logs_for_db(
                    interface,
                    interface.hyperdrive_contract.events.TransferSingle,
                    trade_base_unit_conversion=False,
                    from_block=from_block,
                    argument_filters={"from": wallet_addr},
                )
            )
        # Otherwise, don't filter by wallet
        else:
            all_events.extend(
                get_event_logs_for_db(
                    interface,
                    interface.hyperdrive_contract.events.TransferSingle,
                    trade_base_unit_conversion=False,
                    from_block=from_block,
                )
            )

        # Hyperdrive events
        if wallet_addr is not None:
            trader_arg_filter = {"trader": wallet_addr}
            provider_arg_filter = {"provider": wallet_addr}
        else:
            trader_arg_filter = None
            provider_arg_filter = None

        all_events.extend(
            get_event_logs_for_db(
                interface,
                interface.hyperdrive_contract.events.Initialize,
                trade_base_unit_conversion=True,
                from_block=from_block,
                argument_filters=provider_arg_filter,
            )
        )
        all_events.extend(
            get_event_logs_for_db(
                interface,
                interface.hyperdrive_contract.events.OpenLong,
                trade_base_unit_conversion=True,
                from_block=from_block,
                argument_filters=trader_arg_filter,
            )
        )
        all_events.extend(
            get_event_logs_for_db(
                interface,
                interface.hyperdrive_contract.events.CloseLong,
                trade_base_unit_conversion=True,
                from_block=from_block,
                argument_filters=trader_arg_filter,
            )
        )
        all_events.extend(
            get_event_logs_for_db(
                interface,
                interface.hyperdrive_contract.events.OpenShort,
                trade_base_unit_conversion=True,
                from_block=from_block,
                argument_filters=trader_arg_filter,
            )
        )
        all_events.extend(
            get_event_logs_for_db(
                interface,
                interface.hyperdrive_contract.events.CloseShort,
                trade_base_unit_conversion=True,
                from_block=from_block,
                argument_filters=trader_arg_filter,
            )
        )
        all_events.extend(
            get_event_logs_for_db(
                interface,
                interface.hyperdrive_contract.events.AddLiquidity,
                trade_base_unit_conversion=True,
                from_block=from_block,
                argument_filters=provider_arg_filter,
                numeric_args_as_str=True,
            )
        )
        all_events.extend(
            get_event_logs_for_db(
                interface,
                interface.hyperdrive_contract.events.RemoveLiquidity,
                trade_base_unit_conversion=True,
                from_block=from_block,
                argument_filters=provider_arg_filter,
            )
        )
        all_events.extend(
            get_event_logs_for_db(
                interface,
                interface.hyperdrive_contract.events.RedeemWithdrawalShares,
                trade_base_unit_conversion=True,
                from_block=from_block,
                argument_filters=provider_arg_filter,
                numeric_args_as_str=True,
            )
        )

    events_df = convert_trade_events(all_events, wallet_addr)

    # Add to db
    if len(events_df) > 0:
        df_to_db(events_df, DBTradeEvent, db_session)

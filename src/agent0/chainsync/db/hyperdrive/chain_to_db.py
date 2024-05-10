"""Functions for gathering data from the chain and adding it to the db"""

from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
from fixedpointmath import FixedPoint
from sqlalchemy.orm import Session
from web3.types import BlockData, EventData

from agent0.chainsync.df_to_db import df_to_db
from agent0.ethpy.base import fetch_contract_transactions_for_block
from agent0.ethpy.hyperdrive import HyperdriveReadInterface

from .convert_data import (
    convert_checkpoint_info,
    convert_hyperdrive_transactions_for_block,
    convert_pool_config,
    convert_pool_info,
)
from .interface import (
    add_checkpoint_info,
    add_pool_config,
    add_pool_infos,
    add_transactions,
    add_wallet_deltas,
    get_latest_block_number_from_trade_event,
)
from .schema import TradeEvent


def init_data_chain_to_db(
    interface: HyperdriveReadInterface,
    session: Session,
) -> None:
    """Function to query and insert pool config to dashboard.

    Arguments
    ---------
    interface: HyperdriveReadInterface
        The hyperdrive interface object.
    session: Session
        The database session
    """
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


def data_chain_to_db(interface: HyperdriveReadInterface, block: BlockData, session: Session) -> None:
    """Function to query and insert data to dashboard.

    Arguments
    ---------
    interface: HyperdriveReadInterface
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
    checkpoint_dict["checkpoint_time"] = pool_state.checkpoint_time
    block_checkpoint_info = convert_checkpoint_info(checkpoint_dict)
    # When the contract call fails due to missing checkpoint, solidity returns 0
    # Hence, we detect that here and don't add the checkpoint info if that happens
    if block_checkpoint_info.vault_share_price != 0:
        add_checkpoint_info(block_checkpoint_info, session)

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
    pool_info_dict["timestamp"] = datetime.fromtimestamp(pool_state.block_time, timezone.utc)

    # Adding additional fields
    pool_info_dict["epoch_timestamp"] = pool_state.block_time
    pool_info_dict["total_supply_withdrawal_shares"] = pool_state.total_supply_withdrawal_shares
    pool_info_dict["gov_fees_accrued"] = pool_state.gov_fees_accrued
    pool_info_dict["hyperdrive_base_balance"] = pool_state.hyperdrive_base_balance
    pool_info_dict["hyperdrive_eth_balance"] = pool_state.hyperdrive_eth_balance
    pool_info_dict["variable_rate"] = pool_state.variable_rate
    pool_info_dict["vault_shares"] = pool_state.vault_shares

    block_pool_info = convert_pool_info(pool_info_dict)
    add_pool_infos([block_pool_info], session)


def _event_data_to_dict(in_val: EventData) -> dict[str, Any]:
    out = dict(in_val)
    # The args field is also an attribute dict, change to dict
    out["args"] = dict(in_val["args"])
    # There are issues with storing very large integers
    # in the database, so we convert the assetId to a string
    if "assetId" in out["args"]:
        out["args"]["assetId"] = str(in_val["args"]["assetId"])
    if "id" in out["args"]:
        out["args"]["id"] = str(in_val["args"]["id"])

    # Convert transaction hash to string
    out["transactionHash"] = in_val["transactionHash"].to_0x_hex()
    # Get token id field from args.
    # This field is `assetId` for open/close long/short
    return out


# TODO cleanup
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
def trade_events_to_db(
    interfaces: list[HyperdriveReadInterface],
    wallet_addr: str,
    db_session: Session,
) -> None:
    """Function to query trade events from all pools and add them to the db.

    Arguments
    ---------
    interfaces: list[HyperdriveReadInterface]
        The hyperdrive interface objects connected to a pool.
    wallet_addr: str
        The wallet address to query.
    db_session: Session
        The database session.

    """
    assert len(interfaces) > 0

    # Get the earliest block to get events from
    # TODO can narrow this down to the last block we checked
    # For now, keep this as the latest entry of this wallet.
    # + 1 since the queries are inclusive
    from_block = get_latest_block_number_from_trade_event(db_session, wallet_addr) + 1

    # Gather all events we care about here
    # Transfers to and from wallet address
    # db_event_objs: dict[str, HyperdriveEvent] = {}

    all_events = []

    for interface in interfaces:
        events = interface.hyperdrive_contract.events.TransferSingle.get_logs(
            fromBlock=from_block,
            argument_filters={"to": wallet_addr},
        )
        # Change events from attribute dict to dictionary
        all_events.extend([_event_data_to_dict(event) for event in events])

        events = interface.hyperdrive_contract.events.TransferSingle.get_logs(
            fromBlock=from_block,
            argument_filters={"from": wallet_addr},
        )
        all_events.extend([_event_data_to_dict(event) for event in events])

        # Hyperdrive events
        events = interface.hyperdrive_contract.events.OpenLong.get_logs(
            fromBlock=from_block,
            argument_filters={"trader": wallet_addr},
        )
        all_events.extend([_event_data_to_dict(event) for event in events])

        events = interface.hyperdrive_contract.events.CloseLong.get_logs(
            fromBlock=from_block,
            argument_filters={"trader": wallet_addr},
        )
        all_events.extend([_event_data_to_dict(event) for event in events])

        events = interface.hyperdrive_contract.events.OpenShort.get_logs(
            fromBlock=from_block,
            argument_filters={"trader": wallet_addr},
        )
        all_events.extend([_event_data_to_dict(event) for event in events])

        events = interface.hyperdrive_contract.events.CloseShort.get_logs(
            fromBlock=from_block,
            argument_filters={"trader": wallet_addr},
        )
        all_events.extend([_event_data_to_dict(event) for event in events])

        events = interface.hyperdrive_contract.events.AddLiquidity.get_logs(
            fromBlock=from_block,
            argument_filters={"provider": wallet_addr},
        )
        all_events.extend([_event_data_to_dict(event) for event in events])

        events = interface.hyperdrive_contract.events.RemoveLiquidity.get_logs(
            fromBlock=from_block,
            argument_filters={"provider": wallet_addr},
        )
        all_events.extend([_event_data_to_dict(event) for event in events])

        events = interface.hyperdrive_contract.events.RedeemWithdrawalShares.get_logs(
            fromBlock=from_block,
            argument_filters={"provider": wallet_addr},
        )
        all_events.extend([_event_data_to_dict(event) for event in events])

    # Convert to dataframe
    events_df = pd.DataFrame(all_events)
    # If no events, we just return
    if len(events_df) == 0:
        return

    # Each transaction made through hyperdrive has two rows for each transaction,
    # one TransferSingle and one for the trade.
    # Any transactions without a corresponding trade is a wallet to wallet transfer.
    # We detect this case and throw an error if we find this.
    # TODO handle transfer events

    # Look for any transfer events not associated with a trade
    unique_events_per_transaction = events_df.groupby("transactionHash")["event"].agg(["unique", "nunique"])
    if (unique_events_per_transaction["nunique"] < 2).any():
        raise ValueError(
            "Found less than 2 unique events for transaction, likely due to "
            "a transfer event not associated with a trade. This is not supported yet. "
            f"{unique_events_per_transaction[unique_events_per_transaction['nunique'] < 2]['unique']}"
        )
    if (unique_events_per_transaction["nunique"] > 2).any():
        raise ValueError(
            "Found more than 2 unique events for transaction."
            f"{unique_events_per_transaction[unique_events_per_transaction['nunique'] > 2]['unique']}"
        )

    # Drop all transfer single events
    events_df = events_df[events_df["event"] != "TransferSingle"].reset_index(drop=True)

    # Sanity check, one hyperdrive event per transaction hash
    assert events_df.groupby("transactionHash")["event"].nunique().all() == 1

    # Expand the args dict without losing the args dict field
    # json_normalize works on series, but typing doesn't support it.
    args_columns = pd.json_normalize(events_df["args"])  # type: ignore
    events_df = pd.concat([events_df, args_columns], axis=1)

    # Convert fields to db schema
    # Longs
    events_idx = events_df["event"].isin(["OpenLong", "CloseLong"])
    if events_idx.any():
        events_df.loc[events_idx, "token_type"] = "LONG"
        events_df.loc[events_idx, "token_id"] = "LONG-" + events_df.loc[events_idx, "maturityTime"].astype(int).astype(
            str
        )

    events_idx = events_df["event"] == "OpenLong"
    if events_idx.any():
        # Pandas apply doesn't play nice with types
        events_df.loc[events_idx, "token_delta"] = events_df.loc[events_idx, "bondAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        events_df.loc[events_idx, "base_delta"] = -events_df.loc[events_idx, "baseAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )

    events_idx = events_df["event"] == "CloseLong"
    if events_idx.any():
        # Pandas apply doesn't play nice with types
        events_df.loc[events_idx, "token_delta"] = -events_df.loc[events_idx, "bondAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        events_df.loc[events_idx, "base_delta"] = events_df.loc[events_idx, "baseAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )

    # Shorts
    events_idx = events_df["event"].isin(["OpenShort", "CloseShort"])
    if events_idx.any():
        events_df.loc[events_idx, "token_type"] = "SHORT"
        events_df.loc[events_idx, "token_id"] = "SHORT-" + events_df.loc[events_idx, "maturityTime"].astype(int).astype(
            str
        )

    events_idx = events_df["event"] == "OpenShort"
    if events_idx.any():
        # Pandas apply doesn't play nice with types
        events_df.loc[events_idx, "token_delta"] = events_df.loc[events_idx, "bondAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        events_df.loc[events_idx, "base_delta"] = -events_df.loc[events_idx, "baseAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )

    events_idx = events_df["event"] == "CloseShort"
    if events_idx.any():
        # Pandas apply doesn't play nice with types
        events_df.loc[events_idx, "token_delta"] = -events_df.loc[events_idx, "bondAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        events_df.loc[events_idx, "base_delta"] = events_df.loc[events_idx, "baseAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )

    # LP
    events_idx = events_df["event"].isin(["AddLiquidity", "RemoveLiquidity"])
    if events_idx.any():
        events_df.loc[events_idx, "token_type"] = "LP"
        events_df.loc[events_idx, "token_id"] = "LP"
        # The wallet here is the "provider" column, we remap it to "trader"
        events_df.loc[events_idx, "trader"] = events_df.loc[events_idx, "provider"]
        # We explicitly add a maturity time here to ensure this column exists
        # if there were no longs in this event set.
        events_df.loc[events_idx, "maturityTime"] = np.nan

    events_idx = events_df["event"] == "AddLiquidity"
    if events_idx.any():
        # Pandas apply doesn't play nice with types
        events_df.loc[events_idx, "token_delta"] = events_df.loc[events_idx, "lpAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        events_df.loc[events_idx, "base_delta"] = -events_df.loc[events_idx, "baseAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )

    events_idx = events_df["event"] == "RemoveLiquidity"
    if events_idx.any():
        # Pandas apply doesn't play nice with types
        events_df.loc[events_idx, "token_delta"] = -events_df.loc[events_idx, "lpAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        events_df.loc[events_idx, "base_delta"] = events_df.loc[events_idx, "baseAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        # We need to also add any withdrawal shares as additional rows
        withdrawal_shares_idx = events_idx & (events_df["withdrawalShareAmount"] > 0)
        if withdrawal_shares_idx.any():
            withdrawal_rows = events_df[withdrawal_shares_idx].copy()
            withdrawal_rows["token_type"] = "WITHDRAWAL_SHARE"
            withdrawal_rows["token_id"] = "WITHDRAWAL_SHARE"
            withdrawal_rows["token_delta"] = withdrawal_rows["withdrawalShareAmount"].apply(
                lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
            )
            withdrawal_rows["base_delta"] = Decimal(0)
            events_df = pd.concat([events_df, withdrawal_rows], axis=0)

    events_idx = events_df["event"] == "RedeemWithdrawalShares"
    if events_idx.any():
        events_df.loc[events_idx, "token_type"] = "WITHDRAWAL_SHARE"
        events_df.loc[events_idx, "token_id"] = "WITHDRAWAL_SHARE"
        # The wallet here is the "provider" column, we remap it to "trader"
        events_df.loc[events_idx, "trader"] = events_df.loc[events_idx, "provider"]
        # We explicitly add a maturity time here to ensure this column exists
        # if there were no longs in this event set.
        events_df.loc[events_idx, "maturityTime"] = np.nan
        # Pandas apply doesn't play nice with types
        events_df.loc[events_idx, "token_delta"] = -events_df.loc[events_idx, "withdrawalShareAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        events_df.loc[events_idx, "base_delta"] = events_df.loc[events_idx, "baseAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )

    # We select the subset of columns we need and rename to match db schema
    rename_dict = {
        "address": "hyperdrive_address",
        "transactionHash": "transaction_hash",
        "blockNumber": "block_number",
        "trader": "wallet_address",
        "event": "event_type",
        "token_type": "token_type",
        "maturityTime": "maturity_time",
        "token_id": "token_id",
        "token_delta": "token_delta",
        "base_delta": "base_delta",
        "args": "event_json",
    }

    events_df = events_df[list(rename_dict.keys())].rename(columns=rename_dict)
    # Add to db
    df_to_db(events_df, TradeEvent, db_session)

"""Utilities to convert hyperdrive related things to database schema objects."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
from fixedpointmath import FixedPoint
from web3.types import EventData

from agent0.ethpy.hyperdrive import AssetIdPrefix, decode_asset_id
from agent0.hypertypes.utilities.conversions import camel_to_snake

from .schema import PoolConfig, PoolInfo


def _event_data_to_dict(in_val: EventData) -> dict[str, Any]:
    out = dict(in_val)
    # The args field is also an attribute dict, change to dict
    out["args"] = dict(in_val["args"])

    # Convert transaction hash to string
    out["transactionHash"] = in_val["transactionHash"].hex()
    # Get token id field from args.
    # This field is `assetId` for open/close long/short
    return out


def convert_checkpoint_events(events: list[EventData]) -> pd.DataFrame:
    """Convert hyperdrive trade events to database schema objects.

    Arguments
    ---------
    events: list[EventData]
        A list of web3 EventData objects from `get_logs` to insert into postgres.

    Returns
    -------
    DataFrame
        A DataFrame that matches the db schema of checkpoint events.
    """
    # Convert list of event data to list of dictionaries to allow conversion to dataframe
    events_df = pd.DataFrame([_event_data_to_dict(event) for event in events])

    # If no events, we just return
    if len(events_df) == 0:
        return events_df

    # Expand the args dict without losing the args dict field
    # json_normalize works on series, but typing doesn't support it.
    args_columns = pd.json_normalize(events_df["args"])  # type: ignore
    events_df = pd.concat([events_df, args_columns], axis=1)
    # Select subset of columns we need and rename them
    rename_dict = {
        "address": "hyperdrive_address",
        "blockNumber": "block_number",
        "checkpointTime": "checkpoint_time",
        "checkpointVaultSharePrice": "checkpoint_vault_share_price",
        "vaultSharePrice": "vault_share_price",
        "maturedShorts": "matured_shorts",
        "maturedLongs": "matured_longs",
        "lpSharePrice": "lp_share_price",
    }

    events_df = events_df[list(rename_dict.keys())].rename(columns=rename_dict)
    # Convert values to fixed point decimals
    fixed_point_columns = [
        "checkpoint_vault_share_price",
        "vault_share_price",
        "matured_shorts",
        "matured_longs",
        "lp_share_price",
    ]
    for column in fixed_point_columns:
        events_df[column] = events_df[column].apply(lambda x: Decimal(x) / Decimal(1e18))  # type: ignore
    return events_df


# TODO cleanup
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
# pylint: disable=too-many-locals
def convert_trade_events(events: list[EventData], wallet_addr: str | None) -> pd.DataFrame:
    """Convert hyperdrive trade events to database schema objects.

    Arguments
    ---------
    events: list[EventData]
        A list of web3 EventData objects from `get_logs` to insert into postgres.
    wallet_addr: str | None
        The wallet address that events are associated with for transfer events.
        If None, will assume we want all events to the database.

    Returns
    -------
    DataFrame
        A DataFrame that matches the db schema of trade events.
    """

    # Convert attribute dictionary event data to dictionary to allow conversion to dataframe
    events_df = pd.DataFrame([_event_data_to_dict(event) for event in events])

    # If no events, we just return
    if len(events_df) == 0:
        return events_df

    # Each transaction made through hyperdrive has two rows,
    # one TransferSingle and one for the trade.
    # Any transactions without a corresponding trade is a wallet to wallet transfer.

    # Look for any transfer events not associated with a trade
    unique_events_per_transaction = events_df.groupby("transactionHash")["event"].agg(["unique", "nunique"])
    # Sanity check
    if (unique_events_per_transaction["nunique"] > 2).any():
        raise ValueError(
            "Found more than 2 unique events for transaction."
            f"{unique_events_per_transaction[unique_events_per_transaction['nunique'] > 2]['unique']}"
        )

    # Find any transfer events that are not associated with a trade.
    # This happens when e.g., a wallet to wallet transfer happens, or
    # if this wallet is the initializer of the pool.
    # Sometimes, there doesn't exist a transfer event with a trade
    # So we also make sure the set of unique events per transaction hash contains transfer single.
    # TODO we have a test for initializer of the pool, but we need to implement
    # wallet to wallet transfers of tokens in the interactive interface for a full test
    transfer_events_trx_hash = unique_events_per_transaction[
        (unique_events_per_transaction["nunique"] < 2)
        & (unique_events_per_transaction["unique"].str.contains("TransferSingle", regex=False))
    ].reset_index()["transactionHash"]
    transfer_events_df = events_df[events_df["transactionHash"].isin(transfer_events_trx_hash)].copy()
    if len(transfer_events_df) > 0:
        # Expand the args dict without losing the args dict field
        # json_normalize works on series, but typing doesn't support it.
        args_columns = pd.json_normalize(transfer_events_df["args"])  # type: ignore
        transfer_events_df = pd.concat([transfer_events_df, args_columns], axis=1)
        # We apply the decode function to each element, then expand the resulting
        # tuple to multiple columns
        if "id" not in transfer_events_df:
            pass
        transfer_events_df["token_type"], transfer_events_df["maturityTime"] = zip(
            *transfer_events_df["id"].astype(int).apply(decode_asset_id)
        )
        # Convert token_type enum to name
        transfer_events_df["token_type"] = transfer_events_df["token_type"].apply(lambda x: AssetIdPrefix(x).name)
        # Convert maturity times of 0 to nan to match other events
        transfer_events_df.loc[transfer_events_df["maturityTime"] == 0, "maturityTime"] = np.nan
        # Set token id, default is to set it to the token type
        transfer_events_df["token_id"] = transfer_events_df["token_type"]
        # Append the maturity time for longs and shorts
        long_or_short_idx = transfer_events_df["token_type"].isin(["LONG", "SHORT"])
        transfer_events_df.loc[long_or_short_idx, "token_id"] = (
            transfer_events_df.loc[long_or_short_idx, "token_type"]
            + "-"
            + transfer_events_df.loc[long_or_short_idx, "maturityTime"].astype(str)
        )

        # If the wallet address is set, set the event wrt the trader
        if wallet_addr is not None:
            # Set the trader of this transfer
            transfer_events_df["trader"] = wallet_addr

            # See if it's a receive or send of tokens
            send_idx = transfer_events_df["from"] == wallet_addr
            receive_idx = transfer_events_df["to"] == wallet_addr
            # Set the token delta based on send or receive
            transfer_events_df.loc[send_idx, "token_delta"] = -transfer_events_df.loc[send_idx, "value"].apply(
                lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
            )
            transfer_events_df.loc[receive_idx, "token_delta"] = transfer_events_df.loc[receive_idx, "value"].apply(
                lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
            )
        # If the wallet address is not set, ensure it's not a mint or burn, then add two rows
        # wrt both traders
        else:
            # TODO need to implement transfers to test this case
            # We raise not implemented for now
            raise NotImplementedError("Not implemented for wallet_addr=None")

        # See if it's a receive or send of tokens
        send_idx = transfer_events_df["from"] == wallet_addr
        receive_idx = transfer_events_df["to"] == wallet_addr
        # Set the token delta based on send or receive
        transfer_events_df.loc[send_idx, "token_delta"] = -transfer_events_df.loc[send_idx, "value"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        transfer_events_df.loc[receive_idx, "token_delta"] = transfer_events_df.loc[receive_idx, "value"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        # Base and vault share delta is always 0
        transfer_events_df["base_delta"] = Decimal(0)
        transfer_events_df["vault_share_delta"] = Decimal(0)
        # asBase and vaultSharePrice doesn't make sense here, we keep as nan
        # We use camel case to match the other event fields before rename
        transfer_events_df["asBase"] = np.nan
        transfer_events_df["vaultSharePrice"] = np.nan

    # Drop all transfer single events
    events_df = events_df[events_df["event"] != "TransferSingle"].reset_index(drop=True)

    # Sanity check, one hyperdrive event per transaction hash
    if events_df.groupby("transactionHash")["event"].nunique().all() != 1:
        raise ValueError("Found more than one event per transaction hash.")

    # Expand the args dict without losing the args dict field
    # json_normalize works on series, but typing doesn't support it.
    args_columns = pd.json_normalize(events_df["args"])  # type: ignore
    events_df = pd.concat([events_df, args_columns], axis=1)

    # Convert fields to db schema
    # All events should have vaultSharePrice. We convert to non-scaled value.
    events_df["vaultSharePrice"] = (
        events_df["vaultSharePrice"].astype(int).apply(lambda x: Decimal(x) / Decimal(1e18))  # type: ignore
    )

    # LP
    events_idx = events_df["event"].isin(["AddLiquidity", "RemoveLiquidity", "Initialize"])
    if events_idx.any():
        events_df.loc[events_idx, "token_type"] = "LP"
        events_df.loc[events_idx, "token_id"] = "LP"
        # The wallet here is the "provider" column, we remap it to "trader"
        events_df.loc[events_idx, "trader"] = events_df.loc[events_idx, "provider"]
        # We explicitly add a maturity time here to ensure this column exists
        # if there were no longs in this event set.
        events_df.loc[events_idx, "maturityTime"] = np.nan

    # Add liquidity and initialize are identical
    events_idx = events_df["event"].isin(["AddLiquidity", "Initialize"])
    if events_idx.any():
        # Pandas apply doesn't play nice with types
        events_df.loc[events_idx, "token_delta"] = events_df.loc[events_idx, "lpAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        as_base_idx = events_df["asBase"] & events_idx
        as_shares_idx = ~events_df["asBase"] & events_idx
        events_df.loc[as_base_idx, "base_delta"] = -events_df.loc[as_base_idx, "amount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        events_df.loc[as_shares_idx, "vault_share_delta"] = -events_df.loc[as_shares_idx, "amount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )

    events_idx = events_df["event"] == "RemoveLiquidity"
    if events_idx.any():
        # Pandas apply doesn't play nice with types
        events_df.loc[events_idx, "token_delta"] = -events_df.loc[events_idx, "lpAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        as_base_idx = events_df["asBase"] & events_idx
        as_shares_idx = ~events_df["asBase"] & events_idx
        events_df.loc[as_base_idx, "base_delta"] = events_df.loc[as_base_idx, "amount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        events_df.loc[as_shares_idx, "vault_share_delta"] = events_df.loc[as_shares_idx, "amount"].apply(
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
            withdrawal_rows["vault_share_delta"] = Decimal(0)
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
        as_base_idx = events_df["asBase"] & events_idx
        as_shares_idx = ~events_df["asBase"] & events_idx
        events_df.loc[as_base_idx, "base_delta"] = events_df.loc[as_base_idx, "amount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        events_df.loc[as_shares_idx, "vault_share_delta"] = events_df.loc[as_shares_idx, "amount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )

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
        as_base_idx = events_df["asBase"] & events_idx
        as_shares_idx = ~events_df["asBase"] & events_idx
        events_df.loc[as_base_idx, "base_delta"] = -events_df.loc[as_base_idx, "amount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        events_df.loc[as_shares_idx, "vault_share_delta"] = -events_df.loc[as_shares_idx, "amount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )

    events_idx = events_df["event"] == "CloseLong"
    if events_idx.any():
        # Pandas apply doesn't play nice with types
        events_df.loc[events_idx, "token_delta"] = -events_df.loc[events_idx, "bondAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        as_base_idx = events_df["asBase"] & events_idx
        as_shares_idx = ~events_df["asBase"] & events_idx
        events_df.loc[as_base_idx, "base_delta"] = events_df.loc[as_base_idx, "amount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        events_df.loc[as_shares_idx, "vault_share_delta"] = events_df.loc[as_shares_idx, "amount"].apply(
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
        as_base_idx = events_df["asBase"] & events_idx
        as_shares_idx = ~events_df["asBase"] & events_idx
        events_df.loc[as_base_idx, "base_delta"] = -events_df.loc[as_base_idx, "amount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        events_df.loc[as_shares_idx, "vault_share_delta"] = -events_df.loc[as_shares_idx, "amount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )

    events_idx = events_df["event"] == "CloseShort"
    if events_idx.any():
        # Pandas apply doesn't play nice with types
        events_df.loc[events_idx, "token_delta"] = -events_df.loc[events_idx, "bondAmount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        as_base_idx = events_df["asBase"] & events_idx
        as_shares_idx = ~events_df["asBase"] & events_idx
        events_df.loc[as_base_idx, "base_delta"] = events_df.loc[as_base_idx, "amount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )
        events_df.loc[as_shares_idx, "vault_share_delta"] = events_df.loc[as_shares_idx, "amount"].apply(
            lambda x: Decimal(x) / Decimal(1e18)  # type: ignore
        )

    # Add solo transfer events to events_df
    events_df = pd.concat([events_df, transfer_events_df], axis=0)

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
        "vault_share_delta": "vault_share_delta",
        "asBase": "as_base",
        "vaultSharePrice": "vault_share_price",
    }

    events_df = events_df[list(rename_dict.keys())].rename(columns=rename_dict)

    # Token deltas should always be a number
    assert (~events_df["token_delta"].isnull()).all()
    # Replace any nans in deltas with 0
    # pandas doesn't play nice with types and decimals
    events_df["base_delta"] = events_df["base_delta"].fillna(Decimal(0))  # type: ignore
    events_df["vault_share_delta"] = events_df["vault_share_delta"].fillna(Decimal(0))  # type: ignore
    return events_df


def convert_pool_config(pool_config_dict: dict[str, Any]) -> PoolConfig:
    """Converts a pool_config_dict from a call in hyperdrive_interface to the postgres data type

    Arguments
    ---------
    pool_config_dict: dict[str, Any]
        A dicitonary containing the required pool_config keys.

    Returns
    -------
    PoolConfig
        The db object for pool config
    """
    args_dict = {}
    for key in PoolConfig.__annotations__:
        if key not in pool_config_dict:
            logging.warning("Missing %s from pool config", key)
            value = None
        else:
            value = pool_config_dict[key]
            if isinstance(value, FixedPoint):
                value = Decimal(str(value))
        args_dict[camel_to_snake(key)] = value
    pool_config = PoolConfig(**args_dict)
    return pool_config


def convert_pool_info(pool_info_dict: dict[str, Any]) -> PoolInfo:
    """Converts a pool_info_dict from a call in hyperdrive interface to the postgres data type

    Arguments
    ---------
    pool_info_dict: dict[str, Any]
        The dictionary returned from hyperdrive_instance.get_hyperdrive_pool_info

    Returns
    -------
    PoolInfo
        The db object for pool info
    """
    args_dict = {}
    for key in PoolInfo.__annotations__:
        # Ignore id field
        if key == "id":
            continue
        if key not in pool_info_dict:
            logging.warning("Missing %s from pool info", key)
            value = None
        else:
            value = pool_info_dict[key]
            if isinstance(value, FixedPoint):
                value = Decimal(str(value))
        args_dict[camel_to_snake(key)] = value
    block_pool_info = PoolInfo(**args_dict)
    return block_pool_info

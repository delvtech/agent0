"""Helper functions for interfacing with hyperdrive."""

from __future__ import annotations

from typing import Any, cast

from eth_typing import BlockNumber
from fixedpointmath import FixedPoint
from web3.contract.contract import Contract
from web3.types import Timestamp, TxReceipt

from agent0.ethpy.base import UnknownBlockError, get_transaction_logs
from agent0.hypertypes import IHyperdriveContract
from agent0.hypertypes.fixedpoint_types import CheckpointFP, PoolConfigFP, PoolInfoFP
from agent0.hypertypes.utilities.conversions import (
    camel_to_snake,
    checkpoint_to_fixedpoint,
    pool_config_to_fixedpoint,
    pool_info_to_fixedpoint,
)

from .receipt_breakdown import ReceiptBreakdown


def get_hyperdrive_pool_config(hyperdrive_contract: IHyperdriveContract) -> PoolConfigFP:
    """Get the hyperdrive config from a deployed hyperdrive contract.

    Arguments
    ---------
    hyperdrive_contract: Contract
        The deployed hyperdrive contract instance.

    Returns
    -------
    dict[str, Any]
        The hyperdrive pool config.
    """
    pool_config = hyperdrive_contract.functions.getPoolConfig().call()
    return pool_config_to_fixedpoint(cast(Any, pool_config))


def get_hyperdrive_pool_info(hyperdrive_contract: IHyperdriveContract, block_number: BlockNumber) -> PoolInfoFP:
    """Get the block pool info from the Hyperdrive contract.

    Arguments
    ---------
    hyperdrive_contract: Contract
        The contract to query the pool info from.
    block_number: BlockNumber
        The block number to query from the chain.

    Returns
    -------
    dict[str, Any]
        A dictionary containing the Hyperdrive pool info returned from the smart contract.
    """
    pool_info = hyperdrive_contract.functions.getPoolInfo().call(None, block_number)
    return pool_info_to_fixedpoint(pool_info)


def get_hyperdrive_checkpoint(
    hyperdrive_contract: IHyperdriveContract, checkpoint_time: Timestamp, block_number: BlockNumber
) -> CheckpointFP:
    """Get the checkpoint info for the Hyperdrive contract at a given block.

    Arguments
    ---------
    hyperdrive_contract: IHyperdriveContract
        The contract to query the pool info from.
    checkpoint_time: Timestamp
        The block timestamp that indexes the checkpoint to get.
    block_number: BlockNumber
        The block number to query from the chain.

    Returns
    -------
    CheckpointFP
        The dataclass containing the checkpoint info in fixed point
    """
    checkpoint = hyperdrive_contract.functions.getCheckpoint(checkpoint_time).call(None, block_number)
    return checkpoint_to_fixedpoint(checkpoint)


def get_hyperdrive_checkpoint_exposure(
    hyperdrive_contract: IHyperdriveContract, checkpoint_time: Timestamp, block_number: BlockNumber
) -> FixedPoint:
    """Get the checkpoint exposure for the Hyperdrive contract at a given block.

    Arguments
    ---------
    hyperdrive_contract: IHyperdriveContract
        The contract to query the pool info from.
    checkpoint_time: Timestamp
        The block timestamp that indexes the checkpoint to get.
        This must be an exact checkpoint time for the deployed pool.
    block_number: BlockNumber
        The block number to query from the chain.

    Returns
    -------
    CheckpointFP
        The dataclass containing the checkpoint info in fixed point.
    """
    exposure = hyperdrive_contract.functions.getCheckpointExposure(checkpoint_time).call(None, block_number)
    return FixedPoint(scaled_value=exposure)


def parse_logs(tx_receipt: TxReceipt, hyperdrive_contract: Contract, fn_name: str) -> ReceiptBreakdown:
    """Decode a Hyperdrive contract transaction receipt to get the changes to the agent's funds.

    Arguments
    ---------
    tx_receipt: TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    hyperdrive_contract: Contract
        The deployed Hyperdrive web3 contract
    fn_name: str
        This function must exist in the compiled contract's ABI

    Returns
    -------
    ReceiptBreakdown
        A dataclass containing the maturity time and the absolute values for token quantities changed
    """
    # Sometimes, smart contract transact fails with status 0 with no error message
    # We throw custom error to catch in trades loop, ignore, and move on
    # TODO need to track down why this call fails and handle better
    status = tx_receipt.get("status", None)
    if status is None:
        raise AssertionError("Receipt did not return status")
    if status == 0:
        raise UnknownBlockError("Receipt has status of 0", f"{tx_receipt=}")
    hyperdrive_event_logs = get_transaction_logs(
        hyperdrive_contract,
        tx_receipt,
        event_names=[fn_name[0].capitalize() + fn_name[1:]],
    )
    if len(hyperdrive_event_logs) == 0:
        raise AssertionError("Transaction receipt had no logs", f"{tx_receipt=}")
    if len(hyperdrive_event_logs) > 1:
        raise AssertionError("Too many logs found")
    log_args = hyperdrive_event_logs[0]["args"]

    trade_result = ReceiptBreakdown()
    values = ["trader", "destination", "provider", "assetId", "checkpointTime", "asBase"]
    fixedpoint_values = [
        "amount",
        "bondAmount",
        "lpAmount",
        "withdrawalShareAmount",
        "vaultSharePrice",
        "checkpointVaultSharePrice",
        "baseProceeds",
        "basePayment",
        "lpSharePrice",
        "maturedShorts",
        "maturedLongs",
    ]

    if "maturityTime" in log_args:
        trade_result.maturity_time_seconds = log_args["maturityTime"]

    for value in values:
        if value in log_args and hasattr(trade_result, camel_to_snake(value)):
            setattr(trade_result, camel_to_snake(value), log_args[value])

    for value in fixedpoint_values:
        if value in log_args and hasattr(trade_result, camel_to_snake(value)):
            setattr(trade_result, camel_to_snake(value), FixedPoint(scaled_value=log_args[value]))

    return trade_result


def get_event_history_from_chain(
    hyperdrive_contract: Contract, from_block: int, to_block: int, wallet_addr: str | None = None
) -> dict:
    """Helper function to query event logs directly from the chain.
    Useful for debugging open positions of wallet addresses.
    This might be creating unnecessary filters if ran, so only use for debugging

    Arguments
    ---------
    hyperdrive_contract: Contract
        The deployed hyperdrive contract instance.
    from_block: int
        The starting block to query
    to_block: int
        The end block to query. If from_block == to_block, will query the specified block number
    wallet_addr: str | None, optional
        The wallet address to filter events on. If None, will return all.

    Returns
    -------
    dict
        A dictionary of event logs, keyed by the event name. Specifically:
        # TODO figure out return type of web3 call
        "addLiquidity": list[Unknown]
        "removeLiquidity": list[Unknown]
        "redeemWithdrawalShares": list[Unknown]
        "openLong": list[Unknown]
        "closeLong": list[Unknown]
        "openShort": list[Unknown]
        "closeShort": list[Unknown]
        "total_events": int
    """
    # TODO clean up this function
    # pylint: disable=too-many-locals

    # Build arguments
    lp_addr_filter = {}
    trade_addr_filter = {}
    if wallet_addr is not None:
        lp_addr_filter = {"provider": wallet_addr}
        trade_addr_filter = {"trader": wallet_addr}
    lp_filter_args = {"fromBlock": from_block, "toBlock": to_block, "argument_filters": lp_addr_filter}
    trade_filter_args = {"fromBlock": from_block, "toBlock": to_block, "argument_filters": trade_addr_filter}

    # Create filter on events
    # Typing doesn't know about create_filter function with various events
    add_lp_event_filter = hyperdrive_contract.events.AddLiquidity.create_filter(**lp_filter_args)  # type: ignore
    remove_lp_event_filter = hyperdrive_contract.events.RemoveLiquidity.create_filter(  # type:ignore
        **lp_filter_args
    )
    withdraw_event_filter = hyperdrive_contract.events.RedeemWithdrawalShares.create_filter(  # type:ignore
        **lp_filter_args
    )
    open_long_event_filter = hyperdrive_contract.events.OpenLong.create_filter(  # type:ignore
        **trade_filter_args
    )
    close_long_event_filter = hyperdrive_contract.events.CloseLong.create_filter(  # type:ignore
        **trade_filter_args
    )
    open_short_event_filter = hyperdrive_contract.events.OpenShort.create_filter(  # type:ignore
        **trade_filter_args
    )
    close_short_event_filter = hyperdrive_contract.events.CloseShort.create_filter(  # type:ignore
        **trade_filter_args
    )

    # Retrieve all entries
    add_lp_events = add_lp_event_filter.get_all_entries()
    remove_lp_events = remove_lp_event_filter.get_all_entries()
    withdraw_events = withdraw_event_filter.get_all_entries()
    open_long_events = open_long_event_filter.get_all_entries()
    close_long_events = close_long_event_filter.get_all_entries()
    open_short_events = open_short_event_filter.get_all_entries()
    close_short_events = close_short_event_filter.get_all_entries()

    # Calculate total events on chain
    total_events = (
        len(add_lp_events)
        + len(remove_lp_events)
        + len(withdraw_events)
        + len(open_long_events)
        + len(close_long_events)
        + len(open_short_events)
        + len(close_short_events)
    )

    return {
        "addLiquidity": add_lp_events,
        "removeLiquidity": remove_lp_events,
        "redeemWithdrawalShares": withdraw_events,
        "openLong": open_long_events,
        "closeLong": close_long_events,
        "openShort": open_short_events,
        "closeShort": close_short_events,
        "total_events": total_events,
    }

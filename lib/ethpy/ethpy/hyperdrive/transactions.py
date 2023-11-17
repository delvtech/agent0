"""Helper functions for interfacing with hyperdrive."""
from __future__ import annotations

from eth_typing import BlockNumber
from eth_utils import address
from ethpy.base import UnknownBlockError, get_transaction_logs, smart_contract_read
from ethpy.hyperdrive.state.conversions import (
    contract_checkpoint_to_hypertypes,
    contract_pool_config_to_hypertypes,
    contract_pool_info_to_hypertypes,
    hypertypes_checkpoint_to_fixedpoint,
    hypertypes_pool_config_to_fixedpoint,
    hypertypes_pool_info_to_fixedpoint,
)
from fixedpointmath import FixedPoint
from web3 import Web3
from web3.contract.contract import Contract
from web3.types import Timestamp, TxReceipt

from .addresses import HyperdriveAddresses
from .receipt_breakdown import ReceiptBreakdown
from .state import Checkpoint, PoolConfig, PoolInfo


def get_hyperdrive_pool_config(hyperdrive_contract: Contract) -> PoolConfig:
    """Get the hyperdrive config from a deployed hyperdrive contract.

    Arguments
    ----------
    hyperdrive_contract : Contract
        The deployed hyperdrive contract instance.

    Returns
    -------
    dict[str, Any]
        The hyperdrive pool config.
    """
    return hypertypes_pool_config_to_fixedpoint(
        contract_pool_config_to_hypertypes(smart_contract_read(hyperdrive_contract, "getPoolConfig"))
    )


def get_hyperdrive_pool_info(hyperdrive_contract: Contract, block_number: BlockNumber) -> PoolInfo:
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
    return hypertypes_pool_info_to_fixedpoint(
        contract_pool_info_to_hypertypes(
            smart_contract_read(hyperdrive_contract, "getPoolInfo", block_number=block_number)
        )
    )


def get_hyperdrive_checkpoint(hyperdrive_contract: Contract, block_timestamp: Timestamp) -> Checkpoint:
    """Get the checkpoint info for the Hyperdrive contract at a given block.

    Arguments
    ---------
    hyperdrive_contract: Contract
        The contract to query the pool info from
    block_number: BlockNumber
        The block number to query from the chain

    Returns
    -------
    dict[str, int]
        A dictionary containing the checkpoint details.
    """
    return hypertypes_checkpoint_to_fixedpoint(
        contract_checkpoint_to_hypertypes(smart_contract_read(hyperdrive_contract, "getCheckpoint", block_timestamp))
    )


def get_hyperdrive_contract(web3: Web3, abis: dict, addresses: HyperdriveAddresses) -> Contract:
    """Get the hyperdrive contract given abis.

    Arguments
    ---------
    web3: Web3
        web3 provider object
    abis: dict
        A dictionary that contains all abis keyed by the abi name, returned from `load_all_abis`
    addresses: HyperdriveAddressesJson
        The block number to query from the chain

    Returns
    -------
    Contract
        The contract object returned from the query
    """
    if "IERC4626Hyperdrive" not in abis:
        raise AssertionError("IERC4626Hyperdrive ABI was not provided")
    state_abi = abis["IERC4626Hyperdrive"]
    # get contract instance of hyperdrive
    hyperdrive_contract: Contract = web3.eth.contract(
        address=address.to_checksum_address(addresses.mock_hyperdrive), abi=state_abi
    )
    return hyperdrive_contract


def parse_logs(tx_receipt: TxReceipt, hyperdrive_contract: Contract, fn_name: str) -> ReceiptBreakdown:
    """Decode a Hyperdrive contract transaction receipt to get the changes to the agent's funds.

    Arguments
    ---------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    hyperdrive_contract : Contract
        Any deployed web3 contract
    fn_name : str
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
    if "assetId" in log_args:
        trade_result.asset_id = log_args["assetId"]
    if "maturityTime" in log_args:
        trade_result.maturity_time_seconds = log_args["maturityTime"]
    if "baseAmount" in log_args:
        trade_result.base_amount = FixedPoint(scaled_value=log_args["baseAmount"])
    if "bondAmount" in log_args:
        trade_result.bond_amount = FixedPoint(scaled_value=log_args["bondAmount"])
    if "lpAmount" in log_args:
        trade_result.lp_amount = FixedPoint(scaled_value=log_args["lpAmount"])
    if "withdrawalShareAmount" in log_args:
        trade_result.withdrawal_share_amount = FixedPoint(scaled_value=log_args["withdrawalShareAmount"])
    return trade_result


def get_event_history_from_chain(
    hyperdrive_contract: Contract, from_block: int, to_block: int, wallet_addr: str | None = None
) -> dict:
    """Helper function to query event logs directly from the chain.
    Useful for debugging open positions of wallet addresses.
    This might be creating unnecessary filters if ran, so only use for debugging

    Arguments
    ---------
    hyperdrive_contract : Contract
        The deployed hyperdrive contract instance.
    from_block: int
        The starting block to query
    to_block: int
        The end block to query. If from_block == to_block, will query the specified block number
    wallet_addr: str | None
        The wallet address to filter events on. If None, will return all.

    Returns
    -------
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

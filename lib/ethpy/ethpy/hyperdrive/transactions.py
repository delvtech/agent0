"""Helper functions for interfacing with hyperdrive."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

from eth_typing import BlockNumber, ChecksumAddress
from eth_utils import address
from ethpy.base import UnknownBlockError, get_transaction_logs, smart_contract_read
from fixedpointmath import FixedPoint
from web3 import Web3
from web3.contract.contract import Contract
from web3.types import BlockData, Timestamp, TxReceipt

from .addresses import HyperdriveAddresses, camel_to_snake
from .assets import AssetIdPrefix, encode_asset_id
from .receipt_breakdown import ReceiptBreakdown


# TODO: These dataclasses are similar to pypechain except for
#  - snake_case attributes instead of camelCase
#  - FixedPoint types instead of int
#  - nested dataclasses (PoolConfig) include a __post_init__ that allows for
#  instantiation with a nested dictionary
#
# We'd like to rely on the pypechain classes as much as possible.
# One solution could be to build our own interface wrapper that pulls in the pypechain
# dataclass and makes this fixed set of changes?
# pylint: disable=too-many-instance-attributes
@dataclass
class Checkpoint:
    """Checkpoint struct."""

    share_price: FixedPoint
    long_exposure: FixedPoint


@dataclass
class Fees:
    """Fees struct."""

    curve: FixedPoint
    flat: FixedPoint
    governance: FixedPoint


@dataclass
class PoolConfig:
    """PoolConfig struct."""

    base_token: str
    initial_share_price: FixedPoint
    minimum_share_reserves: FixedPoint
    minimum_transaction_amount: FixedPoint
    position_duration: int
    checkpoint_duration: int
    time_stretch: FixedPoint
    governance: str
    fee_collector: str
    fees: Sequence | Fees
    oracle_size: int
    update_gap: int

    def __post_init__(self):
        if isinstance(self.fees, Sequence):
            self.fees: Fees = Fees(*self.fees)


@dataclass
class PoolInfo:
    """PoolInfo struct."""

    share_reserves: FixedPoint
    share_adjustment: FixedPoint
    bond_reserves: FixedPoint
    lp_total_supply: FixedPoint
    share_price: FixedPoint
    longs_outstanding: FixedPoint
    long_average_maturity_time: FixedPoint
    shorts_outstanding: FixedPoint
    short_average_maturity_time: FixedPoint
    withdrawal_shares_ready_to_withdraw: FixedPoint
    withdrawal_shares_proceeds: FixedPoint
    lp_share_price: FixedPoint
    long_exposure: FixedPoint


def get_hyperdrive_pool_config(hyperdrive_contract: Contract) -> dict[str, Any]:
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
    return smart_contract_read(hyperdrive_contract, "getPoolConfig")


def convert_hyperdrive_pool_config_types(pool_config: dict[str, Any]) -> PoolConfig:
    """Convert the pool_config types from what solidity returns to FixedPoint

    Arguments
    ----------
    pool_config : dict[str, Any]
        The hyperdrive pool config.

    Returns
    -------
    PoolConfig
        A dataclass containing the Hyperdrive pool config with modified types.
        This dataclass has the same attributes as the Hyperdrive ABI, with these changes:
          - The attribute names are converted to snake_case.
          - FixedPoint types are used if the type was FixedPoint in the underlying contract.
    """
    # Adjust the pool_config to use snake case here
    pool_config = {camel_to_snake(key): value for key, value in pool_config.items()}
    # Copy all elements into new out_config
    out_config = pool_config.copy()
    fixedpoint_keys = ["initial_share_price", "minimum_share_reserves", "minimum_transaction_amount", "time_stretch"]
    for key in pool_config:
        if key in fixedpoint_keys:
            out_config[key] = FixedPoint(scaled_value=pool_config[key])
    out_config["fees"] = [FixedPoint(scaled_value=fee) for fee in pool_config["fees"]]
    return PoolConfig(**out_config)


def get_hyperdrive_pool_info(hyperdrive_contract: Contract, block_number: BlockNumber) -> dict[str, Any]:
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
    return smart_contract_read(hyperdrive_contract, "getPoolInfo", block_number=block_number)


def convert_hyperdrive_pool_info_types(pool_info: dict[str, Any]) -> PoolInfo:
    """Convert the pool info types from what solidity returns to FixedPoint.

    Arguments
    ---------
    pool_info : dict[str, Any]
        The hyperdrive pool info.

    Returns
    -------
    PoolInfo
        A dataclass containing the Hyperdrive pool info with modified types.
        This dataclass has the same attributes as the Hyperdrive ABI, with these changes:
          - The attribute names are converted to snake_case.
          - FixedPoint types are used if the type was FixedPoint in the underlying contract.
    """
    return PoolInfo(**{camel_to_snake(key): FixedPoint(scaled_value=value) for (key, value) in pool_info.items()})


def get_hyperdrive_checkpoint(hyperdrive_contract: Contract, block_timestamp: Timestamp) -> dict[str, int]:
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
    return smart_contract_read(hyperdrive_contract, "getCheckpoint", block_timestamp)


def convert_hyperdrive_checkpoint_types(checkpoint: dict[str, int]) -> Checkpoint:
    """Convert the checkpoint types from what solidity returns to FixedPoint.

    Arguments
    ---------
    checkpoint : dict[str, int]
        A dictionary containing the checkpoint details.

    Returns
    -------
    Checkpoint
        A dataclass containing the checkpoint share_price and long_exposure fields converted to FixedPoint.
    """
    return Checkpoint(**{camel_to_snake(key): FixedPoint(scaled_value=value) for key, value in checkpoint.items()})


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
    if "IHyperdrive" not in abis:
        raise AssertionError("IHyperdrive ABI was not provided")
    state_abi = abis["IHyperdrive"]
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

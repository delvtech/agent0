"""Helper functions for interfacing with hyperdrive."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast, overload

from fixedpointmath import FixedPoint
from web3 import Web3
from web3.types import BlockIdentifier, Timestamp, TxReceipt

from agent0.ethpy.base import get_transaction_logs
from agent0.hypertypes import IHyperdriveContract
from agent0.hypertypes.fixedpoint_types import CheckpointFP, PoolConfigFP, PoolInfoFP
from agent0.hypertypes.utilities.conversions import (
    camel_to_snake,
    checkpoint_to_fixedpoint,
    pool_config_to_fixedpoint,
    pool_info_to_fixedpoint,
)

from .event_types import (
    AddLiquidity,
    BaseHyperdriveEvent,
    CloseLong,
    CloseShort,
    CreateCheckpoint,
    OpenLong,
    OpenShort,
    RedeemWithdrawalShares,
    RemoveLiquidity,
)

if TYPE_CHECKING:
    from .interface import HyperdriveReadInterface


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


def get_hyperdrive_pool_info(hyperdrive_contract: IHyperdriveContract, block_identifier: BlockIdentifier) -> PoolInfoFP:
    """Get the block pool info from the Hyperdrive contract.

    Arguments
    ---------
    hyperdrive_contract: Contract
        The contract to query the pool info from.
    block_identifier: BlockIdentifier
        The block identifier to query from the chain.

    Returns
    -------
    dict[str, Any]
        A dictionary containing the Hyperdrive pool info returned from the smart contract.
    """
    pool_info = hyperdrive_contract.functions.getPoolInfo().call(None, block_identifier)
    return pool_info_to_fixedpoint(pool_info)


def get_hyperdrive_checkpoint(
    hyperdrive_contract: IHyperdriveContract, checkpoint_time: Timestamp, block_identifier: BlockIdentifier
) -> CheckpointFP:
    """Get the checkpoint info for the Hyperdrive contract at a given block.

    Arguments
    ---------
    hyperdrive_contract: IHyperdriveContract
        The contract to query the pool info from.
    checkpoint_time: Timestamp
        The block timestamp that indexes the checkpoint to get.
    block_identifier: BlockIdentifier
        The block number to query from the chain.

    Returns
    -------
    CheckpointFP
        The dataclass containing the checkpoint info in fixed point
    """
    checkpoint = hyperdrive_contract.functions.getCheckpoint(checkpoint_time).call(None, block_identifier)
    return checkpoint_to_fixedpoint(checkpoint)


def get_hyperdrive_checkpoint_exposure(
    hyperdrive_contract: IHyperdriveContract, checkpoint_time: Timestamp, block_identifier: BlockIdentifier
) -> FixedPoint:
    """Get the checkpoint exposure for the Hyperdrive contract at a given block.

    Arguments
    ---------
    hyperdrive_contract: IHyperdriveContract
        The contract to query the pool info from.
    checkpoint_time: Timestamp
        The block timestamp that indexes the checkpoint to get.
        This must be an exact checkpoint time for the deployed pool.
    block_identifier: BlockIdentifier
        The block number to query from the chain.

    Returns
    -------
    CheckpointFP
        The dataclass containing the checkpoint info in fixed point.
    """
    exposure = hyperdrive_contract.functions.getCheckpointExposure(checkpoint_time).call(None, block_identifier)
    return FixedPoint(scaled_value=exposure)


@overload
def parse_logs_to_event(
    tx_receipt: TxReceipt, interface: HyperdriveReadInterface, fn_name: Literal["createCheckpoint"]
) -> CreateCheckpoint: ...


@overload
def parse_logs_to_event(
    tx_receipt: TxReceipt, interface: HyperdriveReadInterface, fn_name: Literal["openLong"]
) -> OpenLong: ...


@overload
def parse_logs_to_event(
    tx_receipt: TxReceipt, interface: HyperdriveReadInterface, fn_name: Literal["closeLong"]
) -> CloseLong: ...


@overload
def parse_logs_to_event(
    tx_receipt: TxReceipt, interface: HyperdriveReadInterface, fn_name: Literal["openShort"]
) -> OpenShort: ...


@overload
def parse_logs_to_event(
    tx_receipt: TxReceipt, interface: HyperdriveReadInterface, fn_name: Literal["closeShort"]
) -> CloseShort: ...


@overload
def parse_logs_to_event(
    tx_receipt: TxReceipt, interface: HyperdriveReadInterface, fn_name: Literal["addLiquidity"]
) -> AddLiquidity: ...


@overload
def parse_logs_to_event(
    tx_receipt: TxReceipt, interface: HyperdriveReadInterface, fn_name: Literal["removeLiquidity"]
) -> RemoveLiquidity: ...


@overload
def parse_logs_to_event(
    tx_receipt: TxReceipt,
    interface: HyperdriveReadInterface,
    fn_name: Literal["redeemWithdrawalShares"],
) -> RedeemWithdrawalShares: ...


def parse_logs_to_event(tx_receipt: TxReceipt, interface: HyperdriveReadInterface, fn_name: str) -> BaseHyperdriveEvent:
    """Decode a Hyperdrive contract transaction receipt to get the changes to the agent's funds.

    Arguments
    ---------
    tx_receipt: TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    interface: HyperdriveReadInterface
        The interface to the Hyperdrive contract.
    fn_name: str
        This function must exist in the compiled contract's ABI

    Returns
    -------
    BaseHyperdriveEvent
        A dataclass that maps to the emitted Hyperdrive events
    """
    # pylint: disable=too-many-branches

    # Sanity check, these status should be checked in smart_contract_transact
    status = tx_receipt.get("status", None)
    if status is None:
        raise AssertionError("Receipt did not return status")
    if status == 0:
        raise AssertionError("Receipt has status of 0")

    hyperdrive_event_logs = get_transaction_logs(
        interface.hyperdrive_contract,
        tx_receipt,
        event_names=[fn_name[0].capitalize() + fn_name[1:]],
    )
    if len(hyperdrive_event_logs) == 0:
        raise AssertionError("Transaction receipt had no logs", f"{tx_receipt=}")
    if len(hyperdrive_event_logs) > 1:
        raise AssertionError("Too many logs found")
    event_logs = hyperdrive_event_logs[0]
    log_args = event_logs["args"]

    # Convert solidity types to python types
    values = ["trader", "destination", "provider", "assetId", "checkpointTime", "asBase", "maturityTime"]
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

    event_args_dict = {}
    for value in values:
        if value in log_args:
            event_args_dict[camel_to_snake(value)] = log_args[value]

    for value in fixedpoint_values:
        if value in log_args:
            event_args_dict[camel_to_snake(value)] = FixedPoint(scaled_value=log_args[value])

    # If hyperdrive is steth, convert the amount from lido shares to steth
    if interface.hyperdrive_kind == interface.HyperdriveKind.STETH:
        # TODO consider not converting the amount to steth here

        # The vault share price should be in every event
        if "vault_share_price" not in event_args_dict:
            raise AssertionError("vault_share_price not found in event.")
        vault_share_price = event_args_dict["vault_share_price"]
        if "amount" in event_args_dict:
            event_args_dict["amount"] *= vault_share_price
        if "base_proceeds" in event_args_dict:
            event_args_dict["base_proceeds"] *= vault_share_price
        if "base_payment" in event_args_dict:
            event_args_dict["base_payment"] *= vault_share_price

    # Build event objects based on fn_name
    if fn_name == "createCheckpoint":
        out_event = CreateCheckpoint(
            block_number=event_logs["blockNumber"],
            transaction_hash=event_logs["transactionHash"].to_0x_hex(),
            checkpoint_time=event_args_dict["checkpoint_time"],
            vault_share_price=event_args_dict["vault_share_price"],
            checkpoint_vault_share_price=event_args_dict["checkpoint_vault_share_price"],
            matured_shorts=event_args_dict["matured_shorts"],
            matured_longs=event_args_dict["matured_longs"],
            lp_share_price=event_args_dict["lp_share_price"],
        )
    elif fn_name == "openLong":
        out_event = OpenLong(
            block_number=event_logs["blockNumber"],
            transaction_hash=event_logs["transactionHash"].to_0x_hex(),
            trader=Web3.to_checksum_address(event_args_dict["trader"]),
            asset_id=event_args_dict["asset_id"],
            maturity_time=event_args_dict["maturity_time"],
            amount=event_args_dict["amount"],
            vault_share_price=event_args_dict["vault_share_price"],
            as_base=event_args_dict["as_base"],
            bond_amount=event_args_dict["bond_amount"],
        )
    elif fn_name == "closeLong":
        out_event = CloseLong(
            block_number=event_logs["blockNumber"],
            transaction_hash=event_logs["transactionHash"].to_0x_hex(),
            trader=Web3.to_checksum_address(event_args_dict["trader"]),
            destination=Web3.to_checksum_address(event_args_dict["destination"]),
            asset_id=event_args_dict["asset_id"],
            maturity_time=event_args_dict["maturity_time"],
            amount=event_args_dict["amount"],
            vault_share_price=event_args_dict["vault_share_price"],
            as_base=event_args_dict["as_base"],
            bond_amount=event_args_dict["bond_amount"],
        )
    elif fn_name == "openShort":
        out_event = OpenShort(
            block_number=event_logs["blockNumber"],
            transaction_hash=event_logs["transactionHash"].to_0x_hex(),
            trader=Web3.to_checksum_address(event_args_dict["trader"]),
            asset_id=event_args_dict["asset_id"],
            maturity_time=event_args_dict["maturity_time"],
            amount=event_args_dict["amount"],
            vault_share_price=event_args_dict["vault_share_price"],
            as_base=event_args_dict["as_base"],
            base_proceeds=event_args_dict["base_proceeds"],
            bond_amount=event_args_dict["bond_amount"],
        )
    elif fn_name == "closeShort":
        out_event = CloseShort(
            block_number=event_logs["blockNumber"],
            transaction_hash=event_logs["transactionHash"].to_0x_hex(),
            trader=Web3.to_checksum_address(event_args_dict["trader"]),
            destination=Web3.to_checksum_address(event_args_dict["destination"]),
            asset_id=event_args_dict["asset_id"],
            maturity_time=event_args_dict["maturity_time"],
            amount=event_args_dict["amount"],
            vault_share_price=event_args_dict["vault_share_price"],
            as_base=event_args_dict["as_base"],
            base_payment=event_args_dict["base_payment"],
            bond_amount=event_args_dict["bond_amount"],
        )
    elif fn_name == "addLiquidity":
        out_event = AddLiquidity(
            block_number=event_logs["blockNumber"],
            transaction_hash=event_logs["transactionHash"].to_0x_hex(),
            provider=Web3.to_checksum_address(event_args_dict["provider"]),
            lp_amount=event_args_dict["lp_amount"],
            amount=event_args_dict["amount"],
            vault_share_price=event_args_dict["vault_share_price"],
            as_base=event_args_dict["as_base"],
            lp_share_price=event_args_dict["lp_share_price"],
        )
    elif fn_name == "removeLiquidity":
        out_event = RemoveLiquidity(
            block_number=event_logs["blockNumber"],
            transaction_hash=event_logs["transactionHash"].to_0x_hex(),
            provider=Web3.to_checksum_address(event_args_dict["provider"]),
            destination=Web3.to_checksum_address(event_args_dict["destination"]),
            lp_amount=event_args_dict["lp_amount"],
            amount=event_args_dict["amount"],
            vault_share_price=event_args_dict["vault_share_price"],
            as_base=event_args_dict["as_base"],
            withdrawal_share_amount=event_args_dict["withdrawal_share_amount"],
            lp_share_price=event_args_dict["lp_share_price"],
        )
    elif fn_name == "redeemWithdrawalShares":
        out_event = RedeemWithdrawalShares(
            block_number=event_logs["blockNumber"],
            transaction_hash=event_logs["transactionHash"].to_0x_hex(),
            provider=Web3.to_checksum_address(event_args_dict["provider"]),
            destination=Web3.to_checksum_address(event_args_dict["destination"]),
            withdrawal_share_amount=event_args_dict["withdrawal_share_amount"],
            amount=event_args_dict["amount"],
            vault_share_price=event_args_dict["vault_share_price"],
            as_base=event_args_dict["as_base"],
        )
    else:
        raise AssertionError("Unknown function name", f"{fn_name=}")
    return out_event

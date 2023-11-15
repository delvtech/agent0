"""HyperdriveInterface functions that require a contract call."""
from __future__ import annotations

from typing import TYPE_CHECKING

from eth_utils.currency import MAX_WEI
from ethpy.base import (
    async_smart_contract_transact,
    get_account_balance,
    smart_contract_preview_transaction,
    smart_contract_read,
)
from ethpy.hyperdrive import AssetIdPrefix, encode_asset_id
from ethpy.hyperdrive.transactions import parse_logs
from fixedpointmath import FixedPoint
from web3 import Web3

if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount
    from eth_typing import BlockNumber
    from ethpy.hyperdrive.receipt_breakdown import ReceiptBreakdown
    from web3.contract.contract import Contract
    from web3.types import Nonce

    from .api import HyperdriveInterface


def _get_total_supply_withdrawal_shares(
    hyperdrive_contract: Contract, block_number: BlockNumber | None = None
) -> FixedPoint:
    """See API for documentation."""
    asset_id = encode_asset_id(AssetIdPrefix.WITHDRAWAL_SHARE, 0)
    total_supply_withdrawal_shares = smart_contract_read(
        hyperdrive_contract,
        "balanceOf",
        asset_id,
        hyperdrive_contract.address,
        block_number=block_number,
    )["value"]
    return FixedPoint(scaled_value=int(total_supply_withdrawal_shares))


def _get_variable_rate(yield_contract: Contract, block_number: BlockNumber | None = None) -> FixedPoint:
    """See API for documentation."""
    rate = smart_contract_read(yield_contract, "getRate", block_number=block_number)["value"]
    return FixedPoint(scaled_value=rate)


def _get_vault_shares(
    yield_contract: Contract,
    hyperdrive_contract: Contract,
    block_number: BlockNumber | None = None,
) -> FixedPoint:
    """See API for documentation."""
    vault_shares = smart_contract_read(
        yield_contract,
        "balanceOf",
        (hyperdrive_contract.address),
        block_number=block_number,
    )
    return FixedPoint(scaled_value=int(vault_shares["value"]))


def _get_eth_base_balances(interface: HyperdriveInterface, agent: LocalAccount) -> tuple[FixedPoint, FixedPoint]:
    """See API for documentation."""
    agent_checksum_address = Web3.to_checksum_address(agent.address)
    agent_eth_balance = get_account_balance(interface.web3, agent_checksum_address)
    agent_base_balance = smart_contract_read(
        interface.base_token_contract,
        "balanceOf",
        agent_checksum_address,
    )["value"]
    return (
        FixedPoint(scaled_value=agent_eth_balance),
        FixedPoint(scaled_value=agent_base_balance),
    )


async def _async_open_long(
    interface: HyperdriveInterface,
    agent: LocalAccount,
    trade_amount: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
    nonce: Nonce | None = None,
) -> ReceiptBreakdown:
    """See API for documentation."""
    agent_checksum_address = Web3.to_checksum_address(agent.address)
    # min_share_price : int
    #   Minium share price at which to open the long.
    #   This allows traders to protect themselves from opening a long in
    #   a checkpoint where negative interest has accrued.
    min_share_price = 0  # TODO: give the user access to this parameter
    min_output = 0  # TODO: give the user access to this parameter

    fn_args = (
        trade_amount.scaled_value,
        min_output,
        min_share_price,
        (  # IHyperdrive.Options
            agent_checksum_address,  # destination
            True,  # asBase
            bytes(0),  # extraData
        ),
    )
    # To catch any solidity errors, we always preview transactions on the current block
    # before calling smart contract transact
    # Since current_pool_state.block_number is a property, we want to get the static block here
    current_block = interface.current_pool_state.block_number
    preview_result = smart_contract_preview_transaction(
        interface.hyperdrive_contract,
        agent_checksum_address,
        "openLong",
        *fn_args,
        block_number=current_block,
    )
    if slippage_tolerance is not None:
        min_output = (
            FixedPoint(scaled_value=preview_result["bondProceeds"]) * (FixedPoint(1) - slippage_tolerance)
        ).scaled_value
        fn_args = (
            trade_amount.scaled_value,
            min_output,
            min_share_price,
            (  # IHyperdrive.Options
                agent_checksum_address,  # destination
                True,  # asBase
                bytes(0),  # extraData
            ),
        )
    try:
        tx_receipt = await async_smart_contract_transact(
            interface.web3, interface.hyperdrive_contract, agent, "openLong", *fn_args, nonce=nonce
        )
        trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "openLong")
    except Exception as exc:
        # We add the preview block as an arg to the exception
        exc.args += (f"Call previewed in block {current_block}",)
        raise exc
    return trade_result


# pylint: disable=too-many-arguments
async def _async_close_long(
    interface: HyperdriveInterface,
    agent: LocalAccount,
    trade_amount: FixedPoint,
    maturity_time: int,
    slippage_tolerance: FixedPoint | None = None,
    nonce: Nonce | None = None,
) -> ReceiptBreakdown:
    """See API for documentation."""
    agent_checksum_address = Web3.to_checksum_address(agent.address)
    min_output = 0
    fn_args = (
        maturity_time,
        trade_amount.scaled_value,
        min_output,
        (  # IHyperdrive.Options
            agent_checksum_address,  # destination
            True,  # asBase
            bytes(0),  # extraData
        ),
    )
    # To catch any solidity errors, we always preview transactions on the current block
    # before calling smart contract transact
    # Since current_pool_state.block_number is a property, we want to get the static block here
    current_block = interface.current_pool_state.block_number
    preview_result = smart_contract_preview_transaction(
        interface.hyperdrive_contract,
        agent_checksum_address,
        "closeLong",
        *fn_args,
        block_number=current_block,
    )
    if slippage_tolerance:
        min_output = (
            FixedPoint(scaled_value=preview_result["value"]) * (FixedPoint(1) - slippage_tolerance)
        ).scaled_value
        fn_args = (
            maturity_time,
            trade_amount.scaled_value,
            min_output,
            (  # IHyperdrive.Options
                agent_checksum_address,  # destination
                True,  # asBase
                bytes(0),  # extraData
            ),
        )
    try:
        tx_receipt = await async_smart_contract_transact(
            interface.web3, interface.hyperdrive_contract, agent, "closeLong", *fn_args, nonce=nonce
        )
        trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "closeLong")
    except Exception as exc:
        # We add the preview block as an arg to the exception
        exc.args += (f"Call previewed in block {current_block}",)
        raise exc
    return trade_result


async def _async_open_short(
    interface: HyperdriveInterface,
    agent: LocalAccount,
    trade_amount: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
    nonce: Nonce | None = None,
) -> ReceiptBreakdown:
    """See API for documentation."""
    agent_checksum_address = Web3.to_checksum_address(agent.address)
    max_deposit = int(MAX_WEI)
    # min_share_price : int
    #   Minium share price at which to open the short.
    #   This allows traders to protect themselves from opening a long in
    #   a checkpoint where negative interest has accrued.
    min_share_price = 0  # TODO: give the user access to this parameter
    fn_args = (
        trade_amount.scaled_value,
        max_deposit,
        min_share_price,
        (  # IHyperdrive.Options
            agent_checksum_address,  # destination
            True,  # asBase
            bytes(0),  # extraData
        ),
    )
    # To catch any solidity errors, we always preview transactions on the current block
    # before calling smart contract transact
    # Since current_pool_state.block_number is a property, we want to get the static block here
    current_block = interface.current_pool_state.block_number
    preview_result = smart_contract_preview_transaction(
        interface.hyperdrive_contract,
        agent_checksum_address,
        "openShort",
        *fn_args,
        block_number=current_block,
    )
    if slippage_tolerance:
        max_deposit = (
            FixedPoint(scaled_value=preview_result["traderDeposit"]) * (FixedPoint(1) + slippage_tolerance)
        ).scaled_value
        fn_args = (
            trade_amount.scaled_value,
            max_deposit,
            min_share_price,
            (  # IHyperdrive.Options
                agent_checksum_address,  # destination
                True,  # asBase
                bytes(0),  # extraData
            ),
        )
    try:
        tx_receipt = await async_smart_contract_transact(
            interface.web3, interface.hyperdrive_contract, agent, "openShort", *fn_args, nonce=nonce
        )
        trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "openShort")
    except Exception as exc:
        # We add the preview block as an arg to the exception
        exc.args += (f"Call previewed in block {current_block}",)
        raise exc
    return trade_result


# pylint: disable=too-many-arguments
async def _async_close_short(
    interface: HyperdriveInterface,
    agent: LocalAccount,
    trade_amount: FixedPoint,
    maturity_time: int,
    slippage_tolerance: FixedPoint | None = None,
    nonce: Nonce | None = None,
) -> ReceiptBreakdown:
    """See API for documentation."""
    agent_checksum_address = Web3.to_checksum_address(agent.address)
    min_output = 0
    fn_args = (
        maturity_time,
        trade_amount.scaled_value,
        min_output,
        (  # IHyperdrive.Options
            agent_checksum_address,  # destination
            True,  # asBase
            bytes(0),  # extraData
        ),
    )
    # To catch any solidity errors, we always preview transactions on the current block
    # before calling smart contract transact
    # Since current_pool_state.block_number is a property, we want to get the static block here
    current_block = interface.current_pool_state.block_number
    preview_result = smart_contract_preview_transaction(
        interface.hyperdrive_contract,
        agent_checksum_address,
        "closeShort",
        *fn_args,
        block_number=current_block,
    )
    if slippage_tolerance:
        min_output = (
            FixedPoint(scaled_value=preview_result["value"]) * (FixedPoint(1) - slippage_tolerance)
        ).scaled_value
        fn_args = (
            maturity_time,
            trade_amount.scaled_value,
            min_output,
            (  # IHyperdrive.Options
                agent_checksum_address,  # destination
                True,  # asBase
                bytes(0),  # extraData
            ),
        )
    try:
        tx_receipt = await async_smart_contract_transact(
            interface.web3,
            interface.hyperdrive_contract,
            agent,
            "closeShort",
            *fn_args,
            nonce=nonce,
        )
        trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "closeShort")
    except Exception as exc:
        # We add the preview block as an arg to the exception
        exc.args += (f"Call previewed in block {current_block}",)
        raise exc
    return trade_result


# pylint: disable=too-many-arguments
async def _async_add_liquidity(
    interface: HyperdriveInterface,
    agent: LocalAccount,
    trade_amount: FixedPoint,
    min_apr: FixedPoint,
    max_apr: FixedPoint,
    nonce: Nonce | None = None,
) -> ReceiptBreakdown:
    """See API for documentation."""
    agent_checksum_address = Web3.to_checksum_address(agent.address)
    fn_args = (
        trade_amount.scaled_value,
        min_apr.scaled_value,
        max_apr.scaled_value,
        (  # IHyperdrive.Options
            agent_checksum_address,  # destination
            True,  # asBase
            bytes(0),  # extraData
        ),
    )
    # To catch any solidity errors, we always preview transactions on the current block
    # before calling smart contract transact
    # Since current_pool_state.block_number is a property, we want to get the static block here
    current_block = interface.current_pool_state.block_number
    _ = smart_contract_preview_transaction(
        interface.hyperdrive_contract,
        agent_checksum_address,
        "addLiquidity",
        *fn_args,
        block_number=current_block,
    )
    # TODO add slippage controls for add liquidity
    try:
        tx_receipt = await async_smart_contract_transact(
            interface.web3,
            interface.hyperdrive_contract,
            agent,
            "addLiquidity",
            *fn_args,
            nonce=nonce,
        )
        trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "addLiquidity")
    except Exception as exc:
        # We add the preview block as an arg to the exception
        exc.args += (f"Call previewed in block {current_block}",)
        raise exc
    return trade_result


async def _async_remove_liquidity(
    interface: HyperdriveInterface,
    agent: LocalAccount,
    trade_amount: FixedPoint,
    nonce: Nonce | None = None,
) -> ReceiptBreakdown:
    """See API for documentation."""
    agent_checksum_address = Web3.to_checksum_address(agent.address)
    min_output = 0
    fn_args = (
        trade_amount.scaled_value,
        min_output,
        (  # IHyperdrive.Options
            agent_checksum_address,  # destination
            True,  # asBase
            bytes(0),  # extraData
        ),
    )
    # To catch any solidity errors, we always preview transactions on the current block
    # before calling smart contract transact
    # Since current_pool_state.block_number is a property, we want to get the static block here
    current_block = interface.current_pool_state.block_number
    _ = smart_contract_preview_transaction(
        interface.hyperdrive_contract,
        agent_checksum_address,
        "removeLiquidity",
        *fn_args,
        block_number=current_block,
    )
    try:
        tx_receipt = await async_smart_contract_transact(
            interface.web3,
            interface.hyperdrive_contract,
            agent,
            "removeLiquidity",
            *fn_args,
            nonce=nonce,
        )
        trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "removeLiquidity")
    except Exception as exc:
        # We add the preview block as an arg to the exception
        exc.args += (f"Call previewed in block {current_block}",)
        raise exc
    return trade_result


async def _async_redeem_withdraw_shares(
    interface: HyperdriveInterface,
    agent: LocalAccount,
    trade_amount: FixedPoint,
    nonce: Nonce | None = None,
) -> ReceiptBreakdown:
    """See API for documentation."""
    # for now, assume an underlying vault share price of at least 1, should be higher by a bit
    agent_checksum_address = Web3.to_checksum_address(agent.address)
    min_output = FixedPoint(scaled_value=1)
    fn_args = (
        trade_amount.scaled_value,
        min_output.scaled_value,
        (  # IHyperdrive.Options
            agent_checksum_address,  # destination
            True,  # asBase
            bytes(0),  # extraData
        ),
    )
    # To catch any solidity errors, we always preview transactions on the current block
    # before calling smart contract transact
    # Since current_pool_state.block_number is a property, we want to get the static block here
    current_block = interface.current_pool_state.block_number
    preview_result = smart_contract_preview_transaction(
        interface.hyperdrive_contract,
        agent_checksum_address,
        "redeemWithdrawalShares",
        *fn_args,
        block_number=current_block,
    )

    # Here, a preview call of redeem withdrawal shares will still be successful without logs if
    # the amount of shares to redeem is larger than what's in the wallet. We want to catch this error
    # here with a useful error message, so we check that explicitly here
    if preview_result["sharesRedeemed"] == 0 and trade_amount > 0:
        raise ValueError("Preview call for redeem withdrawal shares returned 0 for non-zero input trade amount")

    try:
        tx_receipt = await async_smart_contract_transact(
            interface.web3,
            interface.hyperdrive_contract,
            agent,
            "redeemWithdrawalShares",
            *fn_args,
            nonce=nonce,
        )
        trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "redeemWithdrawalShares")
    except Exception as exc:
        # We add the preview block as an arg to the exception
        exc.args += (f"Call previewed in block {current_block}",)
        raise exc
    return trade_result

"""Hyperdrive interface functions that require a contract call."""

from __future__ import annotations

from typing import TYPE_CHECKING

from eth_utils.currency import MAX_WEI
from fixedpointmath import FixedPoint
from web3 import Web3

from agent0.ethpy.base import (
    async_smart_contract_transact,
    get_account_balance,
    smart_contract_preview_transaction,
    smart_contract_transact,
)
from agent0.ethpy.hyperdrive.assets import AssetIdPrefix, encode_asset_id
from agent0.ethpy.hyperdrive.transactions import parse_logs
from agent0.hypertypes import ERC20MintableContract, IERC4626HyperdriveContract, MockERC4626Contract

if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount
    from eth_typing import BlockNumber
    from web3.types import Nonce

    from agent0.ethpy.hyperdrive.receipt_breakdown import ReceiptBreakdown

    from .read_interface import HyperdriveReadInterface
    from .read_write_interface import HyperdriveReadWriteInterface

# Number of arguments is influenced by the underlying solidity contract
# pylint: disable=too-many-arguments


def _get_total_supply_withdrawal_shares(
    hyperdrive_contract: IERC4626HyperdriveContract, block_number: BlockNumber | None = None
) -> FixedPoint:
    """See API for documentation."""
    asset_id = encode_asset_id(AssetIdPrefix.WITHDRAWAL_SHARE, 0)
    total_supply_withdrawal_shares = hyperdrive_contract.functions.balanceOf(
        asset_id, hyperdrive_contract.address
    ).call(block_identifier=block_number or "latest")
    return FixedPoint(scaled_value=int(total_supply_withdrawal_shares))


def _get_variable_rate(yield_contract: MockERC4626Contract, block_number: BlockNumber | None = None) -> FixedPoint:
    """See API for documentation."""
    rate = yield_contract.functions.getRate().call(block_identifier=block_number or "latest")
    return FixedPoint(scaled_value=rate)


def _get_vault_shares(
    yield_contract: MockERC4626Contract,
    hyperdrive_contract: IERC4626HyperdriveContract,
    block_number: BlockNumber | None = None,
) -> FixedPoint:
    """See API for documentation."""
    vault_shares = yield_contract.functions.balanceOf(hyperdrive_contract.address).call(
        block_identifier=block_number or "latest"
    )
    return FixedPoint(scaled_value=vault_shares)


def _get_eth_base_balances(interface: HyperdriveReadInterface, agent: LocalAccount) -> tuple[FixedPoint, FixedPoint]:
    """See API for documentation."""
    agent_checksum_address = Web3.to_checksum_address(agent.address)
    agent_eth_balance = get_account_balance(interface.web3, agent_checksum_address)
    agent_base_balance = interface.base_token_contract.functions.balanceOf(agent_checksum_address).call()
    return (
        FixedPoint(scaled_value=agent_eth_balance),
        FixedPoint(scaled_value=agent_base_balance),
    )


def _get_hyperdrive_base_balance(
    base_contract: ERC20MintableContract,
    hyperdrive_contract: IERC4626HyperdriveContract,
    block_number: BlockNumber | None,
) -> FixedPoint:
    """See API for documentation."""
    base_balance = base_contract.functions.balanceOf(hyperdrive_contract.address).call(
        block_identifier=block_number or "latest"
    )
    return FixedPoint(scaled_value=base_balance)


def _get_hyperdrive_eth_balance(web3, hyperdrive_address) -> FixedPoint:
    """See API for documentation."""
    hyperdrive_checksum_address = Web3.to_checksum_address(hyperdrive_address)
    agent_eth_balance = get_account_balance(web3, hyperdrive_checksum_address)
    return FixedPoint(scaled_value=agent_eth_balance)


def _get_gov_fees_accrued(
    hyperdrive_contract: IERC4626HyperdriveContract,
    block_number: BlockNumber | None,
) -> FixedPoint:
    """See API for documentation."""
    if block_number is None:
        block_identifier = "latest"
    else:
        block_identifier = block_number
    gov_fees_accrued = hyperdrive_contract.functions.getUncollectedGovernanceFees().call(
        block_identifier=block_identifier
    )
    return FixedPoint(scaled_value=gov_fees_accrued)


def _create_checkpoint(
    interface: HyperdriveReadWriteInterface,
    sender: LocalAccount,
    block_number: BlockNumber | None = None,
    checkpoint_time: int | None = None,
) -> ReceiptBreakdown:
    """See API for documentation."""
    if checkpoint_time is None:
        if block_number is None:
            block_timestamp = interface.get_block_timestamp(interface.get_current_block())
        else:
            block_timestamp = interface.get_block_timestamp(interface.get_block(block_number))
        checkpoint_time = interface.calc_checkpoint_id(interface.pool_config.checkpoint_duration, block_timestamp)

    tx_receipt = smart_contract_transact(
        interface.web3,
        interface.hyperdrive_contract,
        sender,
        "checkpoint",
        checkpoint_time,
        read_retry_count=interface.read_retry_count,
        write_retry_count=interface.write_retry_count,
    )
    trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "createCheckpoint")
    return trade_result


def _set_variable_rate(
    interface: HyperdriveReadWriteInterface,
    sender: LocalAccount,
    new_rate: FixedPoint,
) -> None:
    """See API for documentation."""
    _ = smart_contract_transact(
        interface.web3,
        interface.yield_contract,
        sender,
        "setRate",
        new_rate.scaled_value,
        read_retry_count=interface.read_retry_count,
        write_retry_count=interface.write_retry_count,
    )


async def _async_open_long(
    interface: HyperdriveReadWriteInterface,
    agent: LocalAccount,
    trade_amount: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
    nonce: Nonce | None = None,
    preview_before_trade: bool = False,
) -> ReceiptBreakdown:
    """See API for documentation."""
    agent_checksum_address = Web3.to_checksum_address(agent.address)
    # min_vault_share_price: int
    #   Minium share price at which to open the long.
    #   This allows traders to protect themselves from opening a long in
    #   a checkpoint where negative interest has accrued.
    min_vault_share_price = 0  # TODO: give the user access to this parameter
    min_output = 0  # TODO: give the user access to this parameter

    fn_args = (
        trade_amount.scaled_value,
        min_output,
        min_vault_share_price,
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
    preview_result = {}
    if preview_before_trade or slippage_tolerance is not None:
        preview_result = smart_contract_preview_transaction(
            interface.hyperdrive_contract,
            agent_checksum_address,
            "openLong",
            *fn_args,
            block_number=current_block,
            read_retry_count=interface.read_retry_count,
        )
    if slippage_tolerance is not None:
        # ABI doesn't have output names. Return result is [maturityTime, bondProceeds]
        min_output = (
            FixedPoint(scaled_value=preview_result["value1"]) * (FixedPoint(1) - slippage_tolerance)
        ).scaled_value
        fn_args = (
            trade_amount.scaled_value,
            min_output,
            min_vault_share_price,
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
            "openLong",
            *fn_args,
            nonce=nonce,
            read_retry_count=interface.read_retry_count,
            write_retry_count=interface.write_retry_count,
        )
        trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "openLong")
    except Exception as exc:
        # We add the preview block as an arg to the exception
        exc.args += (f"Call previewed in block {current_block}",)
        raise exc
    return trade_result


# pylint: disable=too-many-arguments
async def _async_close_long(
    interface: HyperdriveReadWriteInterface,
    agent: LocalAccount,
    trade_amount: FixedPoint,
    maturity_time: int,
    slippage_tolerance: FixedPoint | None = None,
    nonce: Nonce | None = None,
    preview_before_trade: bool = False,
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
    preview_result = {}
    if preview_before_trade or slippage_tolerance is not None:
        preview_result = smart_contract_preview_transaction(
            interface.hyperdrive_contract,
            agent_checksum_address,
            "closeLong",
            *fn_args,
            block_number=current_block,
            read_retry_count=interface.read_retry_count,
        )
    if slippage_tolerance is not None:
        min_output = (
            FixedPoint(scaled_value=preview_result["value0"]) * (FixedPoint(1) - slippage_tolerance)
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
            "closeLong",
            *fn_args,
            nonce=nonce,
            read_retry_count=interface.read_retry_count,
            write_retry_count=interface.write_retry_count,
        )
        trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "closeLong")
    except Exception as exc:
        # We add the preview block as an arg to the exception
        exc.args += (f"Call previewed in block {current_block}",)
        raise exc
    return trade_result


async def _async_open_short(
    interface: HyperdriveReadWriteInterface,
    agent: LocalAccount,
    trade_amount: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
    nonce: Nonce | None = None,
    preview_before_trade: bool = False,
) -> ReceiptBreakdown:
    """See API for documentation."""
    agent_checksum_address = Web3.to_checksum_address(agent.address)
    max_deposit = int(MAX_WEI)
    # min_vault_share_price: int
    #   Minium share price at which to open the short.
    #   This allows traders to protect themselves from opening a long in
    #   a checkpoint where negative interest has accrued.
    min_vault_share_price = 0  # TODO: give the user access to this parameter
    fn_args = (
        trade_amount.scaled_value,
        max_deposit,
        min_vault_share_price,
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
    preview_result = {}
    if preview_before_trade or slippage_tolerance is not None:
        preview_result = smart_contract_preview_transaction(
            interface.hyperdrive_contract,
            agent_checksum_address,
            "openShort",
            *fn_args,
            block_number=current_block,
            read_retry_count=interface.read_retry_count,
        )
    if slippage_tolerance is not None:
        # ABI doesn't have output names. Return result is [maturityTime, traderDeposit]
        max_deposit = (
            FixedPoint(scaled_value=preview_result["value1"]) * (FixedPoint(1) + slippage_tolerance)
        ).scaled_value
        fn_args = (
            trade_amount.scaled_value,
            max_deposit,
            min_vault_share_price,
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
            "openShort",
            *fn_args,
            nonce=nonce,
            read_retry_count=interface.read_retry_count,
            write_retry_count=interface.write_retry_count,
        )
        trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "openShort")
    except Exception as exc:
        # We add the preview block as an arg to the exception
        exc.args += (f"Call previewed in block {current_block}",)
        raise exc
    return trade_result


async def _async_close_short(
    interface: HyperdriveReadWriteInterface,
    agent: LocalAccount,
    trade_amount: FixedPoint,
    maturity_time: int,
    slippage_tolerance: FixedPoint | None = None,
    nonce: Nonce | None = None,
    preview_before_trade: bool = False,
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
    preview_result = {}
    if preview_before_trade or slippage_tolerance is not None:
        preview_result = smart_contract_preview_transaction(
            interface.hyperdrive_contract,
            agent_checksum_address,
            "closeShort",
            *fn_args,
            block_number=current_block,
            read_retry_count=interface.read_retry_count,
        )
    if slippage_tolerance is not None:
        min_output = (
            FixedPoint(scaled_value=preview_result["value0"]) * (FixedPoint(1) - slippage_tolerance)
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
            read_retry_count=interface.read_retry_count,
            write_retry_count=interface.write_retry_count,
        )
        trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "closeShort")
    except Exception as exc:
        # We add the preview block as an arg to the exception
        exc.args += (f"Call previewed in block {current_block}",)
        raise exc
    return trade_result


async def _async_add_liquidity(
    interface: HyperdriveReadWriteInterface,
    agent: LocalAccount,
    trade_amount: FixedPoint,
    min_apr: FixedPoint,
    max_apr: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
    nonce: Nonce | None = None,
    preview_before_trade: bool = False,
) -> ReceiptBreakdown:
    """See API for documentation."""
    # TODO implement slippage tolerance for this. Explicitly setting min_lp_share_price to 0.
    if slippage_tolerance is not None:
        raise NotImplementedError("Slippage tolerance for add liquidity not yet supported")

    agent_checksum_address = Web3.to_checksum_address(agent.address)
    min_lp_share_price = 0
    fn_args = (
        trade_amount.scaled_value,
        min_lp_share_price,
        min_apr.scaled_value,  # trade will reject if liquidity pushes fixed apr below this amount
        max_apr.scaled_value,  # trade will reject if liquidity pushes fixed apr above this amount
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
    if preview_before_trade:
        _ = smart_contract_preview_transaction(
            interface.hyperdrive_contract,
            agent_checksum_address,
            "addLiquidity",
            *fn_args,
            block_number=current_block,
            read_retry_count=interface.read_retry_count,
        )
    try:
        tx_receipt = await async_smart_contract_transact(
            interface.web3,
            interface.hyperdrive_contract,
            agent,
            "addLiquidity",
            *fn_args,
            nonce=nonce,
            read_retry_count=interface.read_retry_count,
            write_retry_count=interface.write_retry_count,
        )
        trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "addLiquidity")
    except Exception as exc:
        # We add the preview block as an arg to the exception
        exc.args += (f"Call previewed in block {current_block}",)
        raise exc
    return trade_result


async def _async_remove_liquidity(
    interface: HyperdriveReadWriteInterface,
    agent: LocalAccount,
    trade_amount: FixedPoint,
    nonce: Nonce | None = None,
    preview_before_trade: bool = False,
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
    if preview_before_trade is True:
        _ = smart_contract_preview_transaction(
            interface.hyperdrive_contract,
            agent_checksum_address,
            "removeLiquidity",
            *fn_args,
            block_number=current_block,
            read_retry_count=interface.read_retry_count,
        )
    try:
        tx_receipt = await async_smart_contract_transact(
            interface.web3,
            interface.hyperdrive_contract,
            agent,
            "removeLiquidity",
            *fn_args,
            nonce=nonce,
            read_retry_count=interface.read_retry_count,
            write_retry_count=interface.write_retry_count,
        )
        trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "removeLiquidity")
    except Exception as exc:
        # We add the preview block as an arg to the exception
        exc.args += (f"Call previewed in block {current_block}",)
        raise exc
    return trade_result


async def _async_redeem_withdraw_shares(
    interface: HyperdriveReadWriteInterface,
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
        read_retry_count=interface.read_retry_count,
    )
    # Here, a preview call of redeem withdrawal shares will still be successful without logs if
    # the amount of shares to redeem is larger than what's in the wallet. We want to catch this error
    # here with a useful error message, so we check that explicitly here

    # withdrawalSharesRedeemed is the second return value of the call
    # The abi doesn't contain the name of the returned variable
    if preview_result["value1"] == 0 and trade_amount > 0:
        raise ValueError("Preview call for redeem withdrawal shares returned 0 for non-zero input trade amount")

    try:
        tx_receipt = await async_smart_contract_transact(
            interface.web3,
            interface.hyperdrive_contract,
            agent,
            "redeemWithdrawalShares",
            *fn_args,
            nonce=nonce,
            read_retry_count=interface.read_retry_count,
            write_retry_count=interface.write_retry_count,
        )
        trade_result = parse_logs(tx_receipt, interface.hyperdrive_contract, "redeemWithdrawalShares")
    except Exception as exc:
        # We add the preview block as an arg to the exception
        exc.args += (f"Call previewed in block {current_block}",)
        raise exc
    return trade_result

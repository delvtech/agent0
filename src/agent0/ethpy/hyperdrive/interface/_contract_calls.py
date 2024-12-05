"""Hyperdrive interface functions that require a contract call."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, TypeVar

from eth_utils.currency import MAX_WEI
from fixedpointmath import FixedPoint
from hyperdrivetypes import (
    AddLiquidityEventFP,
    CloseLongEventFP,
    CloseShortEventFP,
    CreateCheckpointEventFP,
    OpenLongEventFP,
    OpenShortEventFP,
    RedeemWithdrawalSharesEventFP,
    RemoveLiquidityEventFP,
)
from hyperdrivetypes.types.ERC20Mintable import ERC20MintableContract
from hyperdrivetypes.types.IHyperdrive import IHyperdriveContract, Options
from hyperdrivetypes.types.MockERC4626 import MockERC4626Contract
from hyperdrivetypes.types.MockLido import MockLidoContract
from packaging.version import Version
from pypechain.core import PypechainCallException
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput, ContractLogicError
from web3.logs import DISCARD
from web3.types import TxParams

from agent0.ethpy.base import async_wait_for_transaction_receipt, get_account_balance
from agent0.ethpy.hyperdrive.assets import AssetIdPrefix, encode_asset_id

if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount
    from hyperdrivetypes import BaseEvent
    from web3.types import BlockIdentifier, Nonce

    from .read_interface import HyperdriveReadInterface
    from .read_write_interface import HyperdriveReadWriteInterface

# Number of arguments is influenced by the underlying solidity contract
# pylint: disable=too-many-arguments
# ruff: noqa: PLR0913
# pylint: disable=too-many-positional-arguments


def _get_minimum_transaction_amount_shares(
    interface: HyperdriveReadInterface,
    hyperdrive_contract: IHyperdriveContract,
    block_identifier: BlockIdentifier | None = None,
) -> FixedPoint:
    # Get the minimum transaction amount in units of base
    minimum_transaction_amount_base = interface.pool_config.minimum_transaction_amount
    # Convert to shares via rpc call, and cast as fixed point
    try:
        shares_value = hyperdrive_contract.functions.convertToShares(minimum_transaction_amount_base.scaled_value).call(
            block_identifier=block_identifier or "latest"
        )
        return FixedPoint(scaled_value=shares_value)
    except PypechainCallException:
        # Fallback to using vault share price
        # We div_up to overestimate the min txn amount
        shares_value = minimum_transaction_amount_base.div_up(interface.current_pool_state.pool_info.vault_share_price)
        return shares_value


def _get_total_supply_withdrawal_shares(
    hyperdrive_contract: IHyperdriveContract, block_identifier: BlockIdentifier | None = None
) -> FixedPoint:
    """See API for documentation."""
    asset_id = encode_asset_id(AssetIdPrefix.WITHDRAWAL_SHARE, 0)
    total_supply_withdrawal_shares = hyperdrive_contract.functions.balanceOf(
        asset_id, hyperdrive_contract.address
    ).call(block_identifier=block_identifier or "latest")
    return FixedPoint(scaled_value=int(total_supply_withdrawal_shares))


def _get_variable_rate(
    yield_contract: MockERC4626Contract | MockLidoContract, block_identifier: BlockIdentifier | None = None
) -> FixedPoint | None:
    """See API for documentation."""
    # Best attempt at calling `getRate` from the yield contract
    try:
        rate = yield_contract.functions.getRate().call(block_identifier=block_identifier or "latest")
        return FixedPoint(scaled_value=rate)
    except (BadFunctionCallOutput, ValueError):
        return None
    # Some contracts throw a logic error
    except ContractLogicError:
        return None


def _get_vault_shares(
    interface: HyperdriveReadInterface,
    hyperdrive_contract: IHyperdriveContract,
    block_identifier: BlockIdentifier | None = None,
) -> FixedPoint:
    """See API for documentation."""

    # `totalShares` is only available after hyperdrive version `1.0.17`
    if Version(interface.hyperdrive_version) >= Version("1.0.17"):
        vault_shares = interface.hyperdrive_contract.functions.totalShares().call(
            block_identifier=block_identifier or "latest"
        )
    else:
        if interface.hyperdrive_kind == interface.HyperdriveKind.STETH:
            # Type narrowing
            assert interface.vault_shares_token_contract is not None
            vault_shares = interface.vault_shares_token_contract.functions.sharesOf(hyperdrive_contract.address).call(
                block_identifier=block_identifier or "latest"
            )
        elif interface.hyperdrive_kind == interface.HyperdriveKind.MORPHO:
            # Type narrowing
            assert interface.morpho_contract is not None
            assert interface.morpho_market_id is not None

            # TODO pypechain requires bytes input (not HexBytes) for the position function call.
            # Fix to allow for bytes input to be interchangeable.
            morpho_market_id = bytes(interface.morpho_market_id)

            # Get token balances
            vault_shares = (
                interface.morpho_contract.functions.position(morpho_market_id, hyperdrive_contract.address)
                .call(block_identifier=block_identifier or "latest")
                .supplyShares
            )
        else:
            # Type narrowing
            assert interface.vault_shares_token_contract is not None
            vault_shares = interface.vault_shares_token_contract.functions.balanceOf(hyperdrive_contract.address).call(
                block_identifier=block_identifier or "latest"
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
    hyperdrive_contract: IHyperdriveContract,
    block_identifier: BlockIdentifier | None,
) -> FixedPoint:
    """See API for documentation."""
    base_balance = base_contract.functions.balanceOf(hyperdrive_contract.address).call(
        block_identifier=block_identifier or "latest"
    )
    return FixedPoint(scaled_value=base_balance)


def _get_hyperdrive_eth_balance(
    web3: Web3,
    hyperdrive_address: str,
) -> FixedPoint:
    """See API for documentation."""
    hyperdrive_checksum_address = Web3.to_checksum_address(hyperdrive_address)
    agent_eth_balance = get_account_balance(web3, hyperdrive_checksum_address)
    return FixedPoint(scaled_value=agent_eth_balance)


def _get_gov_fees_accrued(
    hyperdrive_contract: IHyperdriveContract,
    block_identifier: BlockIdentifier | None,
) -> FixedPoint:
    """See API for documentation."""
    if block_identifier is None:
        block_identifier = "latest"
    gov_fees_accrued = hyperdrive_contract.functions.getUncollectedGovernanceFees().call(
        block_identifier=block_identifier
    )
    return FixedPoint(scaled_value=gov_fees_accrued)


def _get_long_total_supply(
    hyperdrive_contract: IHyperdriveContract,
    maturity_time: int,
    block_identifier: BlockIdentifier | None,
) -> FixedPoint:
    """See API for documentation."""
    if block_identifier is None:
        block_identifier = "latest"
    asset_id = encode_asset_id(AssetIdPrefix.LONG, maturity_time)
    total_supply = hyperdrive_contract.functions.totalSupply(asset_id).call(block_identifier=block_identifier)
    return FixedPoint(scaled_value=total_supply)


def _get_short_total_supply(
    hyperdrive_contract: IHyperdriveContract,
    maturity_time: int,
    block_identifier: BlockIdentifier | None,
) -> FixedPoint:
    """See API for documentation."""
    if block_identifier is None:
        block_identifier = "latest"
    asset_id = encode_asset_id(AssetIdPrefix.SHORT, maturity_time)
    total_supply = hyperdrive_contract.functions.totalSupply(asset_id).call(block_identifier=block_identifier)
    return FixedPoint(scaled_value=total_supply)


def _create_checkpoint(
    interface: HyperdriveReadWriteInterface,
    sender: LocalAccount,
    checkpoint_time: int | None = None,
    preview: bool = False,
    gas_limit: int | None = None,
    nonce_func: Callable[[], Nonce] | None = None,
) -> CreateCheckpointEventFP:
    """See API for documentation."""

    if checkpoint_time is None:
        block_timestamp = interface.get_block_timestamp(interface.get_current_block())
        checkpoint_time = interface.calc_checkpoint_id(interface.pool_config.checkpoint_duration, block_timestamp)

    # 0 is the max iterations for distribute excess idle, where it will default to
    # the default max iterations
    fn_args = (checkpoint_time, 0)

    contract_fn = interface.hyperdrive_contract.functions.checkpoint(*fn_args)
    tx_params = TxParams({"from": sender.address})
    if preview:
        _ = contract_fn.call(
            tx_params,
            block_identifier="pending",
        )

    if nonce_func is not None:
        tx_params["nonce"] = nonce_func()
    if gas_limit is not None:
        tx_params["gas"] = gas_limit

    tx_receipt = contract_fn.sign_transact_and_wait(
        sender,
        tx_params,
        timeout=interface.txn_receipt_timeout,
        validate_transaction=True,
    )

    # Process receipt attempts to process all events in logs, even if it's not of the
    # defined event. Since we know hyperdrive emits multiple events per transaction,
    # we get the one we want and discard the rest
    out_events = list(
        interface.hyperdrive_contract.events.CreateCheckpoint.process_receipt_typed(tx_receipt, errors=DISCARD)
    )
    if len(out_events) != 1:
        raise ValueError(f"Unexpected number of events: {out_events}")
    return CreateCheckpointEventFP.from_pypechain(out_events[0])


def _set_variable_rate(
    interface: HyperdriveReadWriteInterface,
    sender: LocalAccount,
    new_rate: FixedPoint,
) -> None:
    """See API for documentation."""
    # Type narrowing
    assert interface.vault_shares_token_contract is not None
    contract_fn = interface.vault_shares_token_contract.functions.setRate(new_rate.scaled_value)
    _ = contract_fn.sign_transact_and_wait(sender, timeout=interface.txn_receipt_timeout, validate_transaction=True)


# Helper function to check if we need to convert amounts in the case of a steth (i.e., rebasing) deployment
# TODO consider not converting amount here, and keeping output events in units of steth "shares".
# The suggested change above would keep output events mirroring that of what's returned from hyperdrive.
# We just need to make the conversion in the database to keep track of the actual amount.
# TODO likely need to generalize this to be all rebasing tokens, not just steth.

T = TypeVar("T", bound="BaseEvent")


def _convert_event_base_amounts_for_rebasing_tokens(
    in_event: T,
) -> T:
    # Vault share price should be in every hyperdrive event
    assert hasattr(in_event.args, "vault_share_price")
    if hasattr(in_event.args, "amount"):
        # We make the checks already, typing doesn't narrow here
        in_event.args.amount *= in_event.args.vault_share_price  # type: ignore

    if hasattr(in_event.args, "base_proceeds"):
        # We make the checks already, typing doesn't narrow here
        in_event.args.base_proceeds *= in_event.args.vault_share_price  # type: ignore

    if hasattr(in_event.args, "base_payment"):
        # We make the checks already, typing doesn't narrow here
        in_event.args.base_payment *= in_event.args.vault_share_price  # type: ignore

    # Although this is changed in-place, we return regardless
    return in_event


# pylint: disable=too-many-locals
async def _async_open_long(
    interface: HyperdriveReadWriteInterface,
    sender: LocalAccount,
    trade_amount: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
    gas_limit: int | None = None,
    txn_options_base_fee_multiple: float | None = None,
    txn_options_priority_fee_multiple: float | None = None,
    nonce_func: Callable[[], Nonce] | None = None,
    preview_before_trade: bool = False,
) -> OpenLongEventFP:
    """See API for documentation."""

    # TODO readd in fee multiples
    if txn_options_base_fee_multiple is not None:
        raise NotImplementedError("Base fee multiple not yet implemented")
    if txn_options_priority_fee_multiple is not None:
        raise NotImplementedError("Priority fee multiple not yet implemented")

    # min_vault_share_price: int
    #   Minium share price at which to open the long.
    #   This allows traders to protect themselves from opening a long in
    #   a checkpoint where negative interest has accrued.
    min_vault_share_price = 0  # TODO: give the user access to this parameter
    min_output = 0  # TODO: give the user access to this parameter

    # We use the yield as the base token in steth pools
    if interface.base_is_yield:
        as_base_option = False
    else:
        as_base_option = True

    # Convert the trade amount from steth to lido shares
    # before passing into hyperdrive
    if interface.hyperdrive_kind == interface.HyperdriveKind.STETH:
        # Type narrowing
        assert interface.vault_shares_token_contract is not None
        # Convert input steth into lido shares
        trade_amount = FixedPoint(
            scaled_value=interface.vault_shares_token_contract.functions.getSharesByPooledEth(
                trade_amount.scaled_value
            ).call()
        )

    fn_args = (
        trade_amount.scaled_value,
        min_output,
        min_vault_share_price,
        Options(
            sender.address,  # destination
            as_base_option,  # asBase
            interface.txn_signature,  # extraData
        ),
    )

    contract_fn = interface.hyperdrive_contract.functions.openLong(*fn_args)
    tx_params = TxParams({"from": sender.address})
    preview_result = None
    if preview_before_trade or slippage_tolerance is not None:
        preview_result = contract_fn.call(
            tx_params,
            block_identifier="pending",
        )
    if slippage_tolerance is not None:
        assert preview_result is not None
        min_output = (
            FixedPoint(scaled_value=preview_result.bondProceeds) * (FixedPoint(1) - slippage_tolerance)
        ).scaled_value
        fn_args = (
            trade_amount.scaled_value,
            min_output,
            min_vault_share_price,
            Options(  # IHyperdrive.Options
                sender.address,  # destination
                as_base_option,  # asBase
                interface.txn_signature,  # extraData
            ),
        )
        contract_fn = interface.hyperdrive_contract.functions.openLong(*fn_args)

    if gas_limit is not None:
        tx_params["gas"] = gas_limit
    if nonce_func is not None:
        tx_params["nonce"] = nonce_func()

    tx_hash = contract_fn.sign_and_transact(
        sender,
        tx_params,
    )
    # Use async await to avoid blocking the event loop
    tx_receipt = await async_wait_for_transaction_receipt(
        contract_fn, tx_hash, timeout=interface.txn_receipt_timeout, validate_transaction=True
    )

    # Process receipt attempts to process all events in logs, even if it's not of the
    # defined event. Since we know hyperdrive emits multiple events per transaction,
    # we get the one we want and discard the rest
    out_events = list(interface.hyperdrive_contract.events.OpenLong.process_receipt_typed(tx_receipt, errors=DISCARD))
    if len(out_events) != 1:
        raise ValueError(f"Unexpected number of events: {out_events}")
    out_event = OpenLongEventFP.from_pypechain(out_events[0])

    # If hyperdrive is steth, convert the amount from lido shares to steth
    if interface.hyperdrive_kind == interface.HyperdriveKind.STETH:
        out_event = _convert_event_base_amounts_for_rebasing_tokens(out_event)

    return out_event


# pylint: disable=too-many-arguments
async def _async_close_long(
    interface: HyperdriveReadWriteInterface,
    sender: LocalAccount,
    trade_amount: FixedPoint,
    maturity_time: int,
    slippage_tolerance: FixedPoint | None = None,
    gas_limit: int | None = None,
    txn_options_base_fee_multiple: float | None = None,
    txn_options_priority_fee_multiple: float | None = None,
    nonce_func: Callable[[], Nonce] | None = None,
    preview_before_trade: bool = False,
) -> CloseLongEventFP:
    """See API for documentation."""
    # TODO readd in fee multiples
    if txn_options_base_fee_multiple is not None:
        raise NotImplementedError("Base fee multiple not yet implemented")
    if txn_options_priority_fee_multiple is not None:
        raise NotImplementedError("Priority fee multiple not yet implemented")
    min_output = 0

    # We use the yield as the base token in steth pools
    if interface.base_is_yield:
        as_base_option = False
    else:
        as_base_option = True

    fn_args = (
        maturity_time,
        trade_amount.scaled_value,
        min_output,
        Options(  # IHyperdrive.Options
            sender.address,  # destination
            as_base_option,  # asBase
            interface.txn_signature,  # extraData
        ),
    )

    contract_fn = interface.hyperdrive_contract.functions.closeLong(*fn_args)
    tx_params = TxParams({"from": sender.address})

    # To catch any solidity errors, we preview transactions on the current block
    # before calling smart contract transact
    preview_result = None
    if preview_before_trade or slippage_tolerance is not None:
        preview_result = contract_fn.call(
            tx_params,
            block_identifier="pending",
        )
    if slippage_tolerance is not None:
        assert preview_result is not None
        min_output = (FixedPoint(scaled_value=preview_result) * (FixedPoint(1) - slippage_tolerance)).scaled_value
        fn_args = (
            maturity_time,
            trade_amount.scaled_value,
            min_output,
            Options(  # IHyperdrive.Options
                sender.address,  # destination
                as_base_option,  # asBase
                interface.txn_signature,  # extraData
            ),
        )
        contract_fn = interface.hyperdrive_contract.functions.closeLong(*fn_args)
    if gas_limit is not None:
        tx_params["gas"] = gas_limit
    if nonce_func is not None:
        tx_params["nonce"] = nonce_func()
    tx_hash = contract_fn.sign_and_transact(
        sender,
        tx_params,
    )
    # Use async await to avoid blocking the event loop
    tx_receipt = await async_wait_for_transaction_receipt(
        contract_fn, tx_hash, timeout=interface.txn_receipt_timeout, validate_transaction=True
    )

    # Process receipt attempts to process all events in logs, even if it's not of the
    # defined event. Since we know hyperdrive emits multiple events per transaction,
    # we get the one we want and discard the rest
    out_events = list(interface.hyperdrive_contract.events.CloseLong.process_receipt_typed(tx_receipt, errors=DISCARD))
    if len(out_events) != 1:
        raise ValueError(f"Unexpected number of events: {out_events}")
    out_event = CloseLongEventFP.from_pypechain(out_events[0])
    # If hyperdrive is steth, convert the amount from lido shares to steth
    if interface.hyperdrive_kind == interface.HyperdriveKind.STETH:
        out_event = _convert_event_base_amounts_for_rebasing_tokens(out_event)

    return out_event


# pylint: disable=too-many-locals
async def _async_open_short(
    interface: HyperdriveReadWriteInterface,
    sender: LocalAccount,
    trade_amount: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
    gas_limit: int | None = None,
    txn_options_base_fee_multiple: float | None = None,
    txn_options_priority_fee_multiple: float | None = None,
    nonce_func: Callable[[], Nonce] | None = None,
    preview_before_trade: bool = False,
) -> OpenShortEventFP:
    """See API for documentation."""
    # TODO readd in fee multiples
    if txn_options_base_fee_multiple is not None:
        raise NotImplementedError("Base fee multiple not yet implemented")
    if txn_options_priority_fee_multiple is not None:
        raise NotImplementedError("Priority fee multiple not yet implemented")

    max_deposit = int(MAX_WEI)
    # We use the yield as the base token in steth pools
    if interface.base_is_yield:
        as_base_option = False
    else:
        as_base_option = True

    # min_vault_share_price: int
    #   Minium share price at which to open the short.
    #   This allows traders to protect themselves from opening a long in
    #   a checkpoint where negative interest has accrued.
    min_vault_share_price = 0  # TODO: give the user access to this parameter
    fn_args = (
        trade_amount.scaled_value,
        max_deposit,
        min_vault_share_price,
        Options(  # IHyperdrive.Options
            sender.address,  # destination
            as_base_option,  # asBase
            interface.txn_signature,  # extraData
        ),
    )

    contract_fn = interface.hyperdrive_contract.functions.openShort(*fn_args)
    tx_params = TxParams({"from": sender.address})
    # To catch any solidity errors, we preview transactions on the current block
    # before calling smart contract transact
    preview_result = None
    if preview_before_trade or slippage_tolerance is not None:
        preview_result = contract_fn.call(
            tx_params,
            block_identifier="pending",
        )
    if slippage_tolerance is not None:
        assert preview_result is not None
        max_deposit = (
            FixedPoint(scaled_value=preview_result.deposit) * (FixedPoint(1) + slippage_tolerance)
        ).scaled_value
        fn_args = (
            trade_amount.scaled_value,
            max_deposit,
            min_vault_share_price,
            Options(  # IHyperdrive.Options
                sender.address,  # destination
                as_base_option,  # asBase
                interface.txn_signature,  # extraData
            ),
        )
        contract_fn = interface.hyperdrive_contract.functions.openShort(*fn_args)
    if gas_limit is not None:
        tx_params["gas"] = gas_limit
    if nonce_func is not None:
        tx_params["nonce"] = nonce_func()
    tx_hash = contract_fn.sign_and_transact(
        sender,
        tx_params,
    )
    # Use async await to avoid blocking the event loop
    tx_receipt = await async_wait_for_transaction_receipt(
        contract_fn, tx_hash, timeout=interface.txn_receipt_timeout, validate_transaction=True
    )

    # Process receipt attempts to process all events in logs, even if it's not of the
    # defined event. Since we know hyperdrive emits multiple events per transaction,
    # we get the one we want and discard the rest
    out_events = list(interface.hyperdrive_contract.events.OpenShort.process_receipt_typed(tx_receipt, errors=DISCARD))
    if len(out_events) != 1:
        raise ValueError(f"Unexpected number of events: {out_events}")
    out_event = OpenShortEventFP.from_pypechain(out_events[0])
    # If hyperdrive is steth, convert the amount from lido shares to steth
    if interface.hyperdrive_kind == interface.HyperdriveKind.STETH:
        out_event = _convert_event_base_amounts_for_rebasing_tokens(out_event)

    return out_event


async def _async_close_short(
    interface: HyperdriveReadWriteInterface,
    sender: LocalAccount,
    trade_amount: FixedPoint,
    maturity_time: int,
    slippage_tolerance: FixedPoint | None = None,
    gas_limit: int | None = None,
    txn_options_base_fee_multiple: float | None = None,
    txn_options_priority_fee_multiple: float | None = None,
    nonce_func: Callable[[], Nonce] | None = None,
    preview_before_trade: bool = False,
) -> CloseShortEventFP:
    """See API for documentation."""

    # TODO readd in fee multiples
    if txn_options_base_fee_multiple is not None:
        raise NotImplementedError("Base fee multiple not yet implemented")
    if txn_options_priority_fee_multiple is not None:
        raise NotImplementedError("Priority fee multiple not yet implemented")

    min_output = 0

    # We use the yield as the base token in steth pools
    if interface.base_is_yield:
        as_base_option = False
    else:
        as_base_option = True

    fn_args = (
        maturity_time,
        trade_amount.scaled_value,
        min_output,
        Options(  # IHyperdrive.Options
            sender.address,  # destination
            as_base_option,  # asBase
            interface.txn_signature,  # extraData
        ),
    )

    contract_fn = interface.hyperdrive_contract.functions.closeShort(*fn_args)
    tx_params = TxParams({"from": sender.address})
    # To catch any solidity errors, we preview transactions on the current block
    # before calling smart contract transact
    preview_result = None
    if preview_before_trade or slippage_tolerance is not None:
        preview_result = contract_fn.call(
            tx_params,
            block_identifier="pending",
        )
    if slippage_tolerance is not None:
        min_output = (FixedPoint(scaled_value=preview_result) * (FixedPoint(1) - slippage_tolerance)).scaled_value
        fn_args = (
            maturity_time,
            trade_amount.scaled_value,
            min_output,
            Options(  # IHyperdrive.Options
                sender.address,  # destination
                as_base_option,  # asBase
                interface.txn_signature,  # extraData
            ),
        )
        contract_fn = interface.hyperdrive_contract.functions.closeShort(*fn_args)
    if gas_limit is not None:
        tx_params["gas"] = gas_limit
    if nonce_func is not None:
        tx_params["nonce"] = nonce_func()
    tx_hash = contract_fn.sign_and_transact(
        sender,
        tx_params,
    )
    # Use async await to avoid blocking the event loop
    tx_receipt = await async_wait_for_transaction_receipt(
        contract_fn, tx_hash, timeout=interface.txn_receipt_timeout, validate_transaction=True
    )

    # Process receipt attempts to process all events in logs, even if it's not of the
    # defined event. Since we know hyperdrive emits multiple events per transaction,
    # we get the one we want and discard the rest
    out_events = list(interface.hyperdrive_contract.events.CloseShort.process_receipt_typed(tx_receipt, errors=DISCARD))
    if len(out_events) != 1:
        raise ValueError(f"Unexpected number of events: {out_events}")
    out_event = CloseShortEventFP.from_pypechain(out_events[0])
    # If hyperdrive is steth, convert the amount from lido shares to steth
    if interface.hyperdrive_kind == interface.HyperdriveKind.STETH:
        out_event = _convert_event_base_amounts_for_rebasing_tokens(out_event)

    return out_event


async def _async_add_liquidity(
    interface: HyperdriveReadWriteInterface,
    sender: LocalAccount,
    trade_amount: FixedPoint,
    min_apr: FixedPoint,
    max_apr: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
    gas_limit: int | None = None,
    txn_options_base_fee_multiple: float | None = None,
    txn_options_priority_fee_multiple: float | None = None,
    nonce_func: Callable[[], Nonce] | None = None,
    preview_before_trade: bool = False,
) -> AddLiquidityEventFP:
    """See API for documentation."""

    # TODO readd in fee multiples
    if txn_options_base_fee_multiple is not None:
        raise NotImplementedError("Base fee multiple not yet implemented")
    if txn_options_priority_fee_multiple is not None:
        raise NotImplementedError("Priority fee multiple not yet implemented")

    # TODO implement slippage tolerance for this. Explicitly setting min_lp_share_price to 0.
    if slippage_tolerance is not None:
        raise NotImplementedError("Slippage tolerance for add liquidity not yet supported")

    min_lp_share_price = 0

    # We use the yield as the base token in steth pools
    if interface.base_is_yield:
        as_base_option = False
    else:
        as_base_option = True

    # Convert the trade amount from steth to lido shares
    # before passing into hyperdrive
    if interface.hyperdrive_kind == interface.HyperdriveKind.STETH:
        # type narrowing
        assert interface.vault_shares_token_contract is not None
        # Convert input steth into lido shares
        trade_amount = FixedPoint(
            scaled_value=interface.vault_shares_token_contract.functions.getSharesByPooledEth(
                trade_amount.scaled_value
            ).call()
        )

    fn_args = (
        trade_amount.scaled_value,
        min_lp_share_price,
        min_apr.scaled_value,  # trade will reject if liquidity pushes fixed apr below this amount
        max_apr.scaled_value,  # trade will reject if liquidity pushes fixed apr above this amount
        Options(  # IHyperdrive.Options
            sender.address,
            as_base_option,  # asBase
            interface.txn_signature,  # extraData
        ),
    )

    contract_fn = interface.hyperdrive_contract.functions.addLiquidity(*fn_args)
    tx_params = TxParams({"from": sender.address})
    # To catch any solidity errors, we preview transactions on the current block
    # before calling smart contract transact
    if preview_before_trade:
        _ = contract_fn.call(
            tx_params,
            block_identifier="pending",
        )
    if gas_limit is not None:
        tx_params["gas"] = gas_limit
    if nonce_func is not None:
        tx_params["nonce"] = nonce_func()
    tx_hash = contract_fn.sign_and_transact(
        sender,
        tx_params,
    )
    # Use async await to avoid blocking the event loop
    tx_receipt = await async_wait_for_transaction_receipt(
        contract_fn, tx_hash, timeout=interface.txn_receipt_timeout, validate_transaction=True
    )

    # Process receipt attempts to process all events in logs, even if it's not of the
    # defined event. Since we know hyperdrive emits multiple events per transaction,
    # we get the one we want and discard the rest
    out_events = list(
        interface.hyperdrive_contract.events.AddLiquidity.process_receipt_typed(tx_receipt, errors=DISCARD)
    )
    if len(out_events) != 1:
        raise ValueError(f"Unexpected number of events: {out_events}")
    out_event = AddLiquidityEventFP.from_pypechain(out_events[0])
    # If hyperdrive is steth, convert the amount from lido shares to steth
    if interface.hyperdrive_kind == interface.HyperdriveKind.STETH:
        out_event = _convert_event_base_amounts_for_rebasing_tokens(out_event)

    return out_event


async def _async_remove_liquidity(
    interface: HyperdriveReadWriteInterface,
    sender: LocalAccount,
    trade_amount: FixedPoint,
    gas_limit: int | None = None,
    txn_options_base_fee_multiple: float | None = None,
    txn_options_priority_fee_multiple: float | None = None,
    nonce_func: Callable[[], Nonce] | None = None,
    preview_before_trade: bool = False,
) -> RemoveLiquidityEventFP:
    """See API for documentation."""
    # TODO readd in fee multiples
    if txn_options_base_fee_multiple is not None:
        raise NotImplementedError("Base fee multiple not yet implemented")
    if txn_options_priority_fee_multiple is not None:
        raise NotImplementedError("Priority fee multiple not yet implemented")

    min_output = 0

    # We use the yield as the base token in steth pools
    if interface.base_is_yield:
        as_base_option = False
    else:
        as_base_option = True

    fn_args = (
        trade_amount.scaled_value,
        min_output,
        Options(  # IHyperdrive.Options
            sender.address,
            as_base_option,  # asBase
            interface.txn_signature,  # extraData
        ),
    )
    contract_fn = interface.hyperdrive_contract.functions.removeLiquidity(*fn_args)
    tx_params = TxParams({"from": sender.address})
    # To catch any solidity errors, we preview transactions on the current block
    # before calling smart contract transact
    if preview_before_trade is True:
        _ = contract_fn.call(
            tx_params,
            block_identifier="pending",
        )

    if gas_limit is not None:
        tx_params["gas"] = gas_limit
    if nonce_func is not None:
        tx_params["nonce"] = nonce_func()
    tx_hash = contract_fn.sign_and_transact(
        sender,
        tx_params,
    )
    # Use async await to avoid blocking the event loop
    tx_receipt = await async_wait_for_transaction_receipt(
        contract_fn, tx_hash, timeout=interface.txn_receipt_timeout, validate_transaction=True
    )

    # Process receipt attempts to process all events in logs, even if it's not of the
    # defined event. Since we know hyperdrive emits multiple events per transaction,
    # we get the one we want and discard the rest
    out_events = list(
        interface.hyperdrive_contract.events.RemoveLiquidity.process_receipt_typed(tx_receipt, errors=DISCARD)
    )
    if len(out_events) != 1:
        raise ValueError(f"Unexpected number of events: {out_events}")
    out_event = RemoveLiquidityEventFP.from_pypechain(out_events[0])
    # If hyperdrive is steth, convert the amount from lido shares to steth
    if interface.hyperdrive_kind == interface.HyperdriveKind.STETH:
        out_event = _convert_event_base_amounts_for_rebasing_tokens(out_event)

    return out_event


async def _async_redeem_withdraw_shares(
    interface: HyperdriveReadWriteInterface,
    sender: LocalAccount,
    trade_amount: FixedPoint,
    gas_limit: int | None = None,
    txn_options_base_fee_multiple: float | None = None,
    txn_options_priority_fee_multiple: float | None = None,
    nonce_func: Callable[[], Nonce] | None = None,
    preview_before_trade: bool = False,
) -> RedeemWithdrawalSharesEventFP:
    """See API for documentation."""
    # TODO readd in fee multiples
    if txn_options_base_fee_multiple is not None:
        raise NotImplementedError("Base fee multiple not yet implemented")
    if txn_options_priority_fee_multiple is not None:
        raise NotImplementedError("Priority fee multiple not yet implemented")

    # for now, assume an underlying vault share price of at least 1, should be higher by a bit
    min_output = FixedPoint(scaled_value=1)

    # We use the yield as the base token in steth pools
    if interface.base_is_yield:
        as_base_option = False
    else:
        as_base_option = True

    fn_args = (
        trade_amount.scaled_value,
        min_output.scaled_value,
        Options(  # IHyperdrive.Options
            sender.address,
            as_base_option,  # asBase
            interface.txn_signature,  # extraData
        ),
    )
    contract_fn = interface.hyperdrive_contract.functions.redeemWithdrawalShares(*fn_args)
    tx_params = TxParams({"from": sender.address})
    # To catch any solidity errors, we preview transactions on the current block
    # before calling smart contract transact
    if preview_before_trade is True:
        preview_result = contract_fn.call(
            tx_params,
            block_identifier="pending",
        )
        # Here, a preview call of redeem withdrawal shares will still be successful without logs if
        # the amount of shares to redeem is larger than what's in the wallet. We want to catch this error
        # here with a useful error message, so we check that explicitly here
        if preview_result.withdrawalSharesRedeemed == 0 and trade_amount > 0:
            raise ValueError("Preview call for redeem withdrawal shares returned 0 for non-zero input trade amount")

    if gas_limit is not None:
        tx_params["gas"] = gas_limit
    if nonce_func is not None:
        tx_params["nonce"] = nonce_func()
    tx_hash = contract_fn.sign_and_transact(
        sender,
        tx_params,
    )
    # Use async await to avoid blocking the event loop
    tx_receipt = await async_wait_for_transaction_receipt(
        contract_fn, tx_hash, timeout=interface.txn_receipt_timeout, validate_transaction=True
    )

    # Process receipt attempts to process all events in logs, even if it's not of the
    # defined event. Since we know hyperdrive emits multiple events per transaction,
    # we get the one we want and discard the rest
    out_events = list(
        interface.hyperdrive_contract.events.RedeemWithdrawalShares.process_receipt_typed(tx_receipt, errors=DISCARD)
    )
    if len(out_events) != 1:
        raise ValueError(f"Unexpected number of events: {out_events}")
    out_event = RedeemWithdrawalSharesEventFP.from_pypechain(out_events[0])
    # If hyperdrive is steth, convert the amount from lido shares to steth
    if interface.hyperdrive_kind == interface.HyperdriveKind.STETH:
        out_event = _convert_event_base_amounts_for_rebasing_tokens(out_event)

    return out_event

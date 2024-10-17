"""High-level interface for writing to Hyperdrive smart contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ._contract_calls import (
    _async_add_liquidity,
    _async_close_long,
    _async_close_short,
    _async_open_long,
    _async_open_short,
    _async_redeem_withdraw_shares,
    _async_remove_liquidity,
    _create_checkpoint,
    _set_variable_rate,
)
from .read_interface import HyperdriveReadInterface

if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount
    from eth_typing import ChecksumAddress
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
    from web3 import Web3
    from web3.types import Nonce

# We have no control over the number of arguments since it is specified by the smart contracts
# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
# ruff: noqa: PLR0913
# We only worry about protected access for anyone outside of this folder.
# pylint: disable=protected-access


class HyperdriveReadWriteInterface(HyperdriveReadInterface):
    """Read-write end-point API for interfacing with a deployed Hyperdrive pool."""

    def __init__(
        self,
        hyperdrive_address: ChecksumAddress,
        rpc_uri: str | None = None,
        web3: Web3 | None = None,
        txn_receipt_timeout: float | None = None,
        txn_signature: bytes | None = None,
    ) -> None:
        """Initialize the primary endpoint for users to execute transactions on Hyperdrive smart contracts.

        Arguments
        ---------
        hyperdrive_address: ChecksumAddress
            This is a contract address for a deployed hyperdrive.
        rpc_uri: str, optional
            The URI to initialize the web3 provider. Not used if web3 is provided.
        web3: Web3, optional
            web3 provider object, optional
            If not given, a web3 object is constructed using the `rpc_uri` as the http provider.
        txn_receipt_timeout: float | None, optional
            The timeout for waiting for a transaction receipt in seconds. Defaults to 120.
        txn_signature: bytes | None, optional
            The signature for transactions. Defaults to `0xa0`.
        """
        super().__init__(
            hyperdrive_address=hyperdrive_address,
            rpc_uri=rpc_uri,
            web3=web3,
            txn_receipt_timeout=txn_receipt_timeout,
            txn_signature=txn_signature,
        )
        self._read_interface: HyperdriveReadInterface | None = None

    def get_read_interface(self) -> HyperdriveReadInterface:
        """Return the current instance as an instance of the parent (HyperdriveReadInterface) class.

        Returns
        -------
        HyperdriveReadInterface
            This instantiated object, but as a ReadInterface.
        """

        # We cache the read interface output when this function gets called multiple times
        if self._read_interface is None:
            self._read_interface = HyperdriveReadInterface(
                hyperdrive_address=self.hyperdrive_address,
                web3=self.web3,
                txn_receipt_timeout=self.txn_receipt_timeout,
            )

        return self._read_interface

    def create_checkpoint(
        self,
        sender: LocalAccount,
        checkpoint_time: int | None = None,
        preview: bool = False,
        gas_limit: int | None = None,
        nonce_func: Callable[[], Nonce] | None = None,
    ) -> CreateCheckpointEventFP:
        """Create a Hyperdrive checkpoint.

        Arguments
        ---------
        sender: LocalAccount
            The sender account that is executing and signing the trade transaction.
        checkpoint_time: int, optional
            The checkpoint time to use. Defaults to the corresponding checkpoint for the provided block_number
        preview: bool, optional
            Whether to preview the transaction first for error catching.
        gas_limit: int | None, optional
            The maximum amount of gas used by the transaction.
        nonce_func: Callable[[], Nonce] | None
            A callable function to use to get a nonce. This function is useful for e.g.,
            passing in a safe nonce getter tied to an agent.

        Returns
        -------
        CreateCheckpoint
            A dataclass containing the output event of the contract call.
        """
        return _create_checkpoint(
            interface=self,
            sender=sender,
            checkpoint_time=checkpoint_time,
            preview=preview,
            gas_limit=gas_limit,
            nonce_func=nonce_func,
        )

    def set_variable_rate(self, sender: LocalAccount, new_rate: FixedPoint) -> None:
        """Set the variable rate for the yield source.

        .. note:: This function assumes there's an underlying `setRate` function in the contract.
        This call will fail if the deployed yield contract doesn't have a `setRate` function.

        Arguments
        ---------
        sender: LocalAccount
            The sender account that is executing and signing the trade transaction.
        new_rate: FixedPoint
            The new variable rate for the yield source.
        """
        _set_variable_rate(self, sender, new_rate)

    async def async_open_long(
        self,
        sender: LocalAccount,
        trade_amount: FixedPoint,
        slippage_tolerance: FixedPoint | None = None,
        gas_limit: int | None = None,
        txn_options_base_fee_multiple: float | None = None,
        txn_options_priority_fee_multiple: float | None = None,
        nonce_func: Callable[[], Nonce] | None = None,
        preview_before_trade: bool = False,
    ) -> OpenLongEventFP:
        """Contract call to open a long position.

        Arguments
        ---------
        sender: LocalAccount
            The account that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        slippage_tolerance: FixedPoint, optional
            Amount of slippage allowed from the trade.
            If given, then the trade will not execute unless the slippage is below this value.
            If not given, then execute the trade regardless of the slippage.
        gas_limit: int | None, optional
            The maximum amount of gas used by the transaction.
            Defaults to `eth_estimateGas` RPC output.
        txn_options_base_fee_multiple: float | None, optional
            The multiple applied to the base fee for the transaction. Defaults to 1.
        txn_options_priority_fee_multiple: float | None, optional
            The multiple applied to the priority fee for the transaction. Defaults to 1.
        nonce_func: Callable[[], Nonce] | None
            A callable function to use to get a nonce. This function is useful for e.g.,
            passing in a safe nonce getter tied to an agent.
            Defaults to setting it to the result of `get_transaction_count`.
        preview_before_trade: bool, optional
            Whether to preview the trade before executing. Defaults to False.

        Returns
        -------
        OpenLong
            A dataclass containing the output event of the contract call.
        """
        return await _async_open_long(
            interface=self,
            sender=sender,
            trade_amount=trade_amount,
            slippage_tolerance=slippage_tolerance,
            gas_limit=gas_limit,
            txn_options_base_fee_multiple=txn_options_base_fee_multiple,
            txn_options_priority_fee_multiple=txn_options_priority_fee_multiple,
            nonce_func=nonce_func,
            preview_before_trade=preview_before_trade,
        )

    # We do not control the number of arguments; this is set by hyperdrive-rs
    # pylint: disable=too-many-arguments
    async def async_close_long(
        self,
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
        """Contract call to close a long position.

        Arguments
        ---------
        sender: LocalAccount
            The account that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The amount of bonds you wish to close.
        maturity_time: int
            The token maturity time in seconds.
        slippage_tolerance: FixedPoint, optional
            Amount of slippage allowed from the trade.
            If given, then the trade will not execute unless the slippage is below this value.
            If not given, then execute the trade regardless of the slippage.
        gas_limit: int | None, optional
            The maximum amount of gas used by the transaction.
            Defaults to `eth_estimateGas` RPC output.
        txn_options_base_fee_multiple: float | None, optional
            The multiple applied to the base fee for the transaction. Defaults to 1.
        txn_options_priority_fee_multiple: float | None, optional
            The multiple applied to the priority fee for the transaction. Defaults to 1.
        nonce_func: Callable[[], Nonce] | None
            A callable function to use to get a nonce. This function is useful for e.g.,
            passing in a safe nonce getter tied to an agent.
            Defaults to setting it to the result of `get_transaction_count`.
        preview_before_trade: bool, optional
            Whether to preview the trade before executing. Defaults to False.

        Returns
        -------
        CloseLong
            A dataclass containing the output event of the contract call.
        """
        return await _async_close_long(
            interface=self,
            sender=sender,
            trade_amount=trade_amount,
            maturity_time=maturity_time,
            slippage_tolerance=slippage_tolerance,
            gas_limit=gas_limit,
            txn_options_base_fee_multiple=txn_options_base_fee_multiple,
            txn_options_priority_fee_multiple=txn_options_priority_fee_multiple,
            nonce_func=nonce_func,
            preview_before_trade=preview_before_trade,
        )

    async def async_open_short(
        self,
        sender: LocalAccount,
        trade_amount: FixedPoint,
        slippage_tolerance: FixedPoint | None = None,
        gas_limit: int | None = None,
        txn_options_base_fee_multiple: float | None = None,
        txn_options_priority_fee_multiple: float | None = None,
        nonce_func: Callable[[], Nonce] | None = None,
        preview_before_trade: bool = False,
    ) -> OpenShortEventFP:
        """Contract call to open a short position.

        Arguments
        ---------
        sender: LocalAccount
            The account that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        slippage_tolerance: FixedPoint, optional
            Amount of slippage allowed from the trade.
            If given, then the trade will not execute unless the slippage is below this value.
            If not given, then execute the trade regardless of the slippage.
        gas_limit: int | None, optional
            The maximum amount of gas used by the transaction.
            Defaults to `eth_estimateGas` RPC output.
        txn_options_base_fee_multiple: float | None, optional
            The multiple applied to the base fee for the transaction. Defaults to 1.
        txn_options_priority_fee_multiple: float | None, optional
            The multiple applied to the priority fee for the transaction. Defaults to 1.
        nonce_func: Callable[[], Nonce] | None
            A callable function to use to get a nonce. This function is useful for e.g.,
            passing in a safe nonce getter tied to an agent.
            Defaults to setting it to the result of `get_transaction_count`.
        preview_before_trade: bool, optional
            Whether to preview the trade before executing. Defaults to False.

        Returns
        -------
        OpenShort
            A dataclass containing the output event of the contract call.
        """
        return await _async_open_short(
            interface=self,
            sender=sender,
            trade_amount=trade_amount,
            slippage_tolerance=slippage_tolerance,
            gas_limit=gas_limit,
            txn_options_base_fee_multiple=txn_options_base_fee_multiple,
            txn_options_priority_fee_multiple=txn_options_priority_fee_multiple,
            nonce_func=nonce_func,
            preview_before_trade=preview_before_trade,
        )

    # We do not control the number of arguments; this is set by hyperdrive-rs
    # pylint: disable=too-many-arguments
    async def async_close_short(
        self,
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
        """Contract call to close a short position.

        Arguments
        ---------
        sender: LocalAccount
            The account that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        maturity_time: int
            The token maturity time in seconds.
        slippage_tolerance: FixedPoint, optional
            Amount of slippage allowed from the trade.
            If given, then the trade will not execute unless the slippage is below this value.
            If not given, then execute the trade regardless of the slippage.
        gas_limit: int | None, optional
            The maximum amount of gas used by the transaction.
            Defaults to `eth_estimateGas` RPC output.
        txn_options_base_fee_multiple: float | None, optional
            The multiple applied to the base fee for the transaction. Defaults to 1.
        txn_options_priority_fee_multiple: float | None, optional
            The multiple applied to the priority fee for the transaction. Defaults to 1.
        nonce_func: Callable[[], Nonce] | None
            A callable function to use to get a nonce. This function is useful for e.g.,
            passing in a safe nonce getter tied to an agent.
            Defaults to setting it to the result of `get_transaction_count`.
        preview_before_trade: bool, optional
            Whether to preview the trade before executing. Defaults to False.

        Returns
        -------
        CloseShort
            A dataclass containing the output event of the contract call.
        """
        return await _async_close_short(
            interface=self,
            sender=sender,
            trade_amount=trade_amount,
            maturity_time=maturity_time,
            slippage_tolerance=slippage_tolerance,
            gas_limit=gas_limit,
            txn_options_base_fee_multiple=txn_options_base_fee_multiple,
            txn_options_priority_fee_multiple=txn_options_priority_fee_multiple,
            nonce_func=nonce_func,
            preview_before_trade=preview_before_trade,
        )

    # We do not control the number of arguments; this is set by hyperdrive-rs
    # pylint: disable=too-many-arguments
    async def async_add_liquidity(
        self,
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
        """Contract call to add liquidity to the Hyperdrive pool.

        Arguments
        ---------
        sender: LocalAccount
            The account that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        min_apr: FixedPoint
            The minimum allowable APR after liquidity is added.
        max_apr: FixedPoint
            The maximum allowable APR after liquidity is added.
        slippage_tolerance: FixedPoint, optional
            Amount of slippage allowed from the trade.
            If given, then the trade will not execute unless the slippage is below this value.
            If not given, then execute the trade regardless of the slippage.
        gas_limit: int | None, optional
            The maximum amount of gas used by the transaction.
            Defaults to `eth_estimateGas` RPC output.
        txn_options_base_fee_multiple: float | None, optional
            The multiple applied to the base fee for the transaction. Defaults to 1.
        txn_options_priority_fee_multiple: float | None, optional
            The multiple applied to the priority fee for the transaction. Defaults to 1.
        nonce_func: Callable[[], Nonce] | None
            A callable function to use to get a nonce. This function is useful for e.g.,
            passing in a safe nonce getter tied to an agent.
            Defaults to setting it to the result of `get_transaction_count`.
        preview_before_trade: bool, optional
            Whether to preview the trade before executing. Defaults to False.

        Returns
        -------
        AddLiquidity
            A dataclass containing the output event of the contract call.
        """
        return await _async_add_liquidity(
            interface=self,
            sender=sender,
            trade_amount=trade_amount,
            min_apr=min_apr,
            max_apr=max_apr,
            slippage_tolerance=slippage_tolerance,
            gas_limit=gas_limit,
            txn_options_base_fee_multiple=txn_options_base_fee_multiple,
            txn_options_priority_fee_multiple=txn_options_priority_fee_multiple,
            nonce_func=nonce_func,
            preview_before_trade=preview_before_trade,
        )

    async def async_remove_liquidity(
        self,
        sender: LocalAccount,
        trade_amount: FixedPoint,
        gas_limit: int | None = None,
        txn_options_base_fee_multiple: float | None = None,
        txn_options_priority_fee_multiple: float | None = None,
        nonce_func: Callable[[], Nonce] | None = None,
        preview_before_trade: bool = False,
    ) -> RemoveLiquidityEventFP:
        """Contract call to remove liquidity from the Hyperdrive pool.

        Arguments
        ---------
        sender: LocalAccount
            The account that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        gas_limit: int | None, optional
            The maximum amount of gas used by the transaction.
            Defaults to `eth_estimateGas` RPC output.
        txn_options_base_fee_multiple: float | None, optional
            The multiple applied to the base fee for the transaction. Defaults to 1.
        txn_options_priority_fee_multiple: float | None, optional
            The multiple applied to the priority fee for the transaction. Defaults to 1.
        nonce_func: Callable[[], Nonce] | None
            A callable function to use to get a nonce. This function is useful for e.g.,
            passing in a safe nonce getter tied to an agent.
            Defaults to setting it to the result of `get_transaction_count`.
        preview_before_trade: bool, optional
            Whether to preview the trade before executing. Defaults to False.

        Returns
        -------
        RemoveLiquidity
            A dataclass containing the output event of the contract call.
        """
        return await _async_remove_liquidity(
            interface=self,
            sender=sender,
            trade_amount=trade_amount,
            gas_limit=gas_limit,
            txn_options_base_fee_multiple=txn_options_base_fee_multiple,
            txn_options_priority_fee_multiple=txn_options_priority_fee_multiple,
            nonce_func=nonce_func,
            preview_before_trade=preview_before_trade,
        )

    async def async_redeem_withdraw_shares(
        self,
        sender: LocalAccount,
        trade_amount: FixedPoint,
        gas_limit: int | None = None,
        txn_options_base_fee_multiple: float | None = None,
        txn_options_priority_fee_multiple: float | None = None,
        nonce_func: Callable[[], Nonce] | None = None,
        preview_before_trade: bool = False,
    ) -> RedeemWithdrawalSharesEventFP:
        """Contract call to redeem withdraw shares from Hyperdrive pool.

        This should be done after closing liquidity.

        .. note::
            This is not guaranteed to redeem all shares. The pool will try to redeem as
            many as possible, up to the withdrawPool.readyToRedeem limit, without reverting.
            This will revert if the min_output is too high or the user is trying to withdraw
            more shares than they have.

        Arguments
        ---------
        sender: LocalAccount
            The account that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        gas_limit: int | None, optional
            The maximum amount of gas used by the transaction.
            Defaults to `eth_estimateGas` RPC output.
        txn_options_base_fee_multiple: float | None, optional
            The multiple applied to the base fee for the transaction. Defaults to 1.
        txn_options_priority_fee_multiple: float | None, optional
            The multiple applied to the priority fee for the transaction. Defaults to 1.
        nonce_func: Callable[[], Nonce] | None
            A callable function to use to get a nonce. This function is useful for e.g.,
            passing in a safe nonce getter tied to an agent.
            Defaults to setting it to the result of `get_transaction_count`.
        preview_before_trade: bool, optional
            Whether to preview the trade before executing. Defaults to False.

        Returns
        -------
        RedeemWithdrawalShares
            A dataclass containing the output event of the contract call.
        """
        return await _async_redeem_withdraw_shares(
            interface=self,
            sender=sender,
            trade_amount=trade_amount,
            gas_limit=gas_limit,
            txn_options_base_fee_multiple=txn_options_base_fee_multiple,
            txn_options_priority_fee_multiple=txn_options_priority_fee_multiple,
            nonce_func=nonce_func,
            preview_before_trade=preview_before_trade,
        )

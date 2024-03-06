"""High-level interface for writing to Hyperdrive smart contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING

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

# We have no control over the number of arguments since it is specified by the smart contracts
# pylint: disable=too-many-arguments
# We only worry about protected access for anyone outside of this folder.
# pylint: disable=protected-access


if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount
    from eth_typing import BlockNumber
    from fixedpointmath import FixedPoint
    from web3 import Web3
    from web3.types import Nonce

    from agent0.ethpy import EthConfig
    from agent0.ethpy.hyperdrive.addresses import HyperdriveAddresses
    from agent0.ethpy.hyperdrive.receipt_breakdown import ReceiptBreakdown


class HyperdriveReadWriteInterface(HyperdriveReadInterface):
    """Read-write end-point API for interfacing with a deployed Hyperdrive pool."""

    def __init__(
        self,
        eth_config: EthConfig | None = None,
        addresses: HyperdriveAddresses | None = None,
        web3: Web3 | None = None,
        read_retry_count: int | None = None,
        write_retry_count: int | None = None,
    ) -> None:
        """The HyperdriveReadInterface API. This is the primary endpoint for
        users to execute transactions on Hyperdrive smart contracts.

        Arguments
        ---------
        eth_config: EthConfig, optional
            Configuration dataclass for the ethereum environment.
            If given, then it is constructed from environment variables.
        addresses: HyperdriveAddresses, optional
            This is a dataclass containing addresses for deployed hyperdrive and base token contracts.
            If given, then the `eth_config.artifacts_uri` variable is not used, and these Addresses are used instead.
            If not given, then addresses is constructed from the `addresses.json` file at `eth_config.artifacts_uri`.
        web3: Web3, optional
            web3 provider object, optional
            If given, a web3 object is constructed using the `eth_config.rpc_uri` as the http provider.
        read_retry_count: int | None, optional
            The number of times to retry the read call if it fails. Defaults to 5.
        write_retry_count: int | None, optional
            The number of times to retry the transact call if it fails. Defaults to no retries.
        """
        super().__init__(eth_config, addresses, web3, read_retry_count)
        self.write_retry_count = write_retry_count

    def get_read_interface(self) -> HyperdriveReadInterface:
        """Return the current instance as an instance of the parent (HyperdriveReadInterface) class.

        Returns
        -------
        HyperdriveReadInterface
            This instantiated object, but as a ReadInterface.
        """
        return HyperdriveReadInterface(self.eth_config, self.addresses, self.web3, self.read_retry_count)

    def create_checkpoint(
        self, sender: LocalAccount, block_number: BlockNumber | None = None, checkpoint_time: int | None = None
    ) -> ReceiptBreakdown:
        """Create a Hyperdrive checkpoint.

        Arguments
        ---------
        sender: LocalAccount
            The sender account that is executing and signing the trade transaction.
        block_number: BlockNumber, optional
            The number for any minted block.
            Defaults to the current block number.
        checkpoint_time: int, optional
            The checkpoint time to use. Defaults to the corresponding checkpoint for the provided block_number

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the output event of the contract call.
        """
        return _create_checkpoint(self, sender, block_number, checkpoint_time)

    def set_variable_rate(self, sender: LocalAccount, new_rate: FixedPoint) -> None:
        """Set the variable rate for the yield source.

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
        agent: LocalAccount,
        trade_amount: FixedPoint,
        slippage_tolerance: FixedPoint | None = None,
        nonce: Nonce | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to open a long position.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        slippage_tolerance: FixedPoint, optional
            Amount of slippage allowed from the trade.
            If given, then the trade will not execute unless the slippage is below this value.
            If not given, then execute the trade regardless of the slippage.
        nonce: Nonce, optional
            An optional explicit nonce to set with the transaction.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed.
        """
        return await _async_open_long(
            self, agent, trade_amount, slippage_tolerance, nonce, self.eth_config.preview_before_trade
        )

    # We do not control the number of arguments; this is set by hyperdrive-rs
    # pylint: disable=too-many-arguments
    async def async_close_long(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        maturity_time: int,
        slippage_tolerance: FixedPoint | None = None,
        nonce: Nonce | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to close a long position.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The amount of bonds you wish to close.
        maturity_time: int
            The token maturity time in seconds.
        slippage_tolerance: FixedPoint, optional
            Amount of slippage allowed from the trade.
            If given, then the trade will not execute unless the slippage is below this value.
            If not given, then execute the trade regardless of the slippage.
        nonce: Nonce, optional
            An optional explicit nonce to set with the transaction.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed.
        """
        return await _async_close_long(
            self, agent, trade_amount, maturity_time, slippage_tolerance, nonce, self.eth_config.preview_before_trade
        )

    async def async_open_short(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        slippage_tolerance: FixedPoint | None = None,
        nonce: Nonce | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to open a short position.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        slippage_tolerance: FixedPoint, optional
            Amount of slippage allowed from the trade.
            If given, then the trade will not execute unless the slippage is below this value.
            If not given, then execute the trade regardless of the slippage.
        nonce: Nonce, optional
            An explicit nonce to set with the transaction.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed.
        """
        return await _async_open_short(
            self, agent, trade_amount, slippage_tolerance, nonce, self.eth_config.preview_before_trade
        )

    # We do not control the number of arguments; this is set by hyperdrive-rs
    # pylint: disable=too-many-arguments
    async def async_close_short(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        maturity_time: int,
        slippage_tolerance: FixedPoint | None = None,
        nonce: Nonce | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to close a short position.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        maturity_time: int
            The token maturity time in seconds.
        slippage_tolerance: FixedPoint, optional
            Amount of slippage allowed from the trade.
            If given, then the trade will not execute unless the slippage is below this value.
            If not given, then execute the trade regardless of the slippage.
        nonce: Nonce, optional
            An explicit nonce to set with the transaction.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the maturity time and the absolute values for token quantities changed.
        """
        return await _async_close_short(
            self, agent, trade_amount, maturity_time, slippage_tolerance, nonce, self.eth_config.preview_before_trade
        )

    # We do not control the number of arguments; this is set by hyperdrive-rs
    # pylint: disable=too-many-arguments
    async def async_add_liquidity(
        self,
        agent: LocalAccount,
        trade_amount: FixedPoint,
        min_apr: FixedPoint,
        max_apr: FixedPoint,
        slippage_tolerance: FixedPoint | None = None,
        nonce: Nonce | None = None,
    ) -> ReceiptBreakdown:
        """Contract call to add liquidity to the Hyperdrive pool.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
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
        nonce: Nonce, optional
            An explicit nonce to set with the transaction.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the absolute values for token quantities changed.
        """
        return await _async_add_liquidity(
            self,
            agent,
            trade_amount,
            min_apr,
            max_apr,
            slippage_tolerance=slippage_tolerance,
            nonce=nonce,
            preview_before_trade=self.eth_config.preview_before_trade,
        )

    async def async_remove_liquidity(
        self, agent: LocalAccount, trade_amount: FixedPoint, nonce: Nonce | None = None
    ) -> ReceiptBreakdown:
        """Contract call to remove liquidity from the Hyperdrive pool.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        nonce: Nonce, optional
            An explicit nonce to set with the transaction.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the absolute values for token quantities changed.
        """
        return await _async_remove_liquidity(self, agent, trade_amount, nonce, self.eth_config.preview_before_trade)

    async def async_redeem_withdraw_shares(
        self, agent: LocalAccount, trade_amount: FixedPoint, nonce: Nonce | None = None
    ) -> ReceiptBreakdown:
        """Contract call to redeem withdraw shares from Hyperdrive pool.
        This should be done after closing liquidity.

        .. note::
            This is not guaranteed to redeem all shares. The pool will try to redeem as
            many as possible, up to the withdrawPool.readyToRedeem limit, without reverting.
            This will revert if the min_output is too high or the user is trying to withdraw
            more shares than they have.

        Arguments
        ---------
        agent: LocalAccount
            The account for the agent that is executing and signing the trade transaction.
        trade_amount: FixedPoint
            The size of the position, in base.
        nonce: Nonce | None, optional
            An explicit nonce to set with the transaction.

        Returns
        -------
        ReceiptBreakdown
            A dataclass containing the absolute values for token quantities changed.
        """
        return await _async_redeem_withdraw_shares(self, agent, trade_amount, nonce)

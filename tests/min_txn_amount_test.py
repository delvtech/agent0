"""Test for invalid trades due to trade too small."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fixedpointmath import FixedPoint
from pypechain.core import PypechainCallException
from utils import expect_failure_with_funded_bot  # type: ignore
from web3.exceptions import ContractCustomError

from agent0.core.base import Trade
from agent0.core.hyperdrive import HyperdriveMarketAction, HyperdriveWallet
from agent0.core.hyperdrive.agent import (
    add_liquidity_trade,
    close_long_trade,
    close_short_trade,
    open_long_trade,
    open_short_trade,
    remove_liquidity_trade,
)
from agent0.core.hyperdrive.interactive import LocalHyperdrive
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy

if TYPE_CHECKING:
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface

# ruff: noqa: PLR2004 (magic values used for counter)


# Start by defining policies for failed trades
# One policy per failed trade

SMALL_TRADE_AMOUNT = FixedPoint(scaled_value=1000)


class InvalidAddLiquidity(HyperdriveBasePolicy):
    """An agent that submits an invalid add liquidity due to min txn amount."""

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Add liquidity.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market interface.
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[HyperdriveMarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = [add_liquidity_trade(SMALL_TRADE_AMOUNT)]
        return action_list, True


class InvalidRemoveLiquidity(HyperdriveBasePolicy):
    """An agent that submits an invalid remove liquidity due to min txn amount."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Remove liquidity.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market interface.
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[HyperdriveMarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        if self.counter == 0:
            # Add liquidity
            action_list.append(add_liquidity_trade(FixedPoint(10_000)))
        elif self.counter == 2:
            # Remove liquidity
            action_list.append(remove_liquidity_trade(SMALL_TRADE_AMOUNT))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidOpenLong(HyperdriveBasePolicy):
    """An agent that submits an invalid open long due to min txn amount."""

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Open long.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market interface.
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[HyperdriveMarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        # Closing non-existent long
        action_list.append(open_long_trade(SMALL_TRADE_AMOUNT, self.slippage_tolerance))
        return action_list, True


class InvalidOpenShort(HyperdriveBasePolicy):
    """An agent that submits an invalid open short due to min txn amount."""

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Open short.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market interface.
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[HyperdriveMarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        # Open a short for too few bonds
        action_list = [open_short_trade(SMALL_TRADE_AMOUNT, self.slippage_tolerance)]
        return action_list, True


class InvalidCloseLong(HyperdriveBasePolicy):
    """An agent that submits an invalid close long due to min txn amount."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Close long.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market interface.
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[HyperdriveMarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        if self.counter == 0:
            # Add liquidity for other valid trades
            action_list.append(add_liquidity_trade(FixedPoint(100_000)))
        if self.counter == 1:
            # Open Long
            action_list.append(open_long_trade(FixedPoint(10_000), self.slippage_tolerance))
        elif self.counter == 2:
            # Closing existing long for a small trade amount
            assert len(wallet.longs) == 1
            for long_time in wallet.longs.keys():
                action_list.append(close_long_trade(SMALL_TRADE_AMOUNT, long_time, self.slippage_tolerance))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class InvalidCloseShort(HyperdriveBasePolicy):
    """An agent that submits an invalid close short due to min txn amount."""

    counter = 0

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Close short.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market interface.
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[HyperdriveMarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False
        if self.counter == 0:
            # Add liquidity for other valid trades
            action_list.append(add_liquidity_trade(FixedPoint(100_000)))
        if self.counter == 1:
            # Open Short
            action_list.append(open_short_trade(FixedPoint(10_000), self.slippage_tolerance))
        elif self.counter == 2:
            # Closing existent short for more than I have
            assert len(wallet.shorts) == 1
            for short_time in wallet.shorts.keys():
                action_list.append(close_short_trade(SMALL_TRADE_AMOUNT, short_time, self.slippage_tolerance))
            done_trading = True
        self.counter += 1
        return action_list, done_trading


class TestMinTxAmount:
    """Test pipeline from bots making invalid trades."""

    @pytest.mark.anvil
    def test_invalid_add_liquidity_min_txn(
        self,
        fast_hyperdrive_fixture: LocalHyperdrive,
    ):
        try:
            expect_failure_with_funded_bot(fast_hyperdrive_fixture, InvalidAddLiquidity)
        except PypechainCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Minimum Transaction Amount:" in exc.args[0]
            # Fails on remove liquidity
            assert exc.function_name == "addLiquidity"
            # FIXME double check this
            # This throws ContractCallException under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert "ContractCustomError('MinimumTransactionAmount')" in exc.args

    @pytest.mark.anvil
    def test_invalid_remove_liquidity_min_txn(
        self,
        fast_hyperdrive_fixture: LocalHyperdrive,
    ):
        try:
            expect_failure_with_funded_bot(fast_hyperdrive_fixture, InvalidRemoveLiquidity)
        except PypechainCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Minimum Transaction Amount:" in exc.args[0]
            # Fails on remove liquidity
            assert exc.function_name == "removeLiquidity"
            # FIXME double check this
            # This throws ContractCallException under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert "ContractCustomError('MinimumTransactionAmount')" in exc.args

    # We don't test withdrawal shares because redeeming withdrawal shares are not subject to min_txn_amount

    @pytest.mark.anvil
    def test_invalid_open_long_min_txn(
        self,
        fast_hyperdrive_fixture: LocalHyperdrive,
    ):
        try:
            expect_failure_with_funded_bot(fast_hyperdrive_fixture, InvalidOpenLong)
        except PypechainCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Minimum Transaction Amount:" in exc.args[0]
            # Fails on remove liquidity
            assert exc.function_name == "openLong"
            # FIXME double check this
            # This throws ContractCallException under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert "ContractCustomError('MinimumTransactionAmount')" in exc.args

    @pytest.mark.anvil
    def test_invalid_open_short_min_txn(
        self,
        fast_hyperdrive_fixture: LocalHyperdrive,
    ):
        try:
            expect_failure_with_funded_bot(fast_hyperdrive_fixture, InvalidOpenShort)
        except PypechainCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Minimum Transaction Amount:" in exc.args[0]
            # Fails on remove liquidity
            assert exc.function_name == "openShort"
            # FIXME double check this
            # This throws ContractCallException under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert "ContractCustomError('MinimumTransactionAmount')" in exc.args

    @pytest.mark.anvil
    def test_invalid_close_long_min_txn(
        self,
        fast_hyperdrive_fixture: LocalHyperdrive,
    ):
        try:
            expect_failure_with_funded_bot(fast_hyperdrive_fixture, InvalidCloseLong)
        except PypechainCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Minimum Transaction Amount:" in exc.args[0]
            # Fails on remove liquidity
            assert exc.function_name == "closeLong"
            # FIXME double check this
            # This throws ContractCallException under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert "ContractCustomError('MinimumTransactionAmount')" in exc.args

    @pytest.mark.anvil
    def test_invalid_close_short_min_txn(
        self,
        fast_hyperdrive_fixture: LocalHyperdrive,
    ):
        try:
            expect_failure_with_funded_bot(fast_hyperdrive_fixture, InvalidCloseShort)
        except PypechainCallException as exc:
            # Expected error due to illegal trade
            # We do add an argument for invalid balance to the args, so check for that here
            assert "Minimum Transaction Amount:" in exc.args[0]
            # Fails on remove liquidity
            assert exc.function_name == "closeShort"
            # FIXME double check this
            # This throws ContractCallException under the hood
            assert exc.orig_exception is not None
            assert isinstance(exc.orig_exception, ContractCustomError)
            assert "ContractCustomError('MinimumTransactionAmount')" in exc.args[0]

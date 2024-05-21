"""Pytest fixture that creates an in memory db session and creates dummy db schemas"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Type

import pytest
from fixedpointmath import FixedPoint

from agent0.core.base import Trade
from agent0.core.hyperdrive.agent import (
    add_liquidity_trade,
    close_long_trade,
    close_short_trade,
    open_long_trade,
    open_short_trade,
    redeem_withdraw_shares_trade,
    remove_liquidity_trade,
)
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
from agent0.ethpy.hyperdrive import HyperdriveReadInterface

if TYPE_CHECKING:
    from agent0.core.hyperdrive import HyperdriveMarketAction, HyperdriveWallet


# Build custom policy
# Simple agent, opens a set of all trades for a fixed amount and closes them after
class CycleTradesPolicy(HyperdriveBasePolicy):
    """A agent that simply cycles through all trades."""

    @dataclass(kw_only=True)
    class Config(HyperdriveBasePolicy.Config):
        """Custom config arguments for this policy."""

        max_trades: int | None = None
        """The maximum amount of trades to make before this policy is done trading."""

    # Using default parameters
    def __init__(
        self,
        policy_config: Config,
    ):
        # We want to do a sequence of trades one at a time, so we keep an internal counter based on
        # how many times `action` has been called.
        self.counter = 0
        self.max_trades = policy_config.max_trades
        super().__init__(policy_config)

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """This agent simply opens all trades for a fixed amount and closes them after, one at a time

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market.
        wallet: HyperdriveWallet
            agent's wallet

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        done_trading = False

        # Early stopping based on parameter
        if (self.max_trades is not None) and (self.counter >= self.max_trades):
            # We want this bot to exit and crash after it's done the trades it needs to do
            return [], True

        if self.counter == 0:
            # Add liquidity
            action_list.append(add_liquidity_trade(trade_amount=FixedPoint(111_111)))
        elif self.counter == 1:
            # Open Long
            action_list.append(open_long_trade(FixedPoint(22_222), self.slippage_tolerance))
        elif self.counter == 2:
            # Open Short
            action_list.append(open_short_trade(FixedPoint(333), self.slippage_tolerance))
        elif self.counter == 3:
            # Remove All Liquidity
            action_list.append(remove_liquidity_trade(wallet.lp_tokens))
        elif self.counter == 4:
            # Re-add liquidity to allow for closing positions
            action_list.append(add_liquidity_trade(trade_amount=FixedPoint(111_111)))
        elif self.counter == 5:
            # Close All Longs
            assert len(wallet.longs) == 1
            for long_time, long in wallet.longs.items():
                action_list.append(close_long_trade(long.balance, long_time, self.slippage_tolerance))
        elif self.counter == 6:
            # Close All Shorts
            assert len(wallet.shorts) == 1
            for short_time, short in wallet.shorts.items():
                action_list.append(close_short_trade(short.balance, short_time, self.slippage_tolerance))
        elif self.counter == 7:
            # Redeem all withdrawal shares
            action_list.append(redeem_withdraw_shares_trade(wallet.withdraw_shares))
        else:
            done_trading = True
        self.counter += 1
        return action_list, done_trading


@pytest.fixture(scope="function")
def cycle_trade_policy() -> Type[CycleTradesPolicy]:
    """Test fixture to build a policy that cycles through all trades.

    Returns
    -------
    CycleTradesPolicy
        A policy that cycles through all trades.
    """
    return CycleTradesPolicy

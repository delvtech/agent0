"""Pytest fixture that creates an in memory db session and creates dummy db schemas"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Type

import pytest
from ethpy.hyperdrive.interface import HyperdriveReadInterface
from fixedpointmath import FixedPoint

from agent0.base import Trade
from agent0.hyperdrive.policies import HyperdrivePolicy
from agent0.hyperdrive.state import HyperdriveMarketAction, HyperdriveWallet


# Build custom policy
# Simple agent, opens a set of all trades for a fixed amount and closes them after
class CycleTradesPolicy(HyperdrivePolicy):
    """A agent that simply cycles through all trades"""

    @dataclass(kw_only=True)
    class Config(HyperdrivePolicy.Config):
        """Custom config arguments for this policy

        Attributes
        ----------
        max_trades: int
            The maximum amount of trades to make before this policy is done trading
        """

        max_trades: int | None = None

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
            action_list.append(interface.add_liquidity_trade(trade_amount=FixedPoint(11_111)))
        elif self.counter == 1:
            # Open Long
            action_list.append(interface.open_long_trade(FixedPoint(22_222), self.slippage_tolerance))
        elif self.counter == 2:
            # Open Short
            action_list.append(interface.open_short_trade(FixedPoint(33_333), self.slippage_tolerance))
        elif self.counter == 3:
            # Remove All Liquidity
            action_list.append(interface.remove_liquidity_trade(wallet.lp_tokens))
        elif self.counter == 4:
            # Close All Longs
            assert len(wallet.longs) == 1
            for long_time, long in wallet.longs.items():
                action_list.append(interface.close_long_trade(long.balance, long_time, self.slippage_tolerance))
        elif self.counter == 5:
            # Close All Shorts
            assert len(wallet.shorts) == 1
            for short_time, short in wallet.shorts.items():
                action_list.append(interface.close_short_trade(short.balance, short_time, self.slippage_tolerance))
        elif self.counter == 6:
            # Redeem all withdrawal shares
            action_list.append(interface.redeem_withdraw_shares_trade(wallet.withdraw_shares))
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

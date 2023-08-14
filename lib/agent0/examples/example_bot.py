"""Script to showcase setting up and running custom bots"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agent0.base.config import AgentConfig, Budget, EnvironmentConfig
from agent0.hyperdrive import HyperdriveActionType, HyperdriveMarketAction
from agent0.hyperdrive.policies import HyperdrivePolicy
from elfpy.types import MarketType, Trade
from fixedpointmath import FixedPoint

if TYPE_CHECKING:
    from agent0.hyperdrive.agents import HyperdriveWallet
    from elfpy.markets.hyperdrive import HyperdriveMarket as HyperdriveMarketState
    from numpy.random._generator import Generator as NumpyGenerator


# Build custom policy
# Simple bot, opens a set of all trades for a fixed amount and closes them after
class CycleTradesPolicy(HyperdrivePolicy):
    """A bot that simply cycles through all trades"""

    # Using default parameters
    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        # Add additional parameters for custom policy here
        static_trade_amount: FixedPoint = FixedPoint("100"),
    ):
        self.static_trade_amount = static_trade_amount
        # We want to do a sequence of trades one at a time, so we keep an internal counter based on
        # how many times `action` has been called.
        self.counter = 0
        super().__init__(budget, rng, slippage_tolerance)

    def action(self, market: HyperdriveMarketState, wallet: HyperdriveWallet) -> list[Trade[HyperdriveMarketAction]]:
        """This bot simply opens all trades for a fixed amount and closes them after, one at a time"""
        action_list = []
        if self.counter == 0:
            # Add liquidity
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.ADD_LIQUIDITY,
                    trade_amount=self.static_trade_amount,
                    wallet=wallet,
                ),
            )
        elif self.counter == 1:
            # Open Long
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.OPEN_LONG,
                    trade_amount=self.static_trade_amount,
                    wallet=wallet,
                ),
            )
        elif self.counter == 2:
            # Open Short
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.OPEN_SHORT,
                    trade_amount=self.static_trade_amount,
                    wallet=wallet,
                ),
            )
        elif self.counter == 3:
            # Remove All Liquidity
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.REMOVE_LIQUIDITY,
                    trade_amount=wallet.lp_tokens,
                    wallet=wallet,
                ),
            )
        elif self.counter == 4:
            # Close All Longs
            for long_time, long in wallet.longs.items():
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.CLOSE_LONG,
                        trade_amount=long.balance,
                        wallet=wallet,
                        # TODO is this actually maturity time? Not mint time?
                        mint_time=long_time,
                    ),
                )
        elif self.counter == 4:
            # Close All Shorts
            for short_time, short in wallet.shorts.items():
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.CLOSE_SHORT,
                        trade_amount=short.balance,
                        wallet=wallet,
                        # TODO is this actually maturity time? Not mint time?
                        mint_time=short_time,
                    ),
                )
        elif self.counter == 5:
            # Redeem all withdrawal shares
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.REDEEM_WITHDRAW_SHARE,
                    trade_amount=wallet.withdraw_shares,
                    wallet=wallet,
                ),
            )
        elif self.counter == 6:
            # One more dummy trade to ensure the previous trades get into the db
            # TODO test if we can remove this eventually
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.OPEN_LONG,
                    trade_amount=self.static_trade_amount,
                    wallet=wallet,
                ),
            )

        self.counter += 1
        return action_list


# Build environment config
# Using defaults here
env_config = EnvironmentConfig()

agent_config: list[AgentConfig] = [
    AgentConfig(
        policy=CycleTradesPolicy,
        number_of_agents=1,
        slippage_tolerance=FixedPoint(0.0001),
        base_budget=FixedPoint("1e6"),
        eth_budget=FixedPoint("1e18"),
        init_kwargs={"trade_chance": FixedPoint(0.8)},
    ),
]


# Run the bot

"""Initializer agent

Special reserved user strategy that is used to initialize a market with a desired amount of share & bond reserves
"""
from elfpy.agents.agent import Agent
from elfpy.markets.hyperdrive import Market, MarketActionType

import elfpy.types as types

# pylint: disable=duplicate-code


class Policy(Agent):
    """Adds a large LP"""

    def action(self, market: Market) -> "list[types.Trade]":
        """
        User strategy adds liquidity and then takes no additional actions
        """
        if self.wallet.lp_tokens > 0:  # has already opened the lp
            return []
        return [
            types.Trade(
                types.MarketType.HYPERDRIVE,
                self.create_hyperdrive_action(action_type=MarketActionType.ADD_LIQUIDITY, trade_amount=self.budget),
            )
        ]

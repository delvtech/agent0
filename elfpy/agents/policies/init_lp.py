"""Initializer agent

Special reserved user strategy that is used to initialize a market with a desired amount of share & bond reserves
"""
from elfpy.agents.agent import Agent
import elfpy.markets.base as base
import elfpy.markets.hyperdrive as hyperdrive

import elfpy.types as types

# pylint: disable=duplicate-code


class Policy(Agent):
    """Adds a large LP"""

    def action(self, markets: "dict[types.MarketTypes, base.Market]") -> "list[types.Trade]":
        """
        User strategy adds liquidity and then takes no additional actions
        """
        if self.wallet.lp_tokens > 0:  # has already opened the lp
            return []
        action_list = []
        for market_type, market in markets.items():
            if market_type == types.MarketType.HYPERDRIVE:
                action_list.append(
                    types.Trade(
                        agent=self,
                        market=types.MarketType.HYPERDRIVE,
                        trade=hyperdrive.MarketAction(
                            action_type=hyperdrive.MarketActionType.ADD_LIQUIDITY,
                            trade_amount=self.budget,
                            wallet=self.wallet,
                        ),
                    )
                )
        return action_list

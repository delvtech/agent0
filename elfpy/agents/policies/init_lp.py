"""Initializer agent

Special reserved user strategy that is used to initialize a market with a desired amount of share & bond reserves
"""
from elfpy.agents.agent import Agent
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market

import elfpy.types as types

# pylint: disable=duplicate-code


class Policy(Agent):
    """Adds a large LP"""

    def action(self, market: hyperdrive_market.Market) -> "list[types.Trade]":
        """
        User strategy adds liquidity and then takes no additional actions
        """
        if self.wallet.lp_tokens > 0:  # has already opened the lp
            return []
        return [
            types.Trade(
                market=types.MarketType.HYPERDRIVE,
                trade=hyperdrive_market.MarketAction(
                    action_type=hyperdrive_market.MarketActionType.ADD_LIQUIDITY,
                    trade_amount=self.budget,
                    wallet=self.wallet,
                ),
            )
        ]

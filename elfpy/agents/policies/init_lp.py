"""Initializer agent

Special reserved user strategy that is used to initialize a market with a desired amount of share & bond reserves
"""
from typing import List

import elfpy.agents.agent as elf_agent
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.types as types
from elfpy.math import FixedPoint


class Policy(elf_agent.Agent):
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
                trade=hyperdrive_actions.MarketAction(
                    action_type=hyperdrive_actions.MarketActionType.ADD_LIQUIDITY,
                    trade_amount=self.budget,
                    wallet=self.wallet,
                ),
            )
        ]


class InitializeLiquidityAgent(elf_agent.AgentFP):
    """Adds a large LP"""

    def action(self, market: hyperdrive_market.MarketFP) -> List[types.Trade]:
        """
        User strategy adds liquidity and then takes no additional actions
        """
        if self.wallet.lp_tokens > FixedPoint(0):  # has already opened the lp
            return []
        return [
            types.Trade(
                market=types.MarketType.HYPERDRIVE,
                trade=hyperdrive_actions.MarketActionFP(
                    action_type=hyperdrive_actions.MarketActionType.ADD_LIQUIDITY,
                    trade_amount=self.budget,
                    wallet=self.wallet,
                ),
            )
        ]

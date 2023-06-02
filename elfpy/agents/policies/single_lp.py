"""User strategy that adds base liquidity and doesn't remove until liquidation"""
from __future__ import annotations

from numpy.random._generator import Generator as NumpyGenerator

import elfpy.agents.agent as elf_agent
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.types as types
from elfpy.math import FixedPoint


class SingleLpAgent(elf_agent.Agent):
    """simple LP that only has one LP open at a time"""

    def __init__(
        self,
        wallet_address: int,
        budget: FixedPoint = FixedPoint("1000.0"),
        rng: NumpyGenerator | None = None,
        amount_to_lp: FixedPoint = FixedPoint("100.0"),
    ):
        """call basic policy init then add custom stuff"""
        self.amount_to_lp: FixedPoint = amount_to_lp
        super().__init__(wallet_address, budget, rng)

    def action(self, _market: hyperdrive_market.Market) -> list[types.Trade]:
        """
        implement user strategy
        LP if you can, but only do it once
        """
        action_list = []
        has_lp = self.wallet.lp_tokens > FixedPoint(0)
        can_lp = self.wallet.balance.amount >= self.amount_to_lp
        if can_lp and not has_lp:
            action_list.append(
                types.Trade(
                    market=types.MarketType.HYPERDRIVE,
                    trade=hyperdrive_actions.HyperdriveMarketAction(
                        action_type=hyperdrive_actions.MarketActionType.ADD_LIQUIDITY,
                        trade_amount=self.amount_to_lp,
                        wallet=self.wallet,
                    ),
                )
            )
        return action_list

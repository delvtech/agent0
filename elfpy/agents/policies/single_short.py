"""User strategy that opens a single short and doesn't close until liquidation"""
from __future__ import annotations

from numpy.random._generator import Generator as NumpyGenerator

import elfpy.agents.agent as elf_agent
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.types as types
from elfpy.math import FixedPoint


class SingleShortAgent(elf_agent.Agent):
    """simple short thatonly has one long open at a time"""

    def __init__(
        self,
        wallet_address: int,
        budget: FixedPoint = FixedPoint("100.0"),
        amount_to_trade: FixedPoint | None = None,
        rng: NumpyGenerator | None = None,
    ):
        """call basic policy init then add custom stuff"""
        if amount_to_trade is None:
            amount_to_trade = budget
        self.amount_to_trade = amount_to_trade
        super().__init__(wallet_address, budget, rng)

    def action(self, market: hyperdrive_market.Market) -> list[types.Trade]:
        """Implement user strategy: short if you can, only once."""
        action_list = []
        shorts = list(self.wallet.shorts.values())
        has_opened_short = len(shorts) > 0
        can_open_short = self.get_max_short(market) >= self.amount_to_trade
        if can_open_short and not has_opened_short:
            action_list.append(
                types.Trade(
                    market=types.MarketType.HYPERDRIVE,
                    trade=hyperdrive_actions.HyperdriveMarketAction(
                        action_type=hyperdrive_actions.MarketActionType.OPEN_SHORT,
                        trade_amount=self.amount_to_trade,
                        wallet=self.wallet,
                    ),
                )
            )
        return action_list

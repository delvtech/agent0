"""User strategy that adds liquidity and then removes it when enough time has passed"""
from __future__ import annotations

import elfpy.agents.agent as elf_agent
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.types as types
from elfpy.math import FixedPoint


class LpAndWithdrawAgent(elf_agent.Agent):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(self, wallet_address, budget: FixedPoint = FixedPoint("1000.0")):
        """call basic policy init then add custom stuff"""
        self.time_to_withdraw = FixedPoint("1.0")
        self.amount_to_lp = FixedPoint("100.0")
        super().__init__(wallet_address, budget)

    def action(self, market: hyperdrive_market.Market) -> list[types.Trade]:
        """
        implement user strategy
        LP if you can, but only do it once
        """
        # pylint disable=unused-argument
        action_list: list[types.Trade] = []
        has_lp = self.wallet.lp_tokens > FixedPoint(0)
        amount_in_base = self.wallet.balance.amount
        can_lp = amount_in_base >= self.amount_to_lp
        if not has_lp and can_lp:
            action_list.append(
                types.Trade(
                    market=types.MarketType.HYPERDRIVE,
                    trade=hyperdrive_actions.MarketAction(
                        action_type=hyperdrive_actions.MarketActionType.ADD_LIQUIDITY,
                        trade_amount=self.amount_to_lp,
                        wallet=self.wallet,
                    ),
                )
            )
        elif has_lp:
            enough_time_has_passed = market.block_time.time > self.time_to_withdraw
            if enough_time_has_passed:
                action_list.append(
                    types.Trade(
                        market=types.MarketType.HYPERDRIVE,
                        trade=hyperdrive_actions.MarketAction(
                            action_type=hyperdrive_actions.MarketActionType.REMOVE_LIQUIDITY,
                            trade_amount=self.wallet.lp_tokens,
                            wallet=self.wallet,
                        ),
                    )
                )
        return action_list

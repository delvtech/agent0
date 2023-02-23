"""User strategy that adds liquidity and then removes it when enough time has passed"""
from elfpy.agents.agent import Agent
import elfpy.markets.hyperdrive as hyperdrive
import elfpy.markets.base as base
import elfpy.types as types

# pylint: disable=duplicate-code


class Policy(Agent):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(self, wallet_address, budget=1000):
        """call basic policy init then add custom stuff"""
        self.time_to_withdraw = 1.0
        self.amount_to_lp = 100
        super().__init__(wallet_address, budget)

    def action(self, markets: "dict[types.MarketType, base.Market]") -> "list[types.Trade]":
        """
        implement user strategy
        LP if you can, but only do it once
        """
        # pylint disable=unused-argument
        action_list = []
        for market_type, market in markets.items():
            if market_type == types.MarketType.HYPERDRIVE:
                has_lp = self.wallet.lp_tokens > 0
                amount_in_base = self.wallet.balance.amount
                can_lp = amount_in_base >= self.amount_to_lp
                if not has_lp and can_lp:
                    action_list.append(
                        types.Trade(
                            agent=self.wallet.address,
                            market=types.MarketType.HYPERDRIVE,
                            trade=hyperdrive.MarketAction(
                                action_type=hyperdrive.MarketActionType.ADD_LIQUIDITY,
                                trade_amount=self.amount_to_lp,
                                wallet=self.wallet,
                            ),
                        )
                    )
                elif has_lp:
                    enough_time_has_passed = market.time > self.time_to_withdraw
                    if enough_time_has_passed:
                        action_list.append(
                            types.Trade(
                                agent=self,
                                market=types.MarketType.HYPERDRIVE,
                                trade=hyperdrive.MarketAction(
                                    action_type=hyperdrive.MarketActionType.REMOVE_LIQUIDITY,
                                    trade_amount=self.wallet.lp_tokens,
                                    wallet=self.wallet,
                                ),
                            )
                        )
        return action_list

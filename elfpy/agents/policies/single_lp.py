"""User strategy that adds base liquidity and doesn't remove until liquidation"""
import elfpy.agents.agent as agent
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.types as types
from elfpy.utils.math import FixedPoint

# TODO: the init calls are replicated across each strategy, which looks like duplicate code
#     this should be resolved once we fix user inheritance
# issue #217
# pylint: disable=duplicate-code


class Policy(agent.Agent):
    """simple LP that only has one LP open at a time"""

    def __init__(self, wallet_address, budget=1000):
        """call basic policy init then add custom stuff"""
        self.amount_to_lp = 100
        super().__init__(wallet_address, budget)

    def action(self, _market: hyperdrive_market.Market) -> "list[types.Trade]":
        """
        implement user strategy
        LP if you can, but only do it once
        """
        action_list = []
        has_lp = self.wallet.lp_tokens > 0
        can_lp = self.wallet.balance.amount >= self.amount_to_lp
        if can_lp and not has_lp:
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
        return action_list


class SingleLpAgent(agent.AgentFP):
    """simple LP that only has one LP open at a time"""

    def __init__(self, wallet_address: int, budget: FixedPoint = FixedPoint("1000.0")):
        """call basic policy init then add custom stuff"""
        self.amount_to_lp = FixedPoint("100.0")
        super().__init__(wallet_address, budget)

    def action(self, _market: hyperdrive_market.MarketFP) -> "list[types.Trade]":
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
                    trade=hyperdrive_actions.MarketActionFP(
                        action_type=hyperdrive_actions.MarketActionType.ADD_LIQUIDITY,
                        trade_amount=self.amount_to_lp,
                        wallet=self.wallet,
                    ),
                )
            )
        return action_list

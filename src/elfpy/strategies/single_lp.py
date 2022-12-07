"""
User strategy that adds base liquidity and doesn't remove until liquidation
"""
# TODO: the init calls are replicated across each strategy, which looks like duplicate code
#     this should be resolved once we fix user inheritance
# pylint: disable=duplicate-code
# pylint: disable=too-many-arguments

from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    "single LP: only has one LP open at a time"
    amount_to_lp = 100

    def action(self):
        has_lp = self.wallet.lp_in_wallet > 0
        can_lp = self.wallet.base_in_wallet >= self.amount_to_lp
        if can_lp and not has_lp:
            self.action_list.append(self.create_agent_action(action_type="add_liquidity", trade_amount=self.amount_to_lp))
        return action_list

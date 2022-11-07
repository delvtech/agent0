"""
dynamic shorts
can have multiple longs open at a time
"""


from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    User policy
    """
    def action(self):
        """
        specify action
        """
        action_list = []
        mint_times = list(self.budget.keys()).pop("base")
        have_position = len(mint_times) == 1
        fixed_rate = self.market.pool_apy()
        variable_rate = self.market.vault_apy
        can_open_short = self.get_max_short(self.market) > 10
        if fixed_rate < variable_rate and not have_position and can_open_short:
            action_list.append(["open_short", 10])
        elif fixed_rate > variable_rate and have_position:
            action_list.append(["close_short", mint_times[0], 10])
        return action_list # empty list implies no action

"""
dynamic long
has multiple longs open at once
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
        mint_times = list(self.wallet.keys()).pop("base")
        have_position = len(mint_times) == 1
        fixed_rate = self.market.pool_apy()
        variable_rate = self.market.vault_apy
        if fixed_rate > variable_rate and not have_position:
            action_list.append(["open_long", 10])
        elif fixed_rate < variable_rate and have_position:
            action_list.append(["close_long", 10, mint_times[0]])
        return action_list # empty list implies no action

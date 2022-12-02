"""
Special reserved user strategy that is used to initialize a market with a desired amount of share & bond reserves
"""
# pylint: disable=duplicate-code
# pylint: disable=too-many-arguments

from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(
        self, market, rng, wallet_address, budget=1000, amount_to_lp=100, pt_to_short=100, short_until_apr=0.05
    ):
        """call basic policy init then add custom stuff"""
        self.amount_to_lp = amount_to_lp
        self.pt_to_short = pt_to_short
        self.short_until_apr = short_until_apr
        super().__init__(
            market=market,
            rng=rng,
            wallet_address=wallet_address,
            budget=budget,
        )

    def action(self):
        """
        implement user strategy
        LP if you can, but only do it once
        short if you can, but only do it once
        """
        has_lp = self.wallet.lp_in_wallet > 0
        if has_lp:
            action_list = []
        else:
            action_list = [
                self.create_agent_action(action_type="add_liquidity", trade_amount=self.amount_to_lp),
                self.create_agent_action(action_type="open_short", trade_amount=self.pt_to_short),
            ]
        return action_list

# pylint: disable=duplicate-code

from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple long
    only has one long open at a time
    """

    def __init__(self, market, rng, wallet_address, budget=1000, verbose=None, amount_to_trade=100):
        """call basic policy init then add custom stuff"""
        self.amount_to_trade = amount_to_trade
        self.is_LP = False
        self.is_shorter = True
        super().__init__(
            market=market,
            rng=rng,
            wallet_address=wallet_address,
            budget=budget,
            verbose=verbose,
        )

    def action(self):
        """Specify action"""
        self.can_open_long = self.wallet.base_in_wallet >= self.amount_to_trade
        self.has_opened_long = bool(any([x < 0 for x in self.position_list]))
        action_list = []
        mint_times = list(self.wallet["token_in_wallet"].keys())
        if self.has_opened_long:
            mint_time = mint_times[-1]
            enough_time_has_passed = self.market.time - mint_time > 0.25
            if enough_time_has_passed:
                action_list.append(
                    self.create_agent_action(
                        action_type="close_long",
                        trade_amount=sum(self.position_list) / (self.market.spot_price * 0.99),  # assume 1% slippage
                        mint_time=mint_time,
                        market=self.market,
                    )
                )
        elif (not self.has_opened_long) and self.can_open_long:
            action_list.append(self.create_agent_action(action_type="open_long", trade_amount=self.amount_to_trade))
        return action_list

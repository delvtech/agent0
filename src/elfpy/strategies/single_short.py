from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple short
    only has one long open at a time
    """

    def __init__(self, market, rng, wallet_address, verbose=None, budget=1000, amount_to_trade=100):
        """call basic policy init then add custom stuff"""
        super.__init__(market, rng, wallet_address, verbose=verbose, budget=budget, amount_to_trade=amount_to_trade)

    def action(self):
        """specify action"""
        action_list = []
        if self.has_opened_short:
            mint_time = self.mint_times[-1]
            enough_time_has_passed = self.market.time - mint_time > 0.25
            if enough_time_has_passed:
                action_list.append(
                    self.create_agent_action(
                        action_type="close_short",
                        trade_amount=self.wallet["token_in_wallet"][mint_time],
                        mint_time=mint_time,
                        market=self.market,
                    )
                )
        elif (not self.has_opened_short) and self.can_open_short:
            action_list.append(self.create_agent_action(action_type="open_short", trade_amount=self.amount_to_trade))
        return action_list

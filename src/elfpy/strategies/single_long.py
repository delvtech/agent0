"""
User strategy that opens a long position and then closes it after a certain amount of time has passed
"""
# pylint: disable=too-many-arguments

from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple long
    only has one long open at a time
    """

    def __init__(self, market, rng, wallet_address, budget=1000, verbose=None):
        """call basic policy init then add custom stuff"""
        self.amount_to_trade = 100
        super().__init__(
            market=market,
            rng=rng,
            wallet_address=wallet_address,
            budget=budget,
            verbose=verbose,
        )

    def action(self):
        """Specify action"""
        can_open_long = (self.wallet.base_in_wallet >= self.amount_to_trade) and (
            self.market.share_reserves >= self.amount_to_trade
        )
        block_position_list = list(self.wallet.token_in_protocol.values())
        has_opened_long = bool(any((x < 0 for x in block_position_list)))
        action_list = []
        mint_times = list(self.wallet["token_in_wallet"].keys())
        if has_opened_long:
            mint_time = mint_times[-1]
            enough_time_has_passed = self.market.time - mint_time > 0.25
            if enough_time_has_passed:
                action_list.append(
                    self.create_agent_action(
                        action_type="close_long",
                        trade_amount=sum(block_position_list) / (self.market.spot_price * 0.99),  # assume 1% slippage
                        mint_time=mint_time,
                    )
                )
        elif (not has_opened_long) and can_open_long:
            action_list.append(self.create_agent_action(action_type="open_long", trade_amount=self.amount_to_trade))
        return action_list

from elfpy.strategies.basic import BasicPolicy
from elfpy.utils.bcolors import bcolors


class Policy(BasicPolicy):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(self, market, rng, wallet_address, budget=1000, amount_to_trade=100, verbose=False):
        """call basic policy init then add custom stuff"""
        super().__init__(market=market, rng=rng, wallet_address=wallet_address, budget=budget, verbose=verbose)
        self.amount_to_trade = amount_to_trade
        self.status_update()

    def action(self):
        """
        implement user strategy
        LP if you can, but only do it once
        """
        self.status_update()
        action_list = []
        if not self.has_LPd and self.can_LP:
            action_list.append(
                self.create_user_action(
                    action_type="add_liquidity",
                    trade_amount=self.amount_to_trade
                )
            )
        return action_list

    def liquidate(self):
        """close up shop"""
        self.status_update()
        action_list = []
        if self.has_LPd:
            action_list.append(self.create_user_action(
                    action_type="remove_liquidity",
                    trade_amount=self.wallet.lp_in_wallet
            ))
        return action_list

    def status_update(self):
        self.has_LPd = self.wallet["lp_in_wallet"] > 0
        self.can_LP = self.wallet["base_in_wallet"] >= self.amount_to_trade

    def status_report(self):
        return (
            f"🤖 {bcolors.FAIL}{self.wallet_address}{bcolors.ENDC} has_LPd: {self.has_LPd}, can_LP: {self.can_LP}"
            + f" base_in_wallet: {bcolors.OKBLUE}{self.wallet['base_in_wallet']}{bcolors.ENDC}"
            + f" LP_position: {bcolors.OKCYAN}{self.wallet['lp_in_wallet']}{bcolors.ENDC}"
        )

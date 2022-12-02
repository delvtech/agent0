"""
Implements abstract classes that control agent behavior
"""

import logging

import numpy as np
from numpy.random._generator import Generator

from elfpy.markets import Market, MarketAction, MarketActionType
from elfpy.utils.outputs import float_to_string
from elfpy.utils.bcolors import Bcolors as bcolors
from elfpy.wallet import Wallet

# TODO: this will get fixed soon when verbose is removed due to better logging, revisit this lint
# pylint: disable=too-many-instance-attributes
class Agent:
    """
    Implements a class that controls agent behavior agent has a budget that is a dict, keyed with a
    date value is an inte with how many tokens they have for that date
    """

    # pylint: disable=too-many-arguments
    def __init__(self, market: Market, rng: Generator, wallet_address: int, budget: float):
        """
        Set up initial conditions
        """
        self.market: Market = market
        self.rng: Generator = rng
        # TODO: remove this, wallet_address is a property of wallet, not the agent
        self.wallet_address: int = wallet_address
        self.budget: float = budget
        self.last_update_spend: float = 0  # timestamp
        self.product_of_time_and_base: float = 0
        self.wallet: Wallet = Wallet(address=wallet_address, base_in_wallet=budget)

    def create_agent_action(
        self, action_type: MarketActionType, trade_amount: float, mint_time: float = 0
    ) -> MarketAction:
        """Instantiate a agent action"""
        agent_action = MarketAction(
            # these two variables are required to be set by the strategy
            action_type=action_type,
            trade_amount=trade_amount,
            # next two variables are set automatically by the basic agent class
            wallet_address=self.wallet_address,
            mint_time=mint_time,
        )
        return agent_action

    def action(self) -> list[MarketAction]:
        """Specify action from the policy"""
        raise NotImplementedError

    def get_max_long(self) -> float:
        """Returns the amount of base that the agent can spend."""
        return np.minimum(self.wallet.base_in_wallet, self.market.bond_reserves)

    # TODO: Fix up this function
    def get_max_pt_short(self) -> float:
        """
        Returns an approximation of maximum amount of base that the agent can short given current market conditions

        TODO: This currently is a first-order approximation.
        An alternative is to do this iteratively and find a max trade, but that is probably too slow.
        Maybe we could add an optional flag to iteratively solve it, like num_iters.
        """
        if self.market.share_reserves == 0:
            return 0
        max_pt_short = self.market.share_reserves * self.market.share_price / self.market.spot_price
        return max_pt_short

    def get_trade_list(self):
        """
        Helper function for computing a agent trade
        direction is chosen based on this logic:
        when entering a trade (open long or short),
        we use calcOutGivenIn because we know how much we want to spend,
        and care less about how much we get for it.
        when exiting a trade (close long or short),
        we use calcInGivenOut because we know how much we want to get,
        and care less about how much we have to spend.
        we spend what we have to spend, and get what we get.
        """
        action_list = self.action()  # get the action list from the policy
        for action in action_list:  # edit each action in place
            if action.mint_time is None:
                action.mint_time = self.market.time
        # TODO: Add safety checks
        # e.g. if trade amount > 0, whether there is enough money in the account
        # if len(trade_action) > 0: # there is a trade
        #    token_in, token_out, trade_amount_usd = trade_action
        #    assert trade_amount_usd >= 0, (
        #        f"agent.py: ERROR: Trade amount should not be negative, but is {trade_amount_usd}"
        #        f" token_in={token_in} token_out={token_out}"
        #    )
        return action_list

    def update_spend(self) -> None:
        """Track over time the agent's weighted average spend, for return calculation"""
        new_spend = (self.market.time - self.last_update_spend) * (self.budget - self.wallet["base_in_wallet"])
        self.product_of_time_and_base += new_spend
        self.last_update_spend = self.market.time

    def update_wallet(self, wallet_deltas: Wallet) -> None:
        """Update the agent's wallet"""
        self.update_spend()
        for key, value_or_dict in wallet_deltas.__dict__.items():
            if value_or_dict is None:
                pass
            # handle updating a value
            if key in ["base_in_wallet", "lp_in_wallet", "fees_paid"]:
                if value_or_dict != 0 or self.wallet[key] != 0:
                    logging.debug("pre-trade %17s = %.0g", key, self.wallet[key])
                self.wallet[key] += value_or_dict
                if value_or_dict != 0 or self.wallet[key] != 0:
                    logging.debug("post-trade %17s = %1g", key, self.wallet[key])
                    logging.debug("delta = %1g", value_or_dict)
            # handle updating a dict, which have mint_time attached
            elif key in ["base_in_protocol", "token_in_wallet", "token_in_protocol"]:
                for mint_time, amount in value_or_dict.items():
                    logging.debug("pre-trade %17s = %s", key, self.wallet[key])
                    if mint_time in self.wallet[key]:  #  entry already exists for this mint_time, so add to it
                        self.wallet[key][mint_time] += amount
                    else:
                        self.wallet[key].update({mint_time: amount})
                    logging.debug("post-trade %17s = %s", key, self.wallet[key])
            elif key in ["fees_paid", "effective_price"]:
                pass
            elif key in ["address"]:
                pass
            else:
                raise ValueError(f"wallet_key={key} is not allowed.")

    def get_liquidation_trades(self) -> list[MarketAction]:
        """Get final trades for liquidating positions"""
        action_list: list[MarketAction] = []
        for mint_time, position in self.wallet.token_in_protocol.items():
            logging.debug("evaluating closing short: mint_time=%g, position=%d", mint_time, position)
            if position < 0:
                action_list.append(
                    self.create_agent_action(
                        action_type="close_short",
                        trade_amount=-position,
                        mint_time=mint_time,
                    )
                )
        if self.wallet.lp_in_wallet > 0:
            action_list.append(
                self.create_agent_action(
                    action_type="remove_liquidity", trade_amount=self.wallet.lp_in_wallet, mint_time=self.market.time
                )
            )
        return action_list

    def log_status_report(self) -> str:
        """Return user state"""
        logging.debug(
            "%g base_in_wallet = %1g and fees_paid = %1g",
            self.wallet_address,
            self.wallet.base_in_wallet,
            self.wallet.fees_paid if self.wallet.fees_paid else 0,
        )

    def log_final_report(self) -> None:
        """Logs a report of the agent's state"""
        price = self.market.spot_price
        base = self.wallet.base_in_wallet
        block_position_list = list(self.wallet.token_in_protocol.values())
        tokens = sum(block_position_list) if len(block_position_list) > 0 else 0
        worth = base + tokens * price
        profit_and_loss = worth - self.budget
        weighted_average_spend = self.product_of_time_and_base / self.market.time if self.market.time > 0 else 0
        spend = weighted_average_spend
        holding_period_rate = profit_and_loss / spend if spend != 0 else 0
        if self.market.time > 0:
            annual_percentage_rate = holding_period_rate / self.market.time
        else:
            annual_percentage_rate = np.nan
        lost_or_made = "lost" if profit_and_loss < 0 else "made"
        logging.info(
            (
                "%g %s %s on $%s spent, APR = %g"
                " (%.2g in %s years), net worth = $%s"
                " from %s base and %s tokens at p = %g\n"
            ),
            self.wallet_address,
            lost_or_made,
            float_to_string(profit_and_loss),
            float_to_string(spend),
            annual_percentage_rate,
            holding_period_rate,
            float_to_string(self.market.time, precision=2),
            float_to_string(worth),
            float_to_string(base),
            float_to_string(tokens),
            price,
        )

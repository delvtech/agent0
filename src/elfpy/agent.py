"""
Implements abstract classes that control agent behavior
"""

import logging
import numpy as np

import elfpy.utils.time as time_utils
from elfpy.markets import Market
from elfpy.pricing_models.base import PricingModel
from elfpy.types import MarketAction, MarketActionType
from elfpy.wallet import Wallet


class Agent:
    """
    Implements a class that controls agent behavior agent has a budget that is a dict, keyed with a
    date value is an inte with how many tokens they have for that date
    """

    def __init__(self, market: Market, rng: Generator, wallet_address: int, budget: float = 1000, **kwargs):
        """
        Set up initial conditions
        """
        # TODO: remove this, wallet_address is a property of wallet, not the agent
        self.wallet_address: int = wallet_address
        self.budget: float = budget
        self.last_update_spend: float = 0  # timestamp
        self.product_of_time_and_base: float = 0
        self.wallet: Wallet = Wallet(address=wallet_address, base=budget)
        for key, value in kwargs.items():
            if value and hasattr(self, key):
                logging.info("setting agent's %s to %s", key, str(value))
                setattr(self, key, value)

    def create_agent_action(
        self, action_type: MarketActionType, trade_amount: float, mint_time: float = None
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

    def action(self, market: Market, pricing_model: PricingModel) -> list[MarketAction]:
        """Specify action from the policy"""
        raise NotImplementedError

    # TODO: Fix up this function
    def get_max_pt_short(self, market: Market, pricing_model: PricingModel) -> float:
        """
        Returns an approximation of maximum amount of base that the agent can short given current market conditions

        TODO: This currently is a first-order approximation.
        An alternative is to do this iteratively and find a max trade, but that is probably too slow.
        Maybe we could add an optional flag to iteratively solve it, like num_iters.
        """
        if market.market_state.share_reserves == 0:
            return 0
        time_remaining = time_utils.get_yearfrac_remaining(market.time, market.time, market.token_duration)
        stretched_time_remaining = time_utils.stretch_time(time_remaining, market.time_stretch_constant)
        trade_results = pricing_model.calc_in_given_out(
            market.share_reserves,
            market.share_reserves,
            market.bond_reserves,
            "pt",
            market.fee_percent,
            stretched_time_remaining,
            market.init_share_price,
            market.share_price,
        )
        output_with_fee = trade_results[1]
        return output_with_fee

    def get_trade_list(self, market: Market, pricing_model: PricingModel) -> list:
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
        action_list = self.action(market, pricing_model)  # get the action list from the policy
        # TODO: is this the right place to modify an action's mint_time? why not in __post_init__?
        for action in action_list:  # edit each action in place
            if action.mint_time is None:
                action.mint_time = market.time
        # TODO: Add safety checks
        # e.g. if trade amount > 0, whether there is enough money in the account
        # if len(trade_action) > 0: # there is a trade
        #    token_in, token_out, trade_amount_usd = trade_action
        #    assert trade_amount_usd >= 0, (
        #        f"agent.py: ERROR: Trade amount should not be negative, but is {trade_amount_usd}"
        #        f" token_in={token_in} token_out={token_out}"
        #    )
        return action_list

    def update_wallet(self, wallet_deltas: Wallet, market: Market) -> None:
        """Update the agent's wallet"""
        # track over time the agent's weighted average spend, for return calculation
        new_spend = (market.time - self.last_update_spend) * (self.budget - self.wallet["base"])
        self.product_of_time_and_base += new_spend
        self.last_update_spend = market.time
        for key, value_or_dict in wallet_deltas.__dict__.items():
            if value_or_dict is None:
                pass
            # handle updating a value
            if key in ["base", "lp_tokens"]:
                if value_or_dict != 0 or self.wallet[key] != 0:
                    logging.info(
                        "agent #%03.0f %s pre-trade = %.0g\npost-trade = %1g\ndelta = %1g",
                        self.wallet_address,
                        key,
                        self.wallet[key],
                        self.wallet[key] + value_or_dict,
                        value_or_dict,
                    )
                self.wallet[key] += value_or_dict
            # handle updating a dict, which have mint_time attached
            elif key in ["margin", "longs", "shorts"]:
                for mint_time, amount in value_or_dict.items():
                    logging.info(
                        "agent #%03.0f trade %s, mint_time = %g\npre-trade amount = %s\ntrade delta = %s",
                        self.wallet_address,
                        key,
                        mint_time,
                        self.wallet[key],
                        amount,
                    )
                    if mint_time in self.wallet[key]:  #  entry already exists for this mint_time, so add to it
                        self.wallet[key][mint_time] += amount
                    else:
                        self.wallet[key].update({mint_time: amount})
            elif key in ["address"]:
                pass
            else:
                raise ValueError(f"wallet_key={key} is not allowed.")

    def get_liquidation_trades(self, market: Market) -> list[MarketAction]:
        """Get final trades for liquidating positions"""
        action_list: list[MarketAction] = []
        for mint_time, position in self.wallet.shorts.items():
            logging.debug("evaluating closing short: mint_time=%g, position=%d", mint_time, position)
            if position < 0:
                action_list.append(
                    self.create_agent_action(
                        action_type=MarketActionType.CLOSE_SHORT,
                        trade_amount=-position,
                        mint_time=mint_time,
                    )
                )
        if self.wallet.lp_tokens > 0:
            action_list.append(
                self.create_agent_action(
                    action_type=MarketActionType.REMOVE_LIQUIDITY,
                    trade_amount=self.wallet.lp_tokens,
                    mint_time=market.time,
                )
            )
        return action_list

    def log_status_report(self) -> None:
        """Logs the current user state"""
        logging.info(
            "agent #%03.0f base = %s",
            self.wallet_address,
            self.wallet.base,
        )

    def log_final_report(self, market: Market, pricing_model: PricingModel) -> None:
        """Logs a report of the agent's state"""
        # TODO: This is a HACK to prevent test_sim from failing on market shutdown
        # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
        if market.market_state.share_reserves > 0:
            price = market.get_spot_price(pricing_model)
        else:
            price = 0
        base = self.wallet.base
        block_position_list = list(self.wallet.shorts.values())
        tokens = sum(block_position_list) if len(block_position_list) > 0 else 0
        worth = base + tokens * price
        profit_and_loss = worth - self.budget
        weighted_average_spend = self.product_of_time_and_base / market.time if market.time > 0 else 0
        spend = weighted_average_spend
        holding_period_rate = profit_and_loss / spend if spend != 0 else 0
        if market.time > 0:
            annual_percentage_rate = holding_period_rate / market.time
        else:
            annual_percentage_rate = np.nan
        lost_or_made = "lost" if profit_and_loss < 0 else "made"
        logging.info(
            (
                "agent #%03.0f %s %s on $%s spent, APR = %g (%.2g in %s years), "
                "net worth = $%s from %s base and %s tokens at p = %g\n"
            ),
            self.wallet_address,
            lost_or_made,
            profit_and_loss,
            spend,
            annual_percentage_rate,
            holding_period_rate,
            market.time,
            worth,
            base,
            tokens,
            price,
        )

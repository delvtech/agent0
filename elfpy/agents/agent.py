"""Implements abstract classes that control agent behavior"""
from __future__ import annotations  # types will be strings by default in 3.11

import logging
from typing import TYPE_CHECKING

import elfpy.agents.wallet as wallet
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.types as types
from elfpy.math import FixedPoint, FixedPointMath

if TYPE_CHECKING:
    import elfpy.markets.base as base_market
    import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market


class Agent:
    r"""Agent class for conducting trades on the market

    Implements a class that controls agent behavior agent has a budget that is a dict, keyed with a
    date value is an inte with how many tokens they have for that date.

    Arguments
    ----------
    wallet_address : int
        Random ID used to identify this specific agent in the simulation
    budget : FixedPoint
        Amount of assets that this agent has available for spending in the simulation
    """

    def __init__(self, wallet_address: int, budget: FixedPoint):
        """Set up initial conditions"""
        if not isinstance(budget, FixedPoint):
            raise TypeError(f"{budget=} must be of type `FixedPoint`")
        self.budget: FixedPoint = budget
        self.wallet: wallet.WalletFP = wallet.WalletFP(
            address=wallet_address, balance=types.QuantityFP(amount=budget, unit=types.TokenType.BASE)
        )
        # TODO: We need to fix this up -- probably just have the user specify a name on init
        # (i.e. attribute without default)
        name = str(self.__class__)
        if "Policy" in name:  # agent was instantiated from policy folder
            self.name = name.split(".")[-2]
        else:  # agent was built in the namespace (e.g. a jupyter notebook)
            self.name = name.rsplit(".", maxsplit=1)[-1].split("'")[0]

    def action(self, market: base_market.Market) -> list[types.Trade]:
        r"""Abstract method meant to be implemented by the specific policy

        Specify action from the policy

        Arguments
        ----------
        market : Market
            The market on which this agent will be executing trades (MarketActions)

        Returns
        -------
        list[Trade]
            List of actions to execute in the market
        """
        raise NotImplementedError

    # TODO: this function should optionally accept a target apr.  the short should not slip the
    # market fixed rate below the APR when opening the long
    # issue #213
    def get_max_long(self, market: hyperdrive_market.Market) -> FixedPoint:
        """Gets an approximation of the maximum amount of base the agent can use

        Typically would be called to determine how much to enter into a long position.

        Arguments
        ----------
        market : Market
            The market on which this agent will be executing trades (MarketActions)

        Returns
        -------
        FixedPoint
            Maximum amount the agent can use to open a long
        """
        (max_long, _) = market.pricing_model.get_max_long(
            market_state=market.market_state,
            time_remaining=market.position_duration,
        )
        return FixedPointMath.minimum(
            self.wallet.balance.amount,
            max_long,
        )

    # TODO: this function should optionally accept a target apr.  the short should not slip the
    # market fixed rate above the APR when opening the short
    # issue #213
    def get_max_short(self, market: hyperdrive_market.Market) -> FixedPoint:
        """Gets an approximation of the maximum amount of bonds the agent can short.

        Arguments
        ----------
        market : Market
            The market on which this agent will be executing trades (MarketActions)

        Returns
        -------
        FixedPoint
            Amount of base that the agent can short in the current market
        """
        # Get the market level max short.
        (max_short_max_loss, max_short) = market.pricing_model.get_max_short(
            market_state=market.market_state,
            time_remaining=market.position_duration,
        )
        # If the Agent's base balance can cover the max loss of the maximum
        # short, we can simply return the maximum short.
        if self.wallet.balance.amount >= max_short_max_loss:
            return max_short
        last_maybe_max_short = FixedPoint(0)
        bond_percent = FixedPoint("1.0")
        num_iters = 25
        for step_size in [FixedPoint(f"{1 / (2 ** (x + 1)):.19f}") for x in range(num_iters)]:
            # Compute the amount of base returned by selling the specified
            # amount of bonds.
            maybe_max_short = max_short * bond_percent
            trade_result = market.pricing_model.calc_out_given_in(
                in_=types.QuantityFP(amount=maybe_max_short, unit=types.TokenType.PT),
                market_state=market.market_state,
                time_remaining=market.position_duration,
            )
            # If the max loss is greater than the wallet's base, we need to
            # decrease the bond percentage. Otherwise, we may have found the
            # max short, and we should increase the bond percentage.
            max_loss = maybe_max_short - trade_result.user_result.d_base
            if max_loss > self.wallet.balance.amount:
                bond_percent -= step_size
            else:
                last_maybe_max_short = maybe_max_short
                if bond_percent == FixedPoint("1.0"):
                    return last_maybe_max_short
                bond_percent += step_size
        # do one more iteration at the last step size in case the bisection method was stuck
        # approaching a max_short value with slightly more base than an agent has.
        trade_result = market.pricing_model.calc_out_given_in(
            in_=types.QuantityFP(amount=last_maybe_max_short, unit=types.TokenType.PT),
            market_state=market.market_state,
            time_remaining=market.position_duration,
        )
        max_loss = last_maybe_max_short - trade_result.user_result.d_base
        last_step_size = FixedPoint("1.0") / (FixedPoint("2.0") ** FixedPoint(float(num_iters)) + FixedPoint("1.0"))
        if max_loss > self.wallet.balance.amount:
            bond_percent -= last_step_size
            last_maybe_max_short = max_short * bond_percent
        return last_maybe_max_short

    def get_trades(self, market: base_market.Market) -> list[types.Trade]:
        """Helper function for computing a agent trade

        direction is chosen based on this logic:

            * When entering a trade (open long or short),
            we use calcOutGivenIn because we know how much we want to spend,
            and care less about how much we get for it.

            * When exiting a trade (close long or short),
            we use calcInGivenOut because we know how much we want to get,
            and care less about how much we have to spend.

        Arguments
        ----------
        market : Market
            The market on which this agent will be executing trades (MarketActions)
        pricing_model : PricingModel
            The pricing model in use for this simulated market

        Returns
        -------
        list[Trade]
            List of Trade type objects that represent the trades to be made by this agent
        """
        actions = self.action(market)  # get the action list from the policy
        for action in actions:  # edit each action in place
            if action.market == types.MarketType.HYPERDRIVE and action.trade.mint_time is None:
                action.trade.mint_time = market.latest_checkpoint_time
        # TODO: Add safety checks
        # e.g. if trade amount > 0, whether there is enough money in the account
        # agent wallet Long and Short balances should not be able to be negative
        # issue #57
        return actions

    def get_liquidation_trades(self, market: hyperdrive_market.Market) -> list[types.Trade]:
        """Get final trades for liquidating positions

        Arguments
        ----------
        market : Market
            The market on which this agent will be executing trades or liquidations (MarketActions)

        Returns
        -------
        list[Trade]
            List of trades to execute in order to liquidate positions where applicable
        """
        action_list = []
        for mint_time, long in self.wallet.longs.items():
            logging.debug("evaluating closing long: mint_time=%g, position=%s", float(mint_time), long)
            if long.balance > FixedPoint(0):
                # TODO: Find a way to avoid converting type back and forth for dict keys
                action_list.append(
                    types.Trade(
                        market=types.MarketType.HYPERDRIVE,
                        trade=hyperdrive_actions.MarketAction(
                            action_type=hyperdrive_actions.MarketActionType.CLOSE_LONG,
                            trade_amount=long.balance,
                            wallet=self.wallet,
                            mint_time=mint_time,
                        ),
                    )
                )
        for mint_time, short in self.wallet.shorts.items():
            logging.debug("evaluating closing short: mint_time=%g, position=%s", float(mint_time), short)
            if short.balance > FixedPoint(0):
                action_list.append(
                    types.Trade(
                        market=types.MarketType.HYPERDRIVE,
                        trade=hyperdrive_actions.MarketAction(
                            action_type=hyperdrive_actions.MarketActionType.CLOSE_SHORT,
                            trade_amount=short.balance,
                            wallet=self.wallet,
                            mint_time=mint_time,
                        ),
                    )
                )
        if self.wallet.lp_tokens > FixedPoint(0):
            logging.debug(
                "evaluating closing lp: mint_time=%g, position=%s", float(market.block_time.time), self.wallet.lp_tokens
            )
            action_list.append(
                types.Trade(
                    market=types.MarketType.HYPERDRIVE,
                    trade=hyperdrive_actions.MarketAction(
                        action_type=hyperdrive_actions.MarketActionType.REMOVE_LIQUIDITY,
                        trade_amount=self.wallet.lp_tokens,
                        wallet=self.wallet,
                        mint_time=market.block_time.time,
                    ),
                )
            )
        return action_list

    def log_status_report(self) -> None:
        """Logs the current user state"""
        logging.debug(
            "agent #%g balance = %1g and fees_paid = %1g",
            int(self.wallet.address),
            float(self.wallet.balance.amount),
            float(self.wallet.fees_paid) or 0,
        )

    def log_final_report(self, market: hyperdrive_market.Market) -> None:
        """Logs a report of the agent's state

        Arguments
        ----------
        market : Market
            The market on which this agent can execute trades (MarketActions)
        """
        # TODO: This is a HACK to prevent test_sim from failing on market shutdown
        # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
        price = market.spot_price if market.market_state.share_reserves > FixedPoint(0) else FixedPoint(0)
        balance = self.wallet.balance.amount
        longs = list(self.wallet.longs.values())
        shorts = list(self.wallet.shorts.values())
        # Calculate the total pnl of the trader.
        longs_value = (FixedPoint(sum(float(long.balance) for long in longs)) if longs else FixedPoint(0)) * price
        shorts_value = (
            FixedPoint(
                sum(
                    # take the interest from the margin and subtract the bonds shorted at the current price
                    float(
                        (market.market_state.share_price / short.open_share_price) * short.balance
                        - price * short.balance
                    )
                    for short in shorts
                )
            )
            if shorts
            else FixedPoint(0)
        )
        total_value = balance + longs_value + shorts_value
        profit_and_loss = total_value - self.budget
        # Log the trading report.
        lost_or_made = "lost" if profit_and_loss < FixedPoint(0) else "made"
        logging.info(
            ("agent #%g %s %s (%s years), net worth = $%s from %s balance, %s longs, and %s shorts at p = %g\n"),
            float(self.wallet.address),
            lost_or_made,
            float(profit_and_loss),
            float(market.block_time.time),
            float(total_value),
            float(balance),
            sum((float(long.balance) for long in longs)),
            sum((float(short.balance) for short in shorts)),
            float(price),
        )

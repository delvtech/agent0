"""Implements abstract classes that control agent behavior"""
from __future__ import annotations  # types will be strings by default in 3.11

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict
import logging

import numpy as np

import elfpy.agents.wallet as wallet
import elfpy.markets.base as base
import elfpy.types as types

if TYPE_CHECKING:
    from typing import Iterable


MarketsByName = Dict[types.MarketType, base.Market]


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class AgentTradeResult:
    r"""The result to a user of performing a trade"""

    d_base: float
    d_bonds: float


class Agent:
    r"""Agent class for conducting trades on the market

    Implements a class that controls agent behavior agent has a budget that is a dict, keyed with a
    date value is an inte with how many tokens they have for that date.

    Attributes
    ----------
    market : elfpy.markets.Market
        Market object that this Agent will be trading on.
    rng : numpy.random._generator.Generator
        Random number generator used for various simulation functions
    wallet_address : int
        Random ID used to identify this specific agent in the simulation
    budget : float
        Amount of assets that this agent has available for spending in the simulation
    last_update_spend : float
        Time relative to the market, in years, when this agent last made a trade. This is used to track PnL
    product_of_time_and_base : float
        Helper attribute used to track how an agent spends their assets over time
    wallet : elfpy.wallet.Wallet
        Wallet object which tracks the agent's asset balances
    """

    def __init__(self, wallet_address: int, budget: float):
        """Set up initial conditions"""
        self.budget: float = budget
        self.last_update_spend: float = 0  # timestamp
        self.product_of_time_and_base: float = 0
        self.wallet: wallet.Wallet = wallet.Wallet(
            address=wallet_address, balance=types.Quantity(amount=budget, unit=types.TokenType.BASE)
        )
        # TODO: We need to fix this up -- probably just have the user specify a name on init
        # (i.e. attribute without default)
        name = str(self.__class__)
        if "Policy" in name:  # agent was instantiated from policy folder
            self.name = name.split(".")[-2]
        else:  # agent was built in the namespace (e.g. a jupyter notebook)
            self.name = name.rsplit(".", maxsplit=1)[-1].split("'")[0]

    def action(self, markets: "dict[types.MarketType, base.Market]") -> "list[types.Trade]":
        r"""Abstract method meant to be implemented by the specific policy

        Specify action from the policy

        Parameters
        ----------
        market : Market
            The market on which this agent will be executing trades (MarketActions)

        Returns
        -------
        list[Trade]
            List of actions to execute in the market
        """
        raise NotImplementedError

    def get_trades(self, markets: dict[types.MarketType, base.Market]) -> "list[types.Trade]":
        """Helper function for computing a agent trade

        direction is chosen based on this logic:
            when entering a trade (open long or short),
            we use calcOutGivenIn because we know how much we want to spend,
            and care less about how much we get for it.
            when exiting a trade (close long or short),
            we use calcInGivenOut because we know how much we want to get,
            and care less about how much we have to spend.
            we spend what we have to spend, and get what we get.

        Parameters
        ----------
        market : dict[str, Market]
            The market on which this agent will be executing trades {MarktType: MarketActions}
        pricing_model : PricingModel
            The pricing model in use for this simulated market

        Returns
        -------
        list[Trade]
            List of Trade type objects that represent the trades to be made by this agent
        """
        market_actions = self.action(markets)  # get the action list from the policy
        for action in market_actions:  # edit each action in place
            if action.trade.mint_time is None:
                action.trade.mint_time = markets[0].time  # should be global
        # TODO: Add safety checks
        # e.g. if trade amount > 0, whether there is enough money in the account
        # agent wallet Long and Short balances should not be able to be negative
        # issue #57
        return market_actions

    def update_wallet(self, wallet_deltas: wallet.Wallet, time: float) -> None:
        """Update the agent's wallet

        Parameters
        ----------
        wallet_deltas : Wallet
            The agent's wallet that tracks the amount of assets this agent holds
        market : Market
            The market on which this agent will be executing trades (MarketActions)

        Returns
        -------
        This method has no returns. It updates the Agent's Wallet according to the passed parameters
        """
        # track over time the agent's weighted average spend, for return calculation
        new_spend = (time - self.last_update_spend) * (self.budget - self.wallet.balance.amount)
        self.product_of_time_and_base += new_spend
        self.last_update_spend = time
        for key, value_or_dict in wallet_deltas.__dict__.items():
            if value_or_dict is None:
                continue
            if key in ["fees_paid", "address", "borrows"]:
                continue
            # handle updating a value
            if key in ["lp_tokens", "fees_paid"]:
                logging.debug(
                    "agent #%g %s pre-trade = %.0g\npost-trade = %1g\ndelta = %1g",
                    self.wallet.address,
                    key,
                    self.wallet[key],
                    self.wallet[key] + value_or_dict,
                    value_or_dict,
                )
                self.wallet[key] += value_or_dict
            # handle updating a Quantity
            elif key == "balance":
                logging.debug(
                    "agent #%g %s pre-trade = %.0g\npost-trade = %1g\ndelta = %1g",
                    self.wallet.address,
                    key,
                    self.wallet[key].amount,
                    self.wallet[key].amount + value_or_dict.amount,
                    value_or_dict,
                )
                self.wallet[key].amount += value_or_dict.amount
            # handle updating a dict, which have mint_time attached
            elif key == "longs":
                self._update_longs(value_or_dict.items())
            elif key == "shorts":
                self._update_shorts(value_or_dict.items())
            else:
                raise ValueError(f"wallet_key={key} is not allowed.")

    def _update_longs(self, longs: Iterable[tuple[float, wallet.Long]]) -> None:
        """Helper internal function that updates the data about Longs contained in the Agent's Wallet object

        Parameters
        ----------
        shorts : Iterable[tuple[float, Short]]
            A list (or other Iterable type) of tuples that contain a Long object
            and its market-relative mint time
        """
        for mint_time, long in longs:
            if long.balance != 0:
                logging.debug(
                    "agent #%g trade longs, mint_time = %g\npre-trade amount = %s\ntrade delta = %s",
                    self.wallet.address,
                    mint_time,
                    self.wallet.longs,
                    long,
                )
                if mint_time in self.wallet.longs:  #  entry already exists for this mint_time, so add to it
                    self.wallet.longs[mint_time].balance += long.balance
                else:
                    self.wallet.longs.update({mint_time: long})
            if self.wallet.longs[mint_time].balance == 0:
                # Remove the empty long from the wallet.
                del self.wallet.longs[mint_time]

    def _update_shorts(self, shorts: Iterable[tuple[float, wallet.Short]]) -> None:
        """Helper internal function that updates the data about Shortscontained in the Agent's Wallet object

        Parameters
        ----------
        shorts : Iterable[tuple[float, Short]]
            A list (or other Iterable type) of tuples that contain a Short object
            and its market-relative mint time
        """
        for mint_time, short in shorts:
            if short.balance != 0:
                logging.debug(
                    "agent #%g trade shorts, mint_time = %g\npre-trade amount = %s\ntrade delta = %s",
                    self.wallet.address,
                    mint_time,
                    self.wallet.shorts,
                    short,
                )
                if mint_time in self.wallet.shorts:  #  entry already exists for this mint_time, so add to it
                    self.wallet.shorts[mint_time].balance += short.balance
                    old_balance = self.wallet.shorts[mint_time].balance
                    # if the balance is positive, we are opening a short, therefore do a weighted
                    # mean for the open share price.  this covers an edge case where two shorts are
                    # opened for the same account in the same block.  if the balance is negative, we
                    # don't want to update the open_short_price
                    if short.balance > 0:
                        old_share_price = self.wallet.shorts[mint_time].open_share_price
                        self.wallet.shorts[mint_time].open_share_price = (
                            short.open_share_price * short.balance + old_share_price * old_balance
                        ) / (short.balance + old_balance)
                else:
                    self.wallet.shorts.update({mint_time: short})
            if self.wallet.shorts[mint_time].balance == 0:
                # Remove the empty short from the wallet.
                del self.wallet.shorts[mint_time]

    def log_status_report(self) -> None:
        """Logs the current user state"""
        logging.debug(
            "agent #%g balance = %1g and fees_paid = %1g",
            self.wallet.address,
            self.wallet.balance.amount,
            self.wallet.fees_paid or 0,
        )

    def log_final_report(self, market: base.Market) -> None:
        """Logs a report of the agent's state

        Parameters
        ----------
        market : Market
            The market on which this agent can execute trades (MarketActions)
        """
        # TODO: This is a HACK to prevent test_sim from failing on market shutdown
        # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
        price = market.spot_price if market.market_state.share_reserves > 0 else 0
        balance = self.wallet.balance.amount
        longs = list(self.wallet.longs.values())
        shorts = list(self.wallet.shorts.values())

        # Calculate the total pnl of the trader.
        longs_value = (sum(long.balance for long in longs) if longs else 0) * price
        shorts_value = (
            sum(
                # take the interest from the margin and subtract the bonds shorted at the current price
                (market.market_state.share_price / short.open_share_price) * short.balance - price * short.balance
                for short in shorts
            )
            if shorts
            else 0
        )
        total_value = balance + longs_value + shorts_value
        profit_and_loss = total_value - self.budget

        # Calculated spending statistics.
        weighted_average_spend = self.product_of_time_and_base / market.time if market.time > 0 else 0
        spend = weighted_average_spend
        holding_period_rate = profit_and_loss / spend if spend != 0 else 0
        if market.time > 0:
            annual_percentage_rate = holding_period_rate / market.time
        else:
            annual_percentage_rate = np.nan

        # Log the trading report.
        lost_or_made = "lost" if profit_and_loss < 0 else "made"
        logging.info(
            (
                "agent #%g %s %s on $%s spent, APR = %g"
                " (%.2g in %s years), net worth = $%s"
                " from %s balance, %s longs, and %s shorts at p = %g\n"
            ),
            self.wallet.address,
            lost_or_made,
            profit_and_loss,
            spend,
            annual_percentage_rate,
            holding_period_rate,
            market.time,
            total_value,
            balance,
            sum(long.balance for long in longs),
            sum(short.balance for short in shorts),
            price,
        )

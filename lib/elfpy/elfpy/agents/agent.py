"""Implements abstract classes that control agent behavior"""
from __future__ import annotations  # types will be strings by default in 3.11

import logging
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from elfpy.agents.policies import NoActionPolicy
from elfpy.markets.hyperdrive import HyperdriveMarketAction, MarketActionType
from elfpy.types import MarketType, Quantity, TokenType, Trade
from elfpy.wallet.wallet import Wallet

if TYPE_CHECKING:
    from elfpy.agents.policies.base import BasePolicy
    from elfpy.markets.base import BaseMarket
    from elfpy.markets.hyperdrive import HyperdriveMarket


class Agent:
    r"""Agent class for conducting trades on the market

    Implements a class that controls agent behavior agent has a budget that is a dict, keyed with a
    date value is an inte with how many tokens they have for that date.

    Arguments
    ----------
    wallet_address : int
        Random ID used to identify this specific agent in the simulation
    policy : BasePolicy
        Elfpy policy for producing agent actions
    """

    def __init__(self, wallet_address: int, policy: BasePolicy | None = None):
        r"""Store agent wallet & policy"""
        if policy is None:
            self.policy: BasePolicy = NoActionPolicy()
        else:
            self.policy: BasePolicy = policy
        # TODO: wallet_address is no longer unique with the eth_bots setup and therefore
        # needs to be deprecated in favor of a real checksum address
        self.wallet: Wallet = Wallet(
            address=wallet_address, balance=Quantity(amount=self.policy.budget, unit=TokenType.BASE)
        )

    def action(self, market: BaseMarket) -> list[Trade]:
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
        return self.policy.action(market, self.wallet)

    def get_trades(self, market: BaseMarket) -> list[Trade]:
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
        actions: list[Trade] = self.action(market)  # get the action list from the policy
        for action in actions:  # edit each action in place
            if action.market_type == MarketType.HYPERDRIVE and action.market_action.mint_time is None:
                action.market_action.mint_time = market.latest_checkpoint_time
                if action.market_action.trade_amount <= 0:
                    raise ValueError("Trade amount cannot be zero or negative.")
        return actions

    def get_liquidation_trades(self, market: HyperdriveMarket) -> list[Trade]:
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
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=MarketActionType.CLOSE_LONG,
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
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=MarketActionType.CLOSE_SHORT,
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
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=MarketActionType.REMOVE_LIQUIDITY,
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
            "agent #%g balance = %1g",
            int(self.wallet.address),
            float(self.wallet.balance.amount),
        )

    def log_final_report(self, market: HyperdriveMarket) -> None:
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
        profit_and_loss = total_value - self.policy.budget
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

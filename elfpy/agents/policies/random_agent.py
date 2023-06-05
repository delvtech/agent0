"""User strategy that opens or closes a random position with a random allowed amount"""
from __future__ import annotations

from typing import TYPE_CHECKING

from elfpy import WEI
from elfpy.markets.hyperdrive.hyperdrive_actions import HyperdriveMarketAction, MarketActionType
from elfpy.math import FixedPoint
from elfpy.types import MarketType, Trade

from .base import BasePolicy

if TYPE_CHECKING:
    from numpy.random._generator import Generator as NumpyGenerator

    from elfpy.agents.wallet import Wallet
    from elfpy.markets.hyperdrive.hyperdrive_market import HyperdriveMarket


class RandomAgent(BasePolicy):
    """Random agent"""

    def __init__(
        self,
        budget: FixedPoint = FixedPoint("10_000.0"),
        rng: NumpyGenerator | None = None,
        trade_chance: FixedPoint = FixedPoint("1.0"),
    ) -> None:
        """Adds custom attributes"""
        self.trade_chance = trade_chance
        super().__init__(budget, rng)

    def get_available_actions(
        self,
        wallet: Wallet,
        disallowed_actions: list[MarketActionType] | None = None,
    ) -> list[MarketActionType]:
        """Get all available actions, excluding those listed in disallowed_actions"""
        # prevent accidental override
        if disallowed_actions is None:
            disallowed_actions = []
        # compile a list of all actions
        all_available_actions = [
            MarketActionType.OPEN_LONG,
            MarketActionType.OPEN_SHORT,
            MarketActionType.ADD_LIQUIDITY,
        ]
        if wallet.longs:  # if the agent has open longs
            all_available_actions.append(MarketActionType.CLOSE_LONG)
        if wallet.shorts:  # if the agent has open shorts
            all_available_actions.append(MarketActionType.CLOSE_SHORT)
        if wallet.lp_tokens:
            all_available_actions.append(MarketActionType.REMOVE_LIQUIDITY)
        # downselect from all actions to only include allowed actions
        return [action for action in all_available_actions if action not in disallowed_actions]

    def open_short_with_random_amount(self, market: HyperdriveMarket, wallet: Wallet) -> list[Trade]:
        """Open a short with a random allowable amount"""
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(self.budget) * 0.1, scale=float(self.budget) * 0.01)
        )
        # TODO: This is a hack until we fix get_max
        # issue # 440
        # max_short = self.get_max_short(market)
        # if max_short < WEI:  # no short is possible
        #     return []
        maximum_trade_amount_in_bonds = (
            market.market_state.share_reserves * market.market_state.share_price / FixedPoint("2.0")
        )
        # WEI <= trade_amount <= max_short
        trade_amount = max(WEI, min(initial_trade_amount, maximum_trade_amount_in_bonds / FixedPoint("100.0")))
        return [
            Trade(
                market=MarketType.HYPERDRIVE,
                trade=HyperdriveMarketAction(
                    action_type=MarketActionType.OPEN_SHORT,
                    trade_amount=FixedPoint(trade_amount),
                    wallet=wallet,
                ),
            )
        ]

    def open_long_with_random_amount(self, market: HyperdriveMarket, wallet: Wallet) -> list[Trade]:
        """Open a long with a random allowable amount"""
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(self.budget) * 0.1, scale=float(self.budget) * 0.01)
        )
        # TODO: This is a hack until we fix get_max
        # issue # 440
        # # get the maximum amount that can be traded, based on the budget & market reserve levels
        # max_long = self.get_max_long(market)
        # if max_long < WEI:  # no trade is possible
        #     return []
        maximum_trade_amount_in_base = market.market_state.bond_reserves * market.spot_price / FixedPoint("2.0")
        # # WEI <= trade_amount <= max_short
        trade_amount = max(WEI, min(initial_trade_amount, maximum_trade_amount_in_base / FixedPoint("100.0")))
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            Trade(
                market=MarketType.HYPERDRIVE,
                trade=HyperdriveMarketAction(
                    action_type=MarketActionType.OPEN_LONG,
                    trade_amount=FixedPoint(trade_amount),
                    wallet=wallet,
                ),
            )
        ]

    def add_liquidity_with_random_amount(self, wallet: Wallet) -> list[Trade]:
        """Add liquidity with a random allowable amount"""
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(self.budget) * 0.1, scale=float(self.budget) * 0.01)
        )
        # WEI <= trade_amount
        trade_amount: FixedPoint = max(WEI, initial_trade_amount)
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            Trade(
                market=MarketType.HYPERDRIVE,
                trade=HyperdriveMarketAction(
                    action_type=MarketActionType.ADD_LIQUIDITY,
                    trade_amount=trade_amount,
                    wallet=wallet,
                ),
            )
        ]

    def remove_liquidity_with_random_amount(self, wallet: Wallet) -> list[Trade]:
        """Remove liquidity with a random allowable amount"""
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(self.budget) * 0.1, scale=float(self.budget) * 0.01)
        )
        # WEI <= trade_amount <= lp_tokens
        trade_amount = max(WEI, min(wallet.lp_tokens, initial_trade_amount))
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            Trade(
                market=MarketType.HYPERDRIVE,
                trade=HyperdriveMarketAction(
                    action_type=MarketActionType.REMOVE_LIQUIDITY,
                    trade_amount=trade_amount,
                    wallet=wallet,
                ),
            )
        ]

    def close_random_short(self, wallet: Wallet) -> list[Trade]:
        """Fully close the short balance for a random mint time"""
        # choose a random short time to close
        short_time: FixedPoint = list(wallet.shorts)[self.rng.integers(len(wallet.shorts))]
        trade_amount = wallet.shorts[short_time].balance  # close the full trade
        return [
            Trade(
                market=MarketType.HYPERDRIVE,
                trade=HyperdriveMarketAction(
                    action_type=MarketActionType.CLOSE_SHORT,
                    trade_amount=trade_amount,
                    wallet=wallet,
                    mint_time=short_time,
                ),
            )
        ]

    def close_random_long(self, wallet: Wallet) -> list[Trade]:
        """Fully close the long balance for a random mint time"""
        # choose a random long time to close
        long_time: FixedPoint = list(wallet.longs)[self.rng.integers(len(wallet.longs))]
        trade_amount = wallet.longs[long_time].balance  # close the full trade
        return [
            Trade(
                market=MarketType.HYPERDRIVE,
                trade=HyperdriveMarketAction(
                    action_type=MarketActionType.CLOSE_LONG,
                    trade_amount=trade_amount,
                    wallet=wallet,
                    mint_time=long_time,
                ),
            )
        ]

    def action(self, market: HyperdriveMarket, wallet: Wallet) -> list[Trade]:
        """Implement a random user strategy

        The agent performs one of four possible trades:
            [OPEN_LONG, OPEN_SHORT, CLOSE_LONG, CLOSE_SHORT]
            with the condition that close actions can only be performed after open actions

        The amount opened and closed is random, within constraints given by agent budget & market reserve levels

        Parameters
        ----------
        market : Market
            the trading market

        Returns
        -------
        action_list : list[MarketAction]
        """
        # pylint: disable=too-many-return-statements
        # check if the agent will trade this block or not
        if not self.rng.choice([True, False], p=[float(self.trade_chance), 1 - float(self.trade_chance)]):
            return []
        # user can always open a trade, and can close a trade if one is open
        available_actions = self.get_available_actions(wallet)
        # randomly choose one of the possible actions
        action_type = available_actions[self.rng.integers(len(available_actions))]
        # trade amount is also randomly chosen to be close to 10% of the agent's budget
        if action_type == MarketActionType.OPEN_SHORT:
            return self.open_short_with_random_amount(market, wallet)
        if action_type == MarketActionType.CLOSE_SHORT:
            return self.close_random_short(wallet)
        if action_type == MarketActionType.OPEN_LONG:
            return self.open_long_with_random_amount(market, wallet)
        if action_type == MarketActionType.CLOSE_LONG:
            return self.close_random_long(wallet)
        if action_type == MarketActionType.ADD_LIQUIDITY:
            return self.add_liquidity_with_random_amount(wallet)
        if action_type == MarketActionType.REMOVE_LIQUIDITY:
            return self.remove_liquidity_with_random_amount(wallet)
        return []

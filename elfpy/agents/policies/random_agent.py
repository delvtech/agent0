"""User strategy that opens or closes a random position with a random allowed amount."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from elfpy import WEI
from elfpy.markets.hyperdrive import HyperdriveMarketAction, MarketActionType
from elfpy.types import MarketType, Trade

from .base import BasePolicy

if TYPE_CHECKING:
    from numpy.random._generator import Generator as NumpyGenerator

    from elfpy.markets.hyperdrive import HyperdriveMarket
    from elfpy.wallet.wallet import Wallet


class RandomAgent(BasePolicy):
    """Random agent."""

    def __init__(
        self,
        budget: FixedPoint = FixedPoint("10_000.0"),
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint = FixedPoint("0.0001"),
        trade_chance: FixedPoint = FixedPoint("1.0"),
    ) -> None:
        """Add custom attributes."""
        if not isinstance(trade_chance, FixedPoint):
            raise TypeError(f"{trade_chance=} must be of type `FixedPoint`")
        self.trade_chance = trade_chance
        super().__init__(budget, rng, slippage_tolerance)

    def get_available_actions(
        self, wallet: Wallet, disallowed_actions: list[MarketActionType] | None = None
    ) -> list[MarketActionType]:
        """Get all available actions, excluding those listed in disallowed_actions."""
        # prevent accidental override
        if disallowed_actions is None:
            disallowed_actions = []
        # compile a list of all actions
        if wallet.balance.amount <= WEI:
            all_available_actions = []
        else:
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

    def new_trade(
        self, action_type: MarketActionType, trade_amount: FixedPoint, wallet: Wallet, mint_time=None
    ) -> list[Trade]:
        """Generate a new trade, customized for this bot.

        Arguments
        ---------
        action_type : MarketActionType
            The type of action to generate
        trade_amount : FixedPoint
            The amount to trade
        wallet : Wallet
            The wallet to trade with
        mint_time : FixedPoint
            The mint time of the trade

        Returns
        -------
        list[Trade]
            A list of trades desired to execute
        """
        action = HyperdriveMarketAction(action_type, wallet, trade_amount, self.slippage_tolerance, mint_time)
        return [Trade(market=MarketType.HYPERDRIVE, trade=action)]

    def open_short_with_random_amount(self, market: HyperdriveMarket, wallet: Wallet) -> list[Trade]:
        """Open a short with a random allowable amount."""
        maximum_trade_amount = market.get_max_short_for_account(wallet.balance.amount)
        if maximum_trade_amount <= WEI:
            return []

        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(self.budget) * 0.1, scale=float(self.budget) * 0.01)
        )
        # WEI <= trade_amount <= max_short
        trade_amount = max(WEI, min(initial_trade_amount, maximum_trade_amount))
        # return a trade using a specification that is parsable by the rest of the sim framework
        return self.new_trade(MarketActionType.OPEN_SHORT, trade_amount, wallet)

    def close_random_short(self, wallet: Wallet) -> list[Trade[HyperdriveMarketAction]]:
        """Fully close the short balance for a random mint time."""
        # choose a random short time to close
        short_time: FixedPoint = list(wallet.shorts)[self.rng.integers(len(wallet.shorts))]
        trade_amount = wallet.shorts[short_time].balance  # close the full trade
        return self.new_trade(MarketActionType.CLOSE_SHORT, trade_amount, wallet, short_time)

    def open_long_with_random_amount(
        self, market: HyperdriveMarket, wallet: Wallet
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Open a long with a random allowable amount."""
        maximum_trade_amount = market.get_max_long_for_account(wallet.balance.amount)
        if maximum_trade_amount <= WEI:
            return []
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(self.budget) * 0.1, scale=float(self.budget) * 0.01)
        )
        # WEI <= trade_amount <= max long
        trade_amount = max(WEI, min(initial_trade_amount, maximum_trade_amount))
        # return a trade using a specification that is parsable by the rest of the sim framework
        return self.new_trade(MarketActionType.OPEN_LONG, trade_amount, wallet)

    def close_random_long(self, wallet: Wallet) -> list[Trade[HyperdriveMarketAction]]:
        """Fully close the long balance for a random mint time."""
        # choose a random long time to close
        long_time: FixedPoint = list(wallet.longs)[self.rng.integers(len(wallet.longs))]
        trade_amount = wallet.longs[long_time].balance  # close the full trade
        return self.new_trade(MarketActionType.CLOSE_LONG, trade_amount, wallet, long_time)

    def add_liquidity_with_random_amount(self, wallet: Wallet) -> list[Trade[HyperdriveMarketAction]]:
        """Add liquidity with a random allowable amount."""
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(self.budget) * 0.1, scale=float(self.budget) * 0.01)
        )
        # WEI <= trade_amount
        trade_amount: FixedPoint = max(WEI, min(wallet.balance.amount, initial_trade_amount))
        # return a trade using a specification that is parsable by the rest of the sim framework
        return self.new_trade(MarketActionType.ADD_LIQUIDITY, trade_amount, wallet)

    def remove_liquidity_with_random_amount(self, wallet: Wallet) -> list[Trade[HyperdriveMarketAction]]:
        """Remove liquidity with a random allowable amount."""
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(self.budget) * 0.1, scale=float(self.budget) * 0.01)
        )
        # WEI <= trade_amount <= lp_tokens
        trade_amount = max(WEI, min(wallet.lp_tokens, initial_trade_amount))
        # return a trade using a specification that is parsable by the rest of the sim framework
        return self.new_trade(MarketActionType.REMOVE_LIQUIDITY, trade_amount, wallet)

    def action(self, market: HyperdriveMarket, wallet: Wallet) -> list[Trade[HyperdriveMarketAction]]:
        """Implement a random user strategy.

        The agent performs one of four possible trades:
            [OPEN_LONG, OPEN_SHORT, CLOSE_LONG, CLOSE_SHORT]
            with the condition that close actions can only be performed after open actions

        The amount opened and closed is random, within constraints given by agent budget & market reserve levels

        Arguments
        ---------
        market : Market
            the trading market
        wallet : Wallet
            agent's wallet

        Returns
        -------
        list[MarketAction]
            list of actions
        """
        # pylint: disable=too-many-return-statements
        # check if the agent will trade this block or not
        gonna_trade = self.rng.choice([True, False], p=[float(self.trade_chance), 1 - float(self.trade_chance)])
        if not gonna_trade:
            return []
        # user can always open a trade, and can close a trade if one is open
        available_actions = self.get_available_actions(wallet)
        # randomly choose one of the possible actions
        action_type = available_actions[self.rng.integers(len(available_actions))]
        # map action type to a Tuple of function and arguments
        take_action = {
            MarketActionType.OPEN_SHORT: (self.open_short_with_random_amount, (market, wallet)),
            MarketActionType.CLOSE_SHORT: (self.close_random_short, (wallet)),
            MarketActionType.OPEN_LONG: (self.open_long_with_random_amount, (market, wallet)),
            MarketActionType.CLOSE_LONG: (self.close_random_long, (wallet)),
            MarketActionType.ADD_LIQUIDITY: (self.add_liquidity_with_random_amount, (wallet)),
            MarketActionType.REMOVE_LIQUIDITY: (self.remove_liquidity_with_random_amount, (wallet)),
        }
        # trade amount is also randomly chosen to be close to 10% of the agent's budget
        if action_type in take_action:
            selected_action, *args = take_action[action_type]
            return selected_action(*args)
        return []

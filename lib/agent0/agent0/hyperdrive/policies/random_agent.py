"""User strategy that opens or closes a random position with a random allowed amount."""
from __future__ import annotations

from typing import TYPE_CHECKING

from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction
from elfpy import WEI
from elfpy.types import MarketType, Trade
from fixedpointmath import FixedPoint

from .hyperdrive_policy import HyperdrivePolicy

if TYPE_CHECKING:
    from agent0.hyperdrive.agents import HyperdriveWallet

    # from agent0.hyperdrive import HyperdriveMarketState # TODO: use agent0 market state instead of elfpy market
    from elfpy.markets.hyperdrive import HyperdriveMarket as HyperdriveMarketState
    from numpy.random._generator import Generator as NumpyGenerator


class RandomAgent(HyperdrivePolicy):
    """Random agent."""

    def __init__(
        self,
        budget: FixedPoint = FixedPoint("10_000.0"),
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        trade_chance: FixedPoint = FixedPoint("1.0"),
    ) -> None:
        """Adds custom attributes."""
        if not isinstance(trade_chance, FixedPoint):
            raise TypeError(f"{trade_chance=} must be of type `FixedPoint`")
        self.trade_chance = trade_chance
        super().__init__(budget, rng, slippage_tolerance)

    def get_available_actions(
        self,
        wallet: HyperdriveWallet,
        disallowed_actions: list[HyperdriveActionType] | None = None,
    ) -> list[HyperdriveActionType]:
        """Get all available actions, excluding those listed in disallowed_actions."""
        # prevent accidental override
        if disallowed_actions is None:
            disallowed_actions = []
        # compile a list of all actions
        if wallet.balance.amount <= WEI:
            all_available_actions = []
        else:
            all_available_actions = [
                HyperdriveActionType.OPEN_LONG,
                HyperdriveActionType.OPEN_SHORT,
                HyperdriveActionType.ADD_LIQUIDITY,
            ]
        if wallet.longs:  # if the agent has open longs
            all_available_actions.append(HyperdriveActionType.CLOSE_LONG)
        if wallet.shorts:  # if the agent has open shorts
            all_available_actions.append(HyperdriveActionType.CLOSE_SHORT)
        if wallet.lp_tokens:
            all_available_actions.append(HyperdriveActionType.REMOVE_LIQUIDITY)
        if wallet.withdraw_shares:
            all_available_actions.append(HyperdriveActionType.REDEEM_WITHDRAW_SHARE)
        # downselect from all actions to only include allowed actions
        return [action for action in all_available_actions if action not in disallowed_actions]

    def open_short_with_random_amount(self, market: HyperdriveMarketState, wallet: HyperdriveWallet) -> list[Trade]:
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

        return [
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.OPEN_SHORT,
                    trade_amount=trade_amount,
                    slippage_tolerance=self.slippage_tolerance,
                    wallet=wallet,
                ),
            )
        ]

    def close_random_short(self, wallet: HyperdriveWallet) -> list[Trade[HyperdriveMarketAction]]:
        """Fully close the short balance for a random mint time."""
        # choose a random short time to close
        short_time: FixedPoint = list(wallet.shorts)[self.rng.integers(len(wallet.shorts))]
        trade_amount = wallet.shorts[short_time].balance  # close the full trade
        return [
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.CLOSE_SHORT,
                    trade_amount=trade_amount,
                    slippage_tolerance=self.slippage_tolerance,
                    wallet=wallet,
                    mint_time=short_time,
                ),
            )
        ]

    def open_long_with_random_amount(
        self, market: HyperdriveMarketState, wallet: HyperdriveWallet
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
        return [
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.OPEN_LONG,
                    trade_amount=trade_amount,
                    slippage_tolerance=self.slippage_tolerance,
                    wallet=wallet,
                ),
            )
        ]

    def close_random_long(self, wallet: HyperdriveWallet) -> list[Trade[HyperdriveMarketAction]]:
        """Fully close the long balance for a random mint time."""
        # choose a random long time to close
        long_time: FixedPoint = list(wallet.longs)[self.rng.integers(len(wallet.longs))]
        trade_amount = wallet.longs[long_time].balance  # close the full trade
        return [
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.CLOSE_LONG,
                    trade_amount=trade_amount,
                    slippage_tolerance=self.slippage_tolerance,
                    wallet=wallet,
                    mint_time=long_time,
                ),
            )
        ]

    def add_liquidity_with_random_amount(self, wallet: HyperdriveWallet) -> list[Trade[HyperdriveMarketAction]]:
        """Add liquidity with a random allowable amount."""
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(self.budget) * 0.1, scale=float(self.budget) * 0.01)
        )
        # WEI <= trade_amount
        trade_amount: FixedPoint = max(WEI, min(wallet.balance.amount, initial_trade_amount))
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.ADD_LIQUIDITY,
                    trade_amount=trade_amount,
                    slippage_tolerance=self.slippage_tolerance,
                    wallet=wallet,
                ),
            )
        ]

    def remove_liquidity_with_random_amount(self, wallet: HyperdriveWallet) -> list[Trade[HyperdriveMarketAction]]:
        """Remove liquidity with a random allowable amount."""
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(self.budget) * 0.1, scale=float(self.budget) * 0.01)
        )
        # WEI <= trade_amount <= lp_tokens
        trade_amount = max(WEI, min(wallet.lp_tokens, initial_trade_amount))
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.REMOVE_LIQUIDITY,
                    trade_amount=trade_amount,
                    slippage_tolerance=self.slippage_tolerance,
                    wallet=wallet,
                ),
            )
        ]

    def redeem_withdraw_shares_with_random_amount(
        self, market: HyperdriveMarketState, wallet: HyperdriveWallet
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Redeem withdraw shares with a random allowable amount."""
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(self.budget) * 0.1, scale=float(self.budget) * 0.01)
        )

        shares_available_to_withdraw = min(
            wallet.withdraw_shares, market.market_state.withdraw_shares_ready_to_withdraw
        )

        # WEI <= trade_amount <= withdraw_shares
        trade_amount = max(WEI, min(shares_available_to_withdraw, initial_trade_amount))
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.REDEEM_WITHDRAW_SHARE,
                    trade_amount=trade_amount,
                    slippage_tolerance=self.slippage_tolerance,
                    wallet=wallet,
                ),
            )
        ]

    def action(self, market: HyperdriveMarketState, wallet: HyperdriveWallet) -> list[Trade[HyperdriveMarketAction]]:
        """Implement a random user strategy.

        The agent performs one of four possible trades:
            [OPEN_LONG, OPEN_SHORT, CLOSE_LONG, CLOSE_SHORT]
            with the condition that close actions can only be performed after open actions

        The amount opened and closed is random, within constraints given by agent budget & market reserve levels

        Arguments
        ---------
        market : Market
            the trading market
        wallet : HyperdriveWallet
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
        # trade amount is also randomly chosen to be close to 10% of the agent's budget
        if action_type == HyperdriveActionType.OPEN_SHORT:
            return self.open_short_with_random_amount(market, wallet)
        if action_type == HyperdriveActionType.CLOSE_SHORT:
            return self.close_random_short(wallet)
        if action_type == HyperdriveActionType.OPEN_LONG:
            return self.open_long_with_random_amount(market, wallet)
        if action_type == HyperdriveActionType.CLOSE_LONG:
            return self.close_random_long(wallet)
        if action_type == HyperdriveActionType.ADD_LIQUIDITY:
            return self.add_liquidity_with_random_amount(wallet)
        if action_type == HyperdriveActionType.REMOVE_LIQUIDITY:
            return self.remove_liquidity_with_random_amount(wallet)
        if action_type == HyperdriveActionType.REDEEM_WITHDRAW_SHARE:
            return self.redeem_withdraw_shares_with_random_amount(market, wallet)
        return []

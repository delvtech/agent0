"""User strategy that opens or closes a random position with a random allowed amount."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction
from elfpy import WEI
from elfpy.types import MarketType, Trade
from fixedpointmath import FixedPoint

from .hyperdrive_policy import HyperdrivePolicy

if TYPE_CHECKING:
    from agent0.hyperdrive.state import HyperdriveWallet
    from ethpy.hyperdrive.api import HyperdriveInterface
    from numpy.random._generator import Generator as NumpyGenerator


class Random(HyperdrivePolicy):
    """Random agent."""

    @classmethod
    def description(cls) -> str:
        """Describe the policy in a user friendly manner that allows newcomers to decide whether to use it.

        Returns
        -------
        str
            A description of the policy.
        """
        raw_description = """
        A simple demonstration agent that chooses its actions randomly.
        It can take 7 actions: open/close longs and shorts, add/remove liquidity, and redeem withdraw shares.
        Trade size is randomly drawn from a normal distribution with mean of 10% of budget and standard deviation of 1% of budget.
        A close action picks a random open position of the given type (long or short) and attempts to close its entire size.
        Withdrawals of liquidity and redemption of withdrawal shares is sized the same as an open position: N(0.1, 0.01) * budget.
        """
        return super().describe(raw_description)

    @dataclass
    class Config(HyperdrivePolicy.Config):
        """Custom config arguments for this policy

        Attributes
        ----------
        trade_chance: FixedPoint
            The probability of this bot to make a trade on an actio call
        """

        trade_chance: FixedPoint = FixedPoint("1.0")

    def __init__(
        self,
        budget: FixedPoint = FixedPoint("10_000.0"),
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        policy_config: Config | None = None,
    ) -> None:
        """Initializes the bot

        Arguments
        ---------
        budget: FixedPoint
            The budget of this policy
        rng: NumpyGenerator | None
            Random number generator
        slippage_tolerance: FixedPoint | None
            Slippage tolerance of trades
        policy_config: Config | None
            The custom arguments for this policy
        """

        if policy_config is None:
            policy_config = self.Config()

        self.trade_chance = policy_config.trade_chance
        super().__init__(budget, rng, slippage_tolerance)

    def get_available_actions(
        self,
        wallet: HyperdriveWallet,
        hyperdrive: HyperdriveInterface,
        disallowed_actions: list[HyperdriveActionType] | None = None,
    ) -> list[HyperdriveActionType]:
        """Get all available actions, excluding those listed in disallowed_actions."""
        # prevent accidental override
        if disallowed_actions is None:
            disallowed_actions = []
        # compile a list of all actions
        minimum_trade: FixedPoint = hyperdrive.current_pool_state.pool_config.minimum_transaction_amount
        if wallet.balance.amount <= minimum_trade:
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
        if wallet.withdraw_shares and hyperdrive.current_pool_state.pool_info.withdrawal_shares_ready_to_withdraw > 0:
            all_available_actions.append(HyperdriveActionType.REDEEM_WITHDRAW_SHARE)
        # downselect from all actions to only include allowed actions
        return [action for action in all_available_actions if action not in disallowed_actions]

    def open_short_with_random_amount(self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet) -> list[Trade]:
        """Open a short with a random allowable amount."""
        maximum_trade_amount = hyperdrive.calc_max_short(wallet.balance.amount)
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
        short_time = list(wallet.shorts)[self.rng.integers(len(wallet.shorts))]
        trade_amount = wallet.shorts[short_time].balance  # close the full trade
        return [
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.CLOSE_SHORT,
                    trade_amount=trade_amount,
                    slippage_tolerance=self.slippage_tolerance,
                    wallet=wallet,
                    maturity_time=short_time,
                ),
            )
        ]

    def open_long_with_random_amount(
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Open a long with a random allowable amount."""
        maximum_trade_amount = hyperdrive.calc_max_long(wallet.balance.amount)
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
        long_time = list(wallet.longs)[self.rng.integers(len(wallet.longs))]
        trade_amount = wallet.longs[long_time].balance  # close the full trade
        return [
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=HyperdriveActionType.CLOSE_LONG,
                    trade_amount=trade_amount,
                    slippage_tolerance=self.slippage_tolerance,
                    wallet=wallet,
                    maturity_time=long_time,
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
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> list[Trade[HyperdriveMarketAction]]:
        """Redeem withdraw shares with a random allowable amount."""
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = FixedPoint(
            self.rng.normal(loc=float(self.budget) * 0.1, scale=float(self.budget) * 0.01)
        )
        shares_available_to_withdraw = min(
            wallet.withdraw_shares,
            hyperdrive.current_pool_state.pool_info.withdrawal_shares_ready_to_withdraw,
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

    # We want to rename the argument from "interface" to "hyperdrive" to be more explicit
    # pylint: disable=arguments-renamed
    def action(
        self, hyperdrive: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Implement a random user strategy.

        The agent performs one of four possible trades:
            [OPEN_LONG, OPEN_SHORT, CLOSE_LONG, CLOSE_SHORT]
            with the condition that close actions can only be performed after open actions

        The amount opened and closed is random, within constraints given by agent budget & market reserve levels

        Arguments
        ---------
        hyperdrive : HyperdriveInterface
            Interface for the market on which this agent will be executing trades (MarketActions)
        wallet : HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=too-many-return-statements
        # check if the agent will trade this block or not
        gonna_trade = self.rng.choice([True, False], p=[float(self.trade_chance), 1 - float(self.trade_chance)])
        if not gonna_trade:
            return [], False
        # user can always open a trade, and can close a trade if one is open
        available_actions = self.get_available_actions(wallet, hyperdrive)
        # randomly choose one of the possible actions
        action_type = available_actions[self.rng.integers(len(available_actions))]
        # trade amount is also randomly chosen to be close to 10% of the agent's budget
        if action_type == HyperdriveActionType.OPEN_SHORT:
            return self.open_short_with_random_amount(hyperdrive, wallet), False
        if action_type == HyperdriveActionType.CLOSE_SHORT:
            return self.close_random_short(wallet), False
        if action_type == HyperdriveActionType.OPEN_LONG:
            return self.open_long_with_random_amount(hyperdrive, wallet), False
        if action_type == HyperdriveActionType.CLOSE_LONG:
            return self.close_random_long(wallet), False
        if action_type == HyperdriveActionType.ADD_LIQUIDITY:
            return self.add_liquidity_with_random_amount(wallet), False
        if action_type == HyperdriveActionType.REMOVE_LIQUIDITY:
            return self.remove_liquidity_with_random_amount(wallet), False
        if action_type == HyperdriveActionType.REDEEM_WITHDRAW_SHARE:
            return (
                self.redeem_withdraw_shares_with_random_amount(hyperdrive, wallet),
                False,
            )
        return [], False

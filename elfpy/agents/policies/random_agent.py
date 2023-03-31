"""User strategy that opens or closes a random position with a random allowed amount"""
from __future__ import annotations

import numpy as np
from numpy.random._generator import Generator as numpyGenerator

import elfpy
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.agents.agent as agent
import elfpy.types as types

# pylint: disable=too-many-arguments
# pylint: disable=duplicate-code


class Policy(agent.Agent):
    """Random agent"""

    def __init__(self, rng: numpyGenerator, trade_chance: float, wallet_address: int, budget: int = 10_000) -> None:
        """Adds custom attributes"""
        self.trade_chance = trade_chance
        self.rng = rng
        super().__init__(wallet_address, budget)

    def get_available_actions(
        self,
        disallowed_actions: list[hyperdrive_actions.MarketActionType] | None = None,
    ) -> list[hyperdrive_actions.MarketActionType]:
        """Get all available actions, excluding those listed in disallowed_actions"""
        # prevent accidental override
        if disallowed_actions is None:
            disallowed_actions = []
        # compile a list of all actions
        all_available_actions = [
            hyperdrive_actions.MarketActionType.OPEN_LONG,
            hyperdrive_actions.MarketActionType.OPEN_SHORT,
            hyperdrive_actions.MarketActionType.ADD_LIQUIDITY,
        ]
        if self.wallet.longs:  # if the agent has open longs
            all_available_actions.append(hyperdrive_actions.MarketActionType.CLOSE_LONG)
        if self.wallet.shorts:  # if the agent has open shorts
            all_available_actions.append(hyperdrive_actions.MarketActionType.CLOSE_SHORT)
        if self.wallet.lp_tokens:
            all_available_actions.append(hyperdrive_actions.MarketActionType.REMOVE_LIQUIDITY)
        # downselect from all actions to only include allowed actions
        return [action for action in all_available_actions if action not in disallowed_actions]

    def open_short_with_random_amount(self, market) -> list[types.Trade]:
        """Open a short with a random allowable amount"""
        initial_trade_amount = self.rng.normal(loc=self.budget * 0.1, scale=self.budget * 0.01)
        max_short = self.get_max_short(market)
        if max_short < elfpy.WEI:  # no short is possible
            return []
        trade_amount = np.maximum(
            elfpy.WEI, np.minimum(max_short, initial_trade_amount)
        )  # WEI <= trade_amount <= max_short
        return [
            types.Trade(
                market=types.MarketType.HYPERDRIVE,
                trade=hyperdrive_actions.MarketAction(
                    action_type=hyperdrive_actions.MarketActionType.OPEN_SHORT,
                    trade_amount=trade_amount,
                    wallet=self.wallet,
                ),
            )
        ]

    def open_long_with_random_amount(self, market) -> list[types.Trade]:
        """Open a long with a random allowable amount"""
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = self.rng.normal(loc=self.budget * 0.1, scale=self.budget * 0.01)
        # get the maximum amount that can be traded, based on the budget & market reserve levels
        max_long = self.get_max_long(market)
        if max_long < elfpy.WEI:  # no trade is possible
            return []
        # WEI <= trade_amount <= max_short
        trade_amount = np.maximum(elfpy.WEI, np.minimum(max_long, initial_trade_amount))
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            types.Trade(
                market=types.MarketType.HYPERDRIVE,
                trade=hyperdrive_actions.MarketAction(
                    action_type=hyperdrive_actions.MarketActionType.OPEN_LONG,
                    trade_amount=trade_amount,
                    wallet=self.wallet,
                ),
            )
        ]

    def add_liquidity_with_random_amount(self) -> list[types.Trade]:
        """Add liquidity with a random allowable amount"""
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = self.rng.normal(loc=self.budget * 0.1, scale=self.budget * 0.01)
        # WEI <= trade_amount
        trade_amount = np.maximum(elfpy.WEI, initial_trade_amount)
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            types.Trade(
                market=types.MarketType.HYPERDRIVE,
                trade=hyperdrive_actions.MarketAction(
                    action_type=hyperdrive_actions.MarketActionType.ADD_LIQUIDITY,
                    trade_amount=trade_amount,
                    wallet=self.wallet,
                ),
            )
        ]

    def remove_liquidity_with_random_amount(self) -> list[types.Trade]:
        """Remove liquidity with a random allowable amount"""
        # take a guess at the trade amount, which should be about 10% of the agent’s budget
        initial_trade_amount = self.rng.normal(loc=self.budget * 0.1, scale=self.budget * 0.01)
        # WEI <= trade_amount <= lp_tokens
        trade_amount = np.maximum(elfpy.WEI, np.minimum(self.wallet.lp_tokens, initial_trade_amount))
        # return a trade using a specification that is parsable by the rest of the sim framework
        return [
            types.Trade(
                market=types.MarketType.HYPERDRIVE,
                trade=hyperdrive_actions.MarketAction(
                    action_type=hyperdrive_actions.MarketActionType.REMOVE_LIQUIDITY,
                    trade_amount=trade_amount,
                    wallet=self.wallet,
                ),
            )
        ]

    def close_random_short(self) -> list[types.Trade]:
        """Fully close the short balance for a random mint time"""
        short_time = self.rng.choice(list(self.wallet.shorts)).item()  # choose a random short time to close
        trade_amount = self.wallet.shorts[short_time].balance  # close the full trade
        return [
            types.Trade(
                market=types.MarketType.HYPERDRIVE,
                trade=hyperdrive_actions.MarketAction(
                    action_type=hyperdrive_actions.MarketActionType.CLOSE_SHORT,
                    trade_amount=trade_amount,
                    wallet=self.wallet,
                    mint_time=short_time,
                ),
            )
        ]

    def close_random_long(self) -> list[types.Trade]:
        """Fully close the long balance for a random mint time"""
        long_time = self.rng.choice(list(self.wallet.longs)).item()  # choose a random long time to close
        trade_amount = self.wallet.longs[long_time].balance  # close the full trade
        return [
            types.Trade(
                market=types.MarketType.HYPERDRIVE,
                trade=hyperdrive_actions.MarketAction(
                    action_type=hyperdrive_actions.MarketActionType.CLOSE_LONG,
                    trade_amount=trade_amount,
                    wallet=self.wallet,
                    mint_time=long_time,
                ),
            )
        ]

    def action(self, market: hyperdrive_market.Market) -> list[types.Trade]:
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
        if not self.rng.choice([True, False], p=[self.trade_chance, 1 - self.trade_chance]):
            return []
        # user can always open a trade, and can close a trade if one is open
        available_actions = self.get_available_actions()
        # randomly choose one of the possible actions
        action_type = self.rng.choice(np.array(available_actions), size=1).item()
        # trade amount is also randomly chosen to be close to 10% of the agent's budget
        if action_type == hyperdrive_actions.MarketActionType.OPEN_SHORT:
            return self.open_short_with_random_amount(market)
        if action_type == hyperdrive_actions.MarketActionType.CLOSE_SHORT:
            return self.close_random_short()
        if action_type == hyperdrive_actions.MarketActionType.OPEN_LONG:
            return self.open_long_with_random_amount(market)
        if action_type == hyperdrive_actions.MarketActionType.CLOSE_LONG:
            return self.close_random_long()
        if action_type == hyperdrive_actions.MarketActionType.ADD_LIQUIDITY:
            return self.add_liquidity_with_random_amount()
        if action_type == hyperdrive_actions.MarketActionType.REMOVE_LIQUIDITY:
            return self.remove_liquidity_with_random_amount()
        return []

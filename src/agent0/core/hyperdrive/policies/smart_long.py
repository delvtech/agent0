"""Agent policy for leveraged long positions"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint, minimum

from agent0.core.base import WEI, Trade
from agent0.core.hyperdrive.agent import close_long_trade, open_long_trade

from .hyperdrive_policy import HyperdriveBasePolicy

if TYPE_CHECKING:
    from agent0.core.hyperdrive import HyperdriveMarketAction, HyperdriveWallet
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface

# pylint: disable=too-few-public-methods


class SmartLong(HyperdriveBasePolicy):
    """Agent that opens longs to push the fixed-rate towards the variable-rate."""

    @classmethod
    def description(cls) -> str:
        """Describe the policy in a user friendly manner that allows newcomers to decide whether to use it.

        Returns
        -------
        str
            A description of the policy.
        """
        raw_description = """
        My strategy:
            - I'm not willing to open a long if it will cause the fixed-rate apr to go below the variable rate
                - I simulate the outcome of my trade, and only execute on this condition
            - I only close if the position has matured
            - I only open one long at a time
            - I do not take into account fees when targeting the fixed rate
        """
        return super().describe(raw_description)

    @dataclass(kw_only=True)
    class Config(HyperdriveBasePolicy.Config):
        """Custom config arguments for this policy."""

        trade_chance: FixedPoint = FixedPoint("0.5")
        """The percent chance to open a trade."""
        risk_threshold: FixedPoint = FixedPoint("0.0001")
        """The upper threshold of the fixed rate minus the variable rate to open a long."""

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals

    def __init__(
        self,
        policy_config: Config,
    ):
        """Initializes the bot

        Arguments
        ---------
        policy_config: Config
            The custom arguments for this policy
        """
        self.trade_chance = policy_config.trade_chance
        self.risk_threshold = policy_config.risk_threshold

        super().__init__(policy_config)

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Implement a Long Louie user strategy

        Arguments
        ---------
        interface: HyperdriveReadInterface
            Interface for the market on which this agent will be executing trades (MarketActions).
        wallet: HyperdriveWallet
            The agent's wallet.

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading.
        """
        # Any trading at all is based on a weighted coin flip -- they have a trade_chance% chance of executing a trade
        gonna_trade = self.rng.choice([True, False], p=[float(self.trade_chance), 1 - float(self.trade_chance)])
        if not gonna_trade:
            return ([], False)
        pool_state = interface.current_pool_state
        action_list = []
        for long_time in wallet.longs:  # loop over longs # pylint: disable=consider-using-dict-items
            # if any long is mature
            # TODO: should we make this less time? they dont close before the agent runs out of money
            # how to intelligently pick the length? using PNL I guess.
            if (pool_state.block_time - FixedPoint(long_time)) >= pool_state.pool_config.position_duration:
                trade_amount = wallet.longs[long_time].balance  # close the whole thing
                action_list.append(close_long_trade(trade_amount, long_time, self.slippage_tolerance))
        long_balances = [long.balance for long in wallet.longs.values()]
        has_opened_long = bool(any(long_balance > 0 for long_balance in long_balances))

        variable_rate = pool_state.variable_rate
        # Variable rate can be None if underlying yield doesn't have a `getRate` function
        if variable_rate is None:
            variable_rate = interface.get_standardized_variable_rate()

        # only open a long if the fixed rate is higher than variable rate
        if (interface.calc_spot_rate() - variable_rate) > self.risk_threshold and not has_opened_long:
            # calculate the total number of bonds we want to see in the pool
            total_bonds_to_match_variable_apr = interface.calc_bonds_given_shares_and_rate(target_rate=variable_rate)
            # get the delta bond amount & convert units
            bond_reserves: FixedPoint = pool_state.pool_info.bond_reserves
            # calculate how many bonds we take out of the pool
            new_bonds_to_match_variable_apr = (
                bond_reserves - total_bonds_to_match_variable_apr
            ) * interface.calc_spot_price()
            # calculate how much base we pay for the new bonds
            new_base_to_match_variable_apr = interface.calc_bonds_out_given_shares_in_down(
                new_bonds_to_match_variable_apr
            )
            # get the maximum amount the agent can long given the market and the agent's wallet
            max_base = interface.calc_max_long(wallet.balance.amount, pool_state)
            # don't want to trade more than the agent has or more than the market can handle
            trade_amount = minimum(max_base, new_base_to_match_variable_apr)
            if trade_amount > WEI and wallet.balance.amount > WEI:
                action_list.append(open_long_trade(trade_amount, self.slippage_tolerance))
        return action_list, False

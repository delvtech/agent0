"""Custom policy example."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from agent0 import (
    HyperdriveBasePolicy,
    add_liquidity_trade,
    close_long_trade,
    close_short_trade,
    open_long_trade,
    open_short_trade,
    redeem_withdraw_shares_trade,
    remove_liquidity_trade,
)

if TYPE_CHECKING:
    from agent0.core.base import Trade
    from agent0.core.hyperdrive import HyperdriveMarketAction, HyperdriveWallet
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface


# Build custom policy
# Simple agent, opens a set of all trades for a fixed amount and closes them after
class CustomCycleTradesPolicy(HyperdriveBasePolicy):
    """An agent that simply cycles through all trades."""

    @dataclass(kw_only=True)
    class Config(HyperdriveBasePolicy.Config):
        """Custom config arguments for this policy."""

        # Add additional parameters for custom policy here
        # Setting defaults for this parameter here
        static_trade_amount_wei: int = FixedPoint(100).scaled_value  # 100 base
        """The probability of this bot to make a trade on an action call."""

    # Using default parameters
    def __init__(self, policy_config: Config):
        self.static_trade_amount_wei = policy_config.static_trade_amount_wei
        # We want to do a sequence of trades one at a time, so we keep an internal counter based on
        # how many times `action` has been called.
        self.counter = 0
        super().__init__(policy_config)

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """This agent simply opens all trades for a fixed amount and closes them after, one at a time

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market.
        wallet: HyperdriveWallet
            agent's wallet

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        if self.counter == 0:
            # Add liquidity
            action_list.append(add_liquidity_trade(trade_amount=FixedPoint(scaled_value=self.static_trade_amount_wei)))
        elif self.counter == 1:
            # Open Long
            action_list.append(
                open_long_trade(FixedPoint(scaled_value=self.static_trade_amount_wei), self.slippage_tolerance)
            )
        elif self.counter == 2:
            # Open Short
            action_list.append(
                open_short_trade(FixedPoint(scaled_value=self.static_trade_amount_wei), self.slippage_tolerance)
            )
        elif self.counter == 3:
            # Remove All Liquidity
            action_list.append(remove_liquidity_trade(wallet.lp_tokens))
        elif self.counter == 4:
            # Close All Longs
            assert len(wallet.longs) == 1
            for long_time, long in wallet.longs.items():
                action_list.append(close_long_trade(long.balance, long_time, self.slippage_tolerance))
        elif self.counter == 5:
            # Close All Shorts
            assert len(wallet.shorts) == 1
            for short_time, short in wallet.shorts.items():
                action_list.append(close_short_trade(short.balance, short_time, self.slippage_tolerance))
        elif self.counter == 6:
            # Redeem all withdrawal shares
            action_list.append(redeem_withdraw_shares_trade(wallet.withdraw_shares))

        self.counter += 1
        return action_list, False

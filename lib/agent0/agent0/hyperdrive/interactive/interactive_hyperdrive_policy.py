"""The interactive hyperdrive policy to use for interactive hyperdrive."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Type

from fixedpointmath import FixedPoint

from agent0.base import MarketType, Trade
from agent0.hyperdrive.interface import HyperdriveReadInterface
from agent0.hyperdrive.policies import HyperdrivePolicy
from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction, HyperdriveWallet


class InteractiveHyperdrivePolicy(HyperdrivePolicy):
    """Policy for interactive hyperdrive.
    This policy works by allowing the caller to call `set_next_action` to specify the next action to take
    during the main trading loop.
    """

    @dataclass(kw_only=True)
    class Config(HyperdrivePolicy.Config):
        """Configuration for the interactive hyperdrive policy.

        Attributes
        ----------
        sub_policy: HyperdrivePolicy
            The sub-policy to apply to the actions.
        sub_policy_config: HyperdrivePolicy.Config
            The configuration for the sub-policy.
        """

        sub_policy: Type[HyperdrivePolicy] | None = None
        sub_policy_config: HyperdrivePolicy.Config | None = None

    def __init__(self, policy_config: Config):
        """Initialize the bot.

        Arguments
        ---------
        budget: FixedPoint
            The budget of this policy
        sub_policy: HyperdrivePolicy | None
            An optional sub-policy to apply to the actions.
        """
        self.next_action = None
        self.next_trade_amount = None
        self.next_maturity_time = None
        self.use_sub_policy_for_next_action = False

        # Initialize the sub-policy
        if policy_config.sub_policy is None:
            self.sub_policy = None
        else:
            # If no config, we construct it with defaults
            if policy_config.sub_policy_config is None:
                sub_policy_config = policy_config.sub_policy.Config()
            else:
                sub_policy_config = policy_config.sub_policy_config
            # For typing
            assert sub_policy_config is not None
            self.sub_policy = policy_config.sub_policy(sub_policy_config)

        super().__init__(policy_config)

    def set_next_action(
        self, action: HyperdriveActionType, trade_amount: FixedPoint, maturity_time: int | None = None
    ) -> None:
        """Set the next action to execute when the main trading loop is called.

        Arguments
        ---------
        action: HyperdriveActionType
            The action type to be performed.
        trade_amount: FixedPoint
            A FixedPoint value indicating how much should be traded.
        maturity_time: int | None, optional
            The optional maturity time in epoch seconds.
            This is required for certain trade types, such as closing longs and shorts.
            Otherwise it can be omitted and will be set to the mint time plus the position duration.
        """
        self.next_action = action
        self.next_trade_amount = trade_amount
        self.next_maturity_time = maturity_time
        self.use_sub_policy_for_next_action = False

    def set_next_action_from_sub_policy(self) -> None:
        """Set the next action to execute using the underlying sub policy."""

        # Assuming error handling on this call is handeled by the interactive agent
        assert self.sub_policy is not None

        self.next_action = None
        self.next_trade_amount = None
        self.next_maturity_time = None
        self.use_sub_policy_for_next_action = True

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Specify actions.

        Arguments
        ---------
        interface: HyperdriveReadInterface
            Interface for the market on which this agent will be executing trades (MarketActions)
        wallet: HyperdriveWallet
            agent's wallet

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """

        if self.use_sub_policy_for_next_action:
            assert self.sub_policy is not None
            trades, done_trading = self.sub_policy.action(interface, wallet)
            # If the sub policy is done trading, we print a warning here
            # This policy can never stop trading, as we still may want to do interactive trades after.
            if done_trading:
                logging.warning("Sub policy is done trading")

        else:
            assert self.next_action is not None
            assert self.next_trade_amount is not None

            trades = [
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=self.next_action,
                        trade_amount=self.next_trade_amount,
                        maturity_time=self.next_maturity_time,
                    ),
                )
            ]
        # Since we're executing trade by trade, this bot is never "done" trading
        return trades, False

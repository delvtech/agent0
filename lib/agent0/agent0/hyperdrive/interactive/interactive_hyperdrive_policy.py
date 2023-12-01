"""The interactive hyperdrive policy to use for interactive hyperdrive."""
from __future__ import annotations

from ethpy.hyperdrive.api import HyperdriveInterface
from fixedpointmath import FixedPoint

from agent0.base import MarketType, Trade
from agent0.hyperdrive.policies import HyperdrivePolicy
from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction, HyperdriveWallet


class InteractiveHyperdrivePolicy(HyperdrivePolicy):
    """Policy for interactive hyperdrive.
    This policy works by allowing the caller to call `set_next_action` to specify the next action to take
    during the main trading loop.
    """

    def __init__(self, policy_config: HyperdrivePolicy.Config):
        """Initialize the bot.

        Arguments
        ---------
        budget: FixedPoint
            The budget of this policy
        """
        self.next_action = None
        self.next_trade_amount = None
        self.next_maturity_time = None
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

    def action(
        self, interface: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Specify actions.

        Arguments
        ---------
        interface: HyperdriveInterface
            Interface for the market on which this agent will be executing trades (MarketActions)
        wallet: HyperdriveWallet
            agent's wallet

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        assert self.next_action is not None
        assert self.next_trade_amount is not None

        trades = [
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=self.next_action,
                    trade_amount=self.next_trade_amount,
                    wallet=wallet,
                    maturity_time=self.next_maturity_time,
                ),
            )
        ]
        # Since we're executing trade by trade, this bot is never "done" trading
        return trades, False

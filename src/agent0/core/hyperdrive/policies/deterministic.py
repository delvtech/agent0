"""Deterministically trade things."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from agent0.core.base import MarketType, Trade
from agent0.core.hyperdrive.agent import HyperdriveActionType, HyperdriveMarketAction

from .hyperdrive_policy import HyperdriveBasePolicy

if TYPE_CHECKING:
    from agent0.core.hyperdrive.agent import HyperdriveWallet
    from agent0.ethpy.hyperdrive import HyperdriveReadInterface


class Deterministic(HyperdriveBasePolicy):
    """Deterministic trading for testing and other purposes."""

    @classmethod
    def description(cls) -> str:
        """Describe the policy in a user friendly manner that allows newcomers to decide whether to use it.

        Returns
        -------
        str
            The description of the policy, as described above.
        """
        raw_description = """
        Run deterministic trades as passed in through the trade_policy argument in its
        policy_config. The trade_policy is a list of tuples formatted as follows:
            - (open_long, int(1e6))
        Allowed trade types are "open_long", "close_long", "open_short", "close_short".
        """
        return super().describe(raw_description)

    @dataclass(kw_only=True)
    class Config(HyperdriveBasePolicy.Config):
        """Custom config arguments for this policy."""

        trade_list: list[tuple[str, int]]
        """
        A list of tuples formatted as follows:
            - (<trade_type>, <amount>)
        Allowed trade types are "open_long", "close_long", "open_short", "close_short".
        """

    def __init__(self, policy_config: Config):
        """Initialize the bot.

        Arguments
        ---------
        policy_config: Config
            The custom arguments for this policy
        """
        if policy_config.trade_list is None:
            self.trade_list = [("add_liquidity", 100), ("open_long", 100), ("open_short", 100)]
        else:
            self.trade_list = policy_config.trade_list
        self.starting_length = len(self.trade_list)
        super().__init__(policy_config)

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Specify actions.

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
        logging.log(10, "ACTION LOG %s/%s", len(self.trade_list), self.starting_length)
        if not self.trade_list:
            return [], True  # done trading
        action_type, amount = self.trade_list.pop(0)
        mint_time = next(iter({"close_long": wallet.longs, "close_short": wallet.shorts}.get(action_type, [])), None)
        action = HyperdriveMarketAction(HyperdriveActionType(action_type), FixedPoint(amount), None, mint_time)
        return [Trade(market_type=MarketType.HYPERDRIVE, market_action=action)], False

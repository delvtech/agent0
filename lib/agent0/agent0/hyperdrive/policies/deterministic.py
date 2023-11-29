"""Deterministically trade things."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from agent0.base import MarketType, Trade
from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction

from .hyperdrive_policy import HyperdrivePolicy

if TYPE_CHECKING:
    from ethpy.hyperdrive.api import HyperdriveInterface
    from numpy.random._generator import Generator as NumpyGenerator

    from agent0.hyperdrive.state import HyperdriveWallet


class Deterministic(HyperdrivePolicy):
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

    @dataclass
    class Config(HyperdrivePolicy.Config):
        """Custom config arguments for this policy.

        Attributes
        ----------
        high_fixed_rate_thresh: FixedPoint
            Amount over variable rate to arbitrage.
        low_fixed_rate_thresh: FixedPoint
            Amount below variable rate to arbitrage
        lp_portion: FixedPoint
            The portion of capital assigned to LP
        """

        trade_list: list[tuple[str, int]]

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        policy_config: Config | None = None,
    ):
        """Initialize the bot.

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
        self.trade_list = (
            policy_config.trade_list
            if policy_config
            else [("add_liquidity", 100), ("open_long", 100), ("open_short", 100)]
        )
        self.starting_length = len(self.trade_list)
        super().__init__(budget, rng)

    def action(
        self, interface: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Specify actions.

        Arguments
        ---------
        interface: HyperdriveInterface
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
        action = HyperdriveMarketAction(HyperdriveActionType(action_type), wallet, FixedPoint(amount), None, mint_time)
        return [Trade(market_type=MarketType.HYPERDRIVE, market_action=action)], False

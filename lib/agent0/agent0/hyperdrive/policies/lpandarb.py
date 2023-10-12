"""Agent policy for LP trading that also arbitrage on the fixed rate."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction
from elfpy.types import MarketType, Trade

from .hyperdrive_policy import HyperdrivePolicy

if TYPE_CHECKING:
    from ethpy.hyperdrive import HyperdriveInterface
    from numpy.random._generator import Generator as NumpyGenerator

    from agent0.hyperdrive.state import HyperdriveWallet


# TODO this should maybe subclass from arbitrage policy, but perhaps making it swappable
class LPandArb(HyperdrivePolicy):
    """LP and Arbitrage in a fixed proportion."""

    @classmethod
    def description(cls) -> str:
        """Describe the policy in a user friendly manner that allows newcomers to decide whether to use it.

        Returns
        -------
        str
            A description of the policy"""
        raw_description = """
        LP and arbitrage in a fixed proportion.
        If no arb opportunity, that portion is LPed. In the future this could go into the yield source.
        Try to redeem withdrawal shares right away.
        Arbitrage logic is as follows:
        - If the fixed rate is higher than `high_fixed_rate_thresh`:
            - Close entire short and open a new long for `trade_amount` base.
        - If the fixed rate is lower than `low_fixed_rate_thresh`:
            - Close entire long and open a new short for `trade_amount` bonds.
        """
        return super().describe(raw_description)

    @dataclass
    class Config(HyperdrivePolicy.Config):
        """Custom config arguments for this policy.

        Attributes
        ----------
        high_fixed_rate_thresh: FixedPoint
            The upper threshold of the fixed rate to open a position
        low_fixed_rate_thresh: FixedPoint
            The lower threshold of the fixed rate to open a position
        lp_portion: FixedPoint
            The portion of capital assigned to LP
        """

        lp_portion: FixedPoint = FixedPoint("0.5")
        high_fixed_rate_thresh: FixedPoint = FixedPoint("0.1")
        low_fixed_rate_thresh: FixedPoint = FixedPoint("0.02")

        @property
        def arb_portion(self) -> FixedPoint:
            """The portion of capital assigned to arbitrage."""
            return FixedPoint(1) - self.lp_portion

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
        # Defaults
        if policy_config is None:
            policy_config = self.Config()
        self.policy_config = policy_config
        self.arb_amount = self.policy_config.arb_portion * budget
        self.lp_amount = (self.policy_config.lp_portion) * budget
        self.high_fixed_rate_thresh = policy_config.high_fixed_rate_thresh
        self.low_fixed_rate_thresh = policy_config.low_fixed_rate_thresh

        super().__init__(budget, rng, slippage_tolerance)

    def action(
        self, interface: HyperdriveInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """Specify actions.

        Arguments
        ---------
        market : HyperdriveMarketState
            the trading market
        interface : MarketInterface
            Interface for the market on which this agent will be executing trades (MarketActions)
        wallet : HyperdriveWallet
            agent's wallet

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # Get fixed rate
        fixed_rate = interface.fixed_rate
        variable_rate = interface.variable_rate
        print(f"{fixed_rate=}")
        print(f"{variable_rate=}")

        action_list = []

        # Initial conditions, open LP position
        if wallet.lp_tokens == FixedPoint(0):
            # Add liquidity
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.ADD_LIQUIDITY,
                        trade_amount=self.lp_amount,
                        wallet=wallet,
                    ),
                )
            )

        # TODO run arb bot here

        return action_list, False

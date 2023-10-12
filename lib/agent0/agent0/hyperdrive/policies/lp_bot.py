"""Agent policy for LP trading that also arbitrage on the fixed rate"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction
from elfpy.types import MarketType, Trade
from fixedpointmath import FixedPoint

from .hyperdrive_policy import HyperdrivePolicy

if TYPE_CHECKING:
    from agent0.hyperdrive.state import HyperdriveWallet
    from ethpy.hyperdrive import HyperdriveInterface
    from numpy.random._generator import Generator as NumpyGenerator


# TODO this should maybe subclass from arbitrage policy, but perhaps making it swappable
class LPBot(HyperdrivePolicy):
    """LP Agent that opens an LP position and arbitrages based on the fixed rate

    .. note::
        My strategy:
            - I use a portion of my budget to open an LP position
            - I use the other portion of my budget to arbitrage the fixed rate
            - If nothing to arbitrage, the other portion is an additional LP position
            - I always close any withdrawal shares I have open
            - If the fixed rate is higher than `high_fixed_rate_thresh`,
                I close my short and open a new long for `trade_amount` base
            - If the fixed rate is lower than `low_fixed_rate_thresh`,
                I close my long and open a new short for `trade_amount` bonds
    """

    @dataclass
    class Config(HyperdrivePolicy.Config):
        """Custom config arguments for this policy

        Attributes
        ----------
        trade_amount: FixedPoint
            The static amount to trade when opening a position
        high_fixed_rate_thresh: FixedPoint
            The upper threshold of the fixed rate to open a position
        low_fixed_rate_thresh: FixedPoint
            The lower threshold of the fixed rate to open a position
        """

        high_fixed_rate_thresh: FixedPoint = FixedPoint("0.1")
        low_fixed_rate_thresh: FixedPoint = FixedPoint("0.02")
        lp_percent: FixedPoint = FixedPoint("0.8")

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        policy_config: Config | None = None,
    ):
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

        # Defaults
        if policy_config is None:
            policy_config = self.Config()
        self.trade_amount = (1 - policy_config.lp_percent) * budget
        self.lp_amount = (policy_config.lp_percent) * budget
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

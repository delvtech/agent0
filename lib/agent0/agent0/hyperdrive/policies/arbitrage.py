"""Agent policy for arbitrade trading on the fixed rate"""
from __future__ import annotations

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


class Arbitrage(HyperdrivePolicy):
    """Agent that arbitrages based on the fixed rate

    .. note::
        My strategy:
            - I arbitrage the fixed rate percentage based on thresholds
            - I always close any matured open positions
            - If the fixed rate is higher than `high_fixed_rate_thresh`,
                I close all open shorts an open a new long for `trade_amount` base
            - If the fixed rate is lower than `low_fixed_rate_thresh`,
                I close all open longs and open a new short for `trade_amount` bonds
    """

    @classmethod
    def description(cls) -> str:
        """Describe the policy in a user friendly manner that allows newcomers to decide whether to use it.

        Returns
        -------
        str
            A description of the policy.
        """
        raw_description = """
        Take advantage of deviations in the fixed rate from specified parameters.
        The following 3 parameters in Config define its operation:
        - When `high_fixed_rate_thresh`, open shorts are closed, and a long is opened.
        - When `low_fixed_rate_thresh`, open longs are closed, and a short is opened.
        - Trade size is fixed by `trade_amount`.
        Additionally, longs and shorts are closed if they are matured.
        """
        return super().describe(raw_description)

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

        trade_amount: FixedPoint = FixedPoint(100)
        high_fixed_rate_thresh: FixedPoint = FixedPoint("0.1")
        low_fixed_rate_thresh: FixedPoint = FixedPoint("0.02")

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
        self.policy_config = policy_config

        super().__init__(budget, rng, slippage_tolerance)

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
        pool_state = interface.current_pool_state
        fixed_rate = interface.calc_fixed_rate(pool_state)
        action_list = []

        # Close longs if matured
        for maturity_time, long in wallet.longs.items():
            # If matured
            if maturity_time < pool_state.block_time:
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_LONG,
                            trade_amount=long.balance,
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                            maturity_time=maturity_time,
                        ),
                    )
                )

        # Close shorts if matured
        for maturity_time, short in wallet.shorts.items():
            # If matured
            if maturity_time < pool_state.block_time:
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_SHORT,
                            trade_amount=short.balance,
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                            maturity_time=maturity_time,
                        ),
                    )
                )

        # High fixed rate detected
        if fixed_rate >= self.policy_config.high_fixed_rate_thresh:
            # Close all open shorts
            if len(wallet.shorts) > 0:
                for maturity_time, short in wallet.shorts.items():
                    action_list.append(
                        Trade(
                            market_type=MarketType.HYPERDRIVE,
                            market_action=HyperdriveMarketAction(
                                action_type=HyperdriveActionType.CLOSE_SHORT,
                                trade_amount=short.balance,
                                slippage_tolerance=self.slippage_tolerance,
                                wallet=wallet,
                                maturity_time=maturity_time,
                            ),
                        )
                    )
            # Open a new long
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_LONG,
                        trade_amount=self.policy_config.trade_amount,
                        slippage_tolerance=self.slippage_tolerance,
                        wallet=wallet,
                    ),
                )
            )

        # Low fixed rate detected
        if fixed_rate <= self.policy_config.low_fixed_rate_thresh:
            # Close all open longs
            if len(wallet.longs) > 0:
                for maturity_time, long in wallet.longs.items():
                    action_list.append(
                        Trade(
                            market_type=MarketType.HYPERDRIVE,
                            market_action=HyperdriveMarketAction(
                                action_type=HyperdriveActionType.CLOSE_LONG,
                                trade_amount=long.balance,
                                slippage_tolerance=self.slippage_tolerance,
                                wallet=wallet,
                                maturity_time=maturity_time,
                            ),
                        )
                    )
            # Open a new short
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_SHORT,
                        trade_amount=self.policy_config.trade_amount,
                        slippage_tolerance=self.slippage_tolerance,
                        wallet=wallet,
                    ),
                )
            )

        return action_list, False

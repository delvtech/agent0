"""Agent policy for smart short positions"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction
from elfpy import WEI
from elfpy.types import MarketType, Trade
from fixedpointmath import FixedPoint

from .hyperdrive_policy import HyperdrivePolicy

if TYPE_CHECKING:
    from agent0.hyperdrive.state import HyperdriveWallet

    # from agent0.hyperdrive import HyperdriveMarketState # TODO: use agent0 market state instead of elfpy market
    from elfpy.markets.hyperdrive import HyperdriveMarket as HyperdriveMarketState
    from numpy.random._generator import Generator as NumpyGenerator

# pylint: disable=too-few-public-methods


class ArbitragePolicy(HyperdrivePolicy):
    """Agent that paints & opens fixed rate borrow positions

    .. note::
        My strategy:
            - I arbitrage the fixed rate percentage based on thresholds


    """

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        trade_amount: FixedPoint | None = None,
        high_fixed_rate_thresh: FixedPoint | None = None,
        low_fixed_rate_thresh: FixedPoint | None = None,
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
        trade_amount: FixedPoint | None
            The static amount to trade when opening a position
        high_fixed_rate_thresh: FixedPoint | None
            The upper threshold of the fixed rate to open a position
        low_fixed_rate_thresh: FixedPoint | None
            The lower threshold of the fixed rate to open a position
        """

        # Defaults
        if trade_amount is None:
            trade_amount = FixedPoint(100)
        if high_fixed_rate_thresh is None:
            high_fixed_rate_thresh = FixedPoint(0.1)
        if low_fixed_rate_thresh is None:
            low_fixed_rate_thresh = FixedPoint(0.02)
        self.trade_amount = trade_amount
        self.high_fixed_rate_thresh = high_fixed_rate_thresh
        self.low_fixed_rate_thresh = low_fixed_rate_thresh

        super().__init__(budget, rng, slippage_tolerance)

    def action(self, market: HyperdriveMarketState, wallet: HyperdriveWallet) -> list[Trade]:
        """Specify actions.

        Arguments
        ---------
        market : HyperdriveMarketState
            the trading market
        wallet : HyperdriveWallet
            agent's wallet

        Returns
        -------
        list[Trade]
            list of actions
        """
        # If no base, do no trades
        if wallet.balance.amount <= WEI:
            return []

        # Calculate fixed rate
        # TODO this should be in the market
        init_share_price = market.market_state.init_share_price
        share_reserves = market.market_state.share_reserves
        bond_reserves = market.market_state.bond_reserves
        time_stretch = FixedPoint(1) / market.time_stretch_constant
        annualized_time = market.position_duration.days / (365)
        spot_price = ((init_share_price * share_reserves) / bond_reserves) ** time_stretch
        fixed_rate = (1 - spot_price) / (spot_price * annualized_time)

        action_list = []

        # Close longs if it's matured, one at a time
        # TODO figure out how to determine if position has matured
        # longs = list(wallet.longs.values())
        # has_opened_long = len(longs) > 0
        # if has_opened_long:
        #    maturity_time = list(wallet.longs)[0]  # get the maturity time of the open long
        #    # If matured
        #    if market.block_time.time - mint_time >= market.position_duration.years:
        #        action_list.append(
        #            Trade(
        #                market_type=MarketType.HYPERDRIVE,
        #                market_action=HyperdriveMarketAction(
        #                    action_type=HyperdriveMarketAction.CLOSE_LONG,
        #                    trade_amount=longs[0].balance,
        #                    wallet=wallet,
        #                    maturity_time=maturity_time,
        #                ),
        #            )
        #        )

        # High fixed rate detected
        if fixed_rate >= self.high_fixed_rate_thresh:
            # Close all open shorts
            if len(wallet.shorts) > 0:
                for maturity_time, short in wallet.shorts.items():
                    action_list.append(
                        Trade(
                            market_type=MarketType.HYPERDRIVE,
                            market_action=HyperdriveMarketAction(
                                action_type=HyperdriveActionType.CLOSE_SHORT,
                                trade_amount=short.balance,
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
                        trade_amount=self.trade_amount,
                        wallet=wallet,
                    ),
                )
            )

        # Low fixed rate detected
        if fixed_rate <= self.low_fixed_rate_thresh:
            # Close all open longs
            if len(wallet.longs) > 0:
                for maturity_time, long in wallet.longs.items():
                    action_list.append(
                        Trade(
                            market_type=MarketType.HYPERDRIVE,
                            market_action=HyperdriveMarketAction(
                                action_type=HyperdriveActionType.CLOSE_LONG,
                                trade_amount=long.balance,
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
                        trade_amount=self.trade_amount,
                        wallet=wallet,
                    ),
                )
            )

        return action_list

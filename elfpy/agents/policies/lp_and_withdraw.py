"""User strategy that adds liquidity and then removes it when enough time has passed"""
from __future__ import annotations

from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from elfpy.markets.hyperdrive import HyperdriveMarketAction, MarketActionType
from elfpy.types import MarketType, Trade

from .base import BasePolicy

if TYPE_CHECKING:
    from numpy.random._generator import Generator as NumpyGenerator

    from elfpy.markets.hyperdrive.hyperdrive_market import HyperdriveMarket
    from elfpy.wallet.wallet import Wallet

# pylint: disable=too-few-public-methods


class LpAndWithdrawAgent(BasePolicy):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(
        self,
        budget: FixedPoint = FixedPoint("1000.0"),
        rng: NumpyGenerator | None = None,
        amount_to_lp: FixedPoint = FixedPoint("100.0"),
        time_to_withdraw: FixedPoint = FixedPoint("1.0"),
    ):
        """call basic policy init then add custom stuff"""
        self.amount_to_lp = amount_to_lp
        self.time_to_withdraw = time_to_withdraw
        super().__init__(budget, rng)

    def action(self, market: HyperdriveMarket, wallet: Wallet) -> list[Trade]:
        """
        implement user strategy
        LP if you can, but only do it once
        """
        # pylint disable=unused-argument
        action_list: list[Trade] = []
        has_lp = wallet.lp_tokens > FixedPoint(0)
        amount_in_base = wallet.balance.amount
        can_lp = amount_in_base >= self.amount_to_lp
        if not has_lp and can_lp:
            action_list.append(
                Trade(
                    market=MarketType.HYPERDRIVE,
                    trade=HyperdriveMarketAction(
                        action_type=MarketActionType.ADD_LIQUIDITY,
                        trade_amount=self.amount_to_lp,
                        slippage_tolerance=self.slippage_tolerance,
                        wallet=wallet,
                    ),
                )
            )
        elif has_lp:
            enough_time_has_passed = market.block_time.time > self.time_to_withdraw
            if enough_time_has_passed:
                action_list.append(
                    Trade(
                        market=MarketType.HYPERDRIVE,
                        trade=HyperdriveMarketAction(
                            action_type=MarketActionType.REMOVE_LIQUIDITY,
                            trade_amount=wallet.lp_tokens,
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                        ),
                    )
                )
        return action_list

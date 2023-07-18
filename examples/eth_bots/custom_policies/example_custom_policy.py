"""Example custom agent strategy"""
from __future__ import annotations

from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from elfpy.agents.policies import BasePolicy
from elfpy.markets.hyperdrive import HyperdriveMarketAction, MarketActionType
from elfpy.types import MarketType, Trade

if TYPE_CHECKING:
    from elfpy.markets.hyperdrive import HyperdriveMarket
    from elfpy.wallet.wallet import Wallet

# pylint: disable=too-few-public-methods


class ExampleCustomPolicy(BasePolicy):
    """Example custom agent"""

    def action(self, market: HyperdriveMarket, wallet: Wallet) -> list[Trade]:
        """Specify actions"""
        # OPEN A LONG IF YOU HAVE NONE, CLOSE IT IF MATURED
        longs = list(wallet.longs.values())
        has_opened_long = len(longs) > 0
        action_list = []
        if has_opened_long:
            mint_time = list(wallet.longs)[-1]  # get the mint time of the open long
            if market.block_time.time - mint_time >= market.position_duration.years:
                action_list.append(
                    Trade(
                        market=MarketType.HYPERDRIVE,
                        trade=HyperdriveMarketAction(
                            action_type=MarketActionType.CLOSE_LONG,
                            trade_amount=longs[-1].balance,
                            wallet=wallet,
                            mint_time=mint_time,
                        ),
                    )
                )
        else:
            max_base = market.get_max_long_for_account(wallet.balance.amount)
            trade_amount = max_base / FixedPoint("2.0")
            action_list.append(
                Trade(
                    market=MarketType.HYPERDRIVE,
                    trade=HyperdriveMarketAction(
                        action_type=MarketActionType.OPEN_LONG,
                        trade_amount=trade_amount,
                        wallet=wallet,
                    ),
                )
            )

        # OPEN A SHORT IF YOU HAVE NONE, CLOSE IT IF MATURED
        shorts = list(wallet.shorts.values())
        has_opened_short = len(shorts) > 0
        action_list = []
        if has_opened_short:
            mint_time = list(wallet.shorts)[-1]  # get the mint time of the open long
            if market.block_time.time - mint_time >= market.position_duration.years:
                action_list.append(
                    Trade(
                        market=MarketType.HYPERDRIVE,
                        trade=HyperdriveMarketAction(
                            action_type=MarketActionType.CLOSE_SHORT,
                            trade_amount=shorts[-1].balance,
                            wallet=wallet,
                            mint_time=mint_time,
                        ),
                    )
                )
        else:
            max_base = market.get_max_short_for_account(wallet.balance.amount)
            trade_amount = max_base / FixedPoint("2.0")
            action_list.append(
                Trade(
                    market=MarketType.HYPERDRIVE,
                    trade=HyperdriveMarketAction(
                        action_type=MarketActionType.OPEN_SHORT,
                        trade_amount=trade_amount,
                        wallet=wallet,
                    ),
                )
            )
        return action_list

"""Example custom agent strategy"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from lib.elfpy.elfpy import WEI
from lib.elfpy.elfpy.agents.policies import BasePolicy
from lib.elfpy.elfpy.markets.hyperdrive import HyperdriveMarketAction, MarketActionType
from lib.elfpy.elfpy.types import MarketType, Trade

if TYPE_CHECKING:
    from numpy.random._generator import Generator as NumpyGenerator

    from lib.elfpy.elfpy.markets.hyperdrive import HyperdriveMarket
    from lib.elfpy.elfpy.wallet.wallet import Wallet

# pylint: disable=too-few-public-methods


class ExampleCustomPolicy(BasePolicy):
    """Example custom agent"""

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        trade_amount: FixedPoint | None = None,
    ):
        if trade_amount is None:
            self.trade_amount = FixedPoint(100)
            logging.warning("Policy trade_amount not set, using 100.")
        else:
            self.trade_amount: FixedPoint = trade_amount

        super().__init__(budget, rng, slippage_tolerance)

    def action(self, market: HyperdriveMarket, wallet: Wallet) -> list[Trade]:
        """Specify actions.

        Arguments
        ---------
        market : Market
            the trading market
        wallet : Wallet
            agent's wallet

        Returns
        -------
        list[MarketAction]
            list of actions
        """
        if wallet.balance.amount <= WEI:
            return []
        lp_chance = 0.5
        gonna_lp = self.rng.choice([True, False], p=[lp_chance, 1 - lp_chance])
        action_list = []
        if gonna_lp:
            # ADD LIQUIDITY IF YOU HAVEN'T, OTHERWISE REMOVE IT
            if wallet.lp_tokens > 0:  # agent has liquidity
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=MarketActionType.REMOVE_LIQUIDITY,
                            trade_amount=wallet.lp_tokens,
                            wallet=wallet,
                        ),
                    )
                )
            else:  # remove all of the agent's liquidity
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=MarketActionType.ADD_LIQUIDITY,
                            trade_amount=self.trade_amount,
                            wallet=wallet,
                        ),
                    )
                )
        else:
            # OPEN A LONG IF YOU HAVE NONE, CLOSE IT IF MATURED
            longs = list(wallet.longs.values())
            has_opened_long = len(longs) > 0
            if has_opened_long:
                mint_time = list(wallet.longs)[0]  # get the mint time of the open long
                if market.block_time.time - mint_time >= market.position_duration.years:
                    action_list.append(
                        Trade(
                            market_type=MarketType.HYPERDRIVE,
                            market_action=HyperdriveMarketAction(
                                action_type=MarketActionType.CLOSE_LONG,
                                trade_amount=longs[0].balance,
                                wallet=wallet,
                                mint_time=mint_time,
                            ),
                        )
                    )
            else:
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=MarketActionType.OPEN_LONG,
                            trade_amount=self.trade_amount,
                            wallet=wallet,
                        ),
                    )
                )

            # OPEN A SHORT IF YOU HAVE NONE, CLOSE IT IF MATURED
            shorts = list(wallet.shorts.values())
            has_opened_short = len(shorts) > 0
            if has_opened_short:
                mint_time = list(wallet.shorts)[0]  # get the mint time of the open long
                if market.block_time.time - mint_time >= market.position_duration.years:
                    action_list.append(
                        Trade(
                            market_type=MarketType.HYPERDRIVE,
                            market_action=HyperdriveMarketAction(
                                action_type=MarketActionType.CLOSE_SHORT,
                                trade_amount=shorts[0].balance,
                                wallet=wallet,
                                mint_time=mint_time,
                            ),
                        )
                    )
            else:
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=MarketActionType.OPEN_SHORT,
                            trade_amount=self.trade_amount,
                            wallet=wallet,
                        ),
                    )
                )
        return action_list

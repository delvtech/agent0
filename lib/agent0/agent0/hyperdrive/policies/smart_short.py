"""Agent policy for smart short positions"""
from __future__ import annotations

from typing import TYPE_CHECKING

from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction
from elfpy import WEI
from elfpy.types import MarketType, Trade
from fixedpointmath import FixedPoint

from .hyperdrive_policy import HyperdrivePolicy

if TYPE_CHECKING:
    from agent0.hyperdrive.agents import HyperdriveWallet

    # from agent0.hyperdrive import HyperdriveMarketState # TODO: use agent0 market state instead of elfpy market
    from elfpy.markets.hyperdrive import HyperdriveMarket as HyperdriveMarketState
    from numpy.random._generator import Generator as NumpyGenerator

# pylint: disable=too-few-public-methods


class ShortSally(HyperdrivePolicy):
    """Agent that paints & opens fixed rate borrow positions

    .. note::
        My strategy:
            - I'm an actor with a high risk threshold
            - I'm willing to open up a fixed-rate borrow (aka a short) if the fixed rate is
            ~2% higher than the variable rate (gauss mean=0.02; std=0.005, clipped at 0, 5)
            - I will never close my short until the simulation stops
                - UNLESS my short reaches the token duration mark (e.g. 6mo)
                - realistically, people might leave them hanging
            - I have total budget of 2k -> 250k (gauss mean=75k; std=50k, i.e. 68% values are within 75k +/- 50k)
            - I only open one short at a time
    """

    # pylint: disable=too-many-arguments

    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator,
        trade_chance: FixedPoint,
        risk_threshold: FixedPoint,
        slippage_tolerance: FixedPoint | None = None,
    ) -> None:
        """Add custom stuff then call basic policy init"""
        if not isinstance(trade_chance, FixedPoint):
            raise TypeError(f"{trade_chance=} must be of type `FixedPoint`")
        if not isinstance(risk_threshold, FixedPoint):
            raise TypeError(f"{risk_threshold=} must be of type `FixedPoint`")
        self.trade_chance = trade_chance
        self.risk_threshold = risk_threshold
        super().__init__(budget, rng, slippage_tolerance)

    def action(self, market: HyperdriveMarketState, wallet: HyperdriveWallet) -> list[Trade[HyperdriveMarketAction]]:
        """Implement a Short Sally user strategy


        Parameters
        ----------
        market : HyperdriveMarket
            the trading market

        Returns
        -------
        action_list : list[HyperdriveMarketAction]
        """
        # Any trading at all is based on a weighted coin flip -- they have a trade_chance% chance of executing a trade
        gonna_trade = self.rng.choice([True, False], p=[float(self.trade_chance), 1 - float(self.trade_chance)])
        if not gonna_trade:
            return []
        action_list = []
        for short_time in wallet.shorts:  # loop over shorts # pylint: disable=consider-using-dict-items
            # if any short is mature
            if (market.block_time.time - FixedPoint(short_time)) >= market.annualized_position_duration:
                trade_amount = wallet.shorts[short_time].balance  # close the whole thing
                action_list += [
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_SHORT,
                            trade_amount=trade_amount,
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                            mint_time=short_time,
                        ),
                    )
                ]
        short_balances = [short.balance for short in wallet.shorts.values()]
        has_opened_short = bool(any(short_balance > FixedPoint(0) for short_balance in short_balances))
        # only open a short if the fixed rate is 0.02 or more lower than variable rate
        if market.fixed_apr - market.market_state.variable_apr < self.risk_threshold and not has_opened_short:
            # maximum amount the agent can short given the market and the agent's wallet
            trade_amount = market.get_max_short_for_account(wallet.balance.amount)
            if trade_amount > WEI and wallet.balance.amount > WEI:
                action_list += [
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.OPEN_SHORT,
                            trade_amount=trade_amount,
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                            mint_time=market.block_time.time,
                        ),
                    )
                ]
        return action_list

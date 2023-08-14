"""Agent policy for leveraged long positions"""
from __future__ import annotations

from typing import TYPE_CHECKING

from agent0.hyperdrive import HyperdriveActionType, HyperdriveMarketAction
from elfpy import WEI
from elfpy.types import MarketType, Trade
from fixedpointmath import FixedPoint, FixedPointMath

from .hyperdrive_policy import HyperdrivePolicy

if TYPE_CHECKING:
    from agent0.hyperdrive.agents import HyperdriveWallet

    # from agent0.hyperdrive import HyperdriveMarketState # TODO: use agent0 market state instead of elfpy market
    from elfpy.markets.hyperdrive import HyperdriveMarket as HyperdriveMarketState
    from numpy.random._generator import Generator as NumpyGenerator
# pylint: disable=too-few-public-methods


class LongLouie(HyperdrivePolicy):
    """Agent that opens longs to push the fixed-rate towards the variable-rate

    .. note::
        My strategy:
            - I'm not willing to open a long if it will cause the fixed-rate apr to go below the variable rate
                - I simulate the outcome of my trade, and only execute on this condition
            - I only close if the position has matured
            - I have total budget of 2k -> 250k (gauss mean=75k; std=50k, i.e. 68% values are within 75k +/- 50k)
            - I only open one long at a time

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
        """Implement a Long Louie user strategy

        Parameters
        ----------
        market : Market
            the trading market

        Returns
        -------
        action_list : list[MarketAction]
        """
        # Any trading at all is based on a weighted coin flip -- they have a trade_chance% chance of executing a trade
        gonna_trade = self.rng.choice([True, False], p=[float(self.trade_chance), 1 - float(self.trade_chance)])
        if not gonna_trade:
            return []
        action_list = []
        for long_time in wallet.longs:  # loop over longs # pylint: disable=consider-using-dict-items
            # if any long is mature
            # TODO: should we make this less time? they dont close before the bot runs out of money
            # how to intelligently pick the length? using PNL I guess.
            if (market.block_time.time - FixedPoint(long_time)) >= market.annualized_position_duration:
                trade_amount = wallet.longs[long_time].balance  # close the whole thing
                action_list += [
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_LONG,
                            trade_amount=trade_amount,
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                            mint_time=long_time,
                        ),
                    )
                ]
        long_balances = [long.balance for long in wallet.longs.values()]
        has_opened_long = bool(any(long_balance > 0 for long_balance in long_balances))
        # only open a long if the fixed rate is higher than variable rate
        if (market.fixed_apr - market.market_state.variable_apr) > self.risk_threshold and not has_opened_long:
            total_bonds_to_match_variable_apr = market.pricing_model.calc_bond_reserves(
                target_apr=market.market_state.variable_apr,  # fixed rate targets the variable rate
                time_remaining=market.position_duration,
                market_state=market.market_state,
            )
            # get the delta bond amount & convert units
            new_bonds_to_match_variable_apr = (
                market.market_state.bond_reserves - total_bonds_to_match_variable_apr
            ) * market.spot_price
            new_base_to_match_variable_apr = market.pricing_model.calc_shares_out_given_bonds_in(
                share_reserves=market.market_state.share_reserves,
                bond_reserves=market.market_state.bond_reserves,
                lp_total_supply=market.market_state.lp_total_supply,
                d_bonds=new_bonds_to_match_variable_apr,
                time_elapsed=FixedPoint(1),  # opening a short, so no time has elapsed
                share_price=market.market_state.share_price,
                init_share_price=market.market_state.init_share_price,
            )
            # get the maximum amount the agent can long given the market and the agent's wallet
            max_base = market.get_max_long_for_account(wallet.balance.amount)
            # don't want to trade more than the agent has or more than the market can handle
            trade_amount = FixedPointMath.minimum(max_base, new_base_to_match_variable_apr)
            if trade_amount > WEI and wallet.balance.amount > WEI:
                action_list += [
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.OPEN_LONG,
                            trade_amount=trade_amount,
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                            mint_time=market.block_time.time,
                        ),
                    )
                ]
        return action_list

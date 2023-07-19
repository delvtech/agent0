"""The base pricing model"""
from __future__ import annotations  # types will be strings by default in 3.11

import logging
from abc import ABC
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

import elfpy
import elfpy.time as time
import elfpy.types as types
import elfpy.utils.price as price_utils

if TYPE_CHECKING:
    import elfpy.markets.trades as trades
    from elfpy.markets.hyperdrive import HyperdriveMarketState


class BasePricingModel(ABC):
    """Contains functions for calculating AMM variables

    Base class should not be instantiated on its own; it is assumed that a user will instantiate a child class

    .. todo:: Make this an interface
    """

    def calc_in_given_out(
        self,
        out: types.Quantity,
        market_state: HyperdriveMarketState,
        time_remaining: time.StretchedTime,
    ) -> trades.TradeResult:
        """Calculate fees and asset quantity adjustments"""
        raise NotImplementedError

    def calc_out_given_in(
        self,
        in_: types.Quantity,
        market_state: HyperdriveMarketState,
        time_remaining: time.StretchedTime,
    ) -> trades.TradeResult:
        """Calculate fees and asset quantity adjustments"""
        raise NotImplementedError

    def calc_lp_out_given_tokens_in(
        self,
        d_base: FixedPoint,
        rate: FixedPoint,
        market_state: HyperdriveMarketState,
        time_remaining: time.StretchedTime,
    ) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
        """Computes the amount of LP tokens to be minted for a given amount of base asset"""
        raise NotImplementedError

    def calc_tokens_out_given_lp_in(
        self,
        lp_in: FixedPoint,
        market_state: HyperdriveMarketState,
    ) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
        """Calculate how many tokens should be returned for a given lp addition"""
        raise NotImplementedError

    def model_name(self) -> str:
        """Unique name given to the model, can be based on member variable states"""
        raise NotImplementedError

    def model_type(self) -> str:
        """Unique identifier given to the model, should be lower snake_cased name"""
        raise NotImplementedError

    def calc_initial_bond_reserves(
        self,
        target_apr: FixedPoint,
        time_remaining: time.StretchedTime,
        market_state: HyperdriveMarketState,
    ) -> FixedPoint:
        """Returns the assumed bond (i.e. token asset) reserve amounts given
        the share (i.e. base asset) reserves and APR for an initialized market

        Arguments
        ----------
        target_apr : FixedPoint
            Target fixed APR in decimal units (for example, 5% APR would be 0.05)
        time_remaining : StretchedTime
            Amount of time left until bond maturity
        market_state : MarketState
            MarketState object; the following attributes are used:
                share_reserves : FixedPoint
                    Base asset reserves in the pool
                init_share_price : FixedPoint
                    Original share price when the pool started
                share_price : FixedPoint
                    Current share price

        Returns
        -------
        FixedPoint
            The expected amount of bonds (token asset) in the pool, given the inputs

        .. todo:: test_market.test_initialize_market uses this, but this should also have a unit test
        """
        # Only want to renormalize time for APR ("annual", so hard coded to 365)
        # Don't want to renormalize stretched time
        annualized_time = time_remaining.days / FixedPoint("365.0")
        # y = z/2 * (mu * (1 + rt)**(1/tau) - c)
        return (market_state.share_reserves / FixedPoint("2.0")) * (
            market_state.init_share_price
            * (FixedPoint("1.0") + target_apr * annualized_time) ** (FixedPoint("1.0") / time_remaining.stretched_time)
            - market_state.share_price
        )

    def calc_bond_reserves(
        self,
        target_apr: FixedPoint,
        time_remaining: time.StretchedTime,
        market_state: HyperdriveMarketState,
    ) -> FixedPoint:
        """Returns the assumed bond (i.e. token asset) reserve amounts given
        the share (i.e. base asset) reserves and APR

        Arguments
        ----------
        target_apr : FixedPoint
            Target fixed APR in decimal units (for example, 5% APR would be 0.05)
        time_remaining : StretchedTime
            Amount of time left until bond maturity
        market_state : MarketState
            MarketState object; the following attributes are used:
                share_reserves : FixedPoint
                    Base asset reserves in the pool
                init_share_price : FixedPoint
                    Original share price when the pool started
                share_price : FixedPoint
                    Current share price

        Returns
        -------
        FixedPoint
            The expected amount of bonds (token asset) in the pool, given the inputs

        .. todo:: Test this function
        """
        # Only want to renormalize time for APR ("annual", so hard coded to 365)
        annualized_time = time_remaining.days / FixedPoint("365.0")
        # (1 + r * t) ** (1 / tau)
        interest_factor = (FixedPoint("1.0") + target_apr * annualized_time) ** (
            FixedPoint("1.0") / time_remaining.stretched_time
        )
        # mu * z * (1 + apr * t) ** (1 / tau) - l
        return (
            market_state.init_share_price * market_state.share_reserves * interest_factor - market_state.lp_total_supply
        )

    def calc_spot_price_from_reserves(
        self,
        market_state: HyperdriveMarketState,
        time_remaining: time.StretchedTime,
    ) -> FixedPoint:
        r"""Calculates the spot price of base in terms of bonds.
        The spot price is defined as:

        .. math::
            \begin{align}
                p &= (\frac{y + s}{\mu z})^{-\tau} \\
                  &= (\frac{\mu z}{y + s})^{\tau}
            \end{align}

        Arguments
        ----------
        market_state : MarketState
            The reserves and prices in the pool.
        time_remaining : StretchedTime
            The time remaining for the asset (uses time stretch).

        Returns
        -------
        FixedPoint
            The spot price of principal tokens.
        """
        # avoid div by zero error
        if market_state.bond_reserves + market_state.lp_total_supply <= FixedPoint(0):
            return FixedPoint("nan")
        # p = ((mu * z) / (y + s))^(tau)
        return (
            (market_state.init_share_price * market_state.share_reserves)
            / (market_state.bond_reserves + market_state.lp_total_supply)
        ) ** time_remaining.stretched_time

    def calc_apr_from_reserves(
        self,
        market_state: HyperdriveMarketState,
        time_remaining: time.StretchedTime,
    ) -> FixedPoint:
        r"""Returns the apr given reserve amounts

        Arguments
        ----------
        market_state : MarketState
            The reserves and share prices of the pool
        time_remaining : StretchedTime
            The expiry time for the asset
        """
        spot_price = self.calc_spot_price_from_reserves(
            market_state,
            time_remaining,
        )
        return price_utils.calc_apr_from_spot_price(spot_price, time_remaining)

    def calc_time_stretch(self, apr: FixedPoint) -> FixedPoint:
        """Returns fixed time-stretch value based on current apr (as a FixedPoint)"""
        apr_percent = apr * FixedPoint("100.0")  # bounded between 0 and 100
        return FixedPoint("3.09396") / (
            FixedPoint("0.02789") * apr_percent
        )  # bounded between ~1.109 (apr=1) and inf (apr=0)

    def check_input_assertions(
        self,
        quantity: types.Quantity,
        market_state: HyperdriveMarketState,
        time_remaining: time.StretchedTime,
    ):
        """Applies a set of assertions to the input of a trading function."""
        assert time_remaining.normalized_time <= 1
        assert quantity.amount >= elfpy.WEI, f"expected quantity.amount >= {elfpy.WEI}, not {quantity.amount}!"
        assert market_state.share_reserves >= FixedPoint(
            "0.0"
        ), f"expected share_reserves >= 0, not {market_state.share_reserves}!"
        assert market_state.bond_reserves >= FixedPoint("0.0"), (
            f"expected bond_reserves >= 0" f" bond_reserves == 0, not {market_state.bond_reserves}!"
        )
        if market_state.share_price < market_state.init_share_price:
            logging.warning(
                "WARNING: expected share_price >= %g, not share_price=%g",
                market_state.init_share_price,
                market_state.share_price,
            )
        assert market_state.init_share_price >= FixedPoint(
            "1.0"
        ), f"expected init_share_price >= 1, not share_price={market_state.init_share_price}"
        reserves_difference = abs(market_state.share_reserves * market_state.share_price - market_state.bond_reserves)
        assert reserves_difference < elfpy.MAX_RESERVES_DIFFERENCE, (
            f"expected reserves_difference = abs(share_reserves * share_price - bond_reserves) "
            f"to be < {elfpy.MAX_RESERVES_DIFFERENCE}, not {reserves_difference}!"
        )
        assert (
            FixedPoint("1.0") >= market_state.curve_fee_multiple >= FixedPoint("0.0")
        ), f"expected 1 >= curve_fee_multiple >= 0, not {market_state.curve_fee_multiple}!"
        assert (
            FixedPoint("1.0") >= market_state.flat_fee_multiple >= FixedPoint("0.0")
        ), f"expected 1 >= flat_fee_multiple >= 0, not {market_state.flat_fee_multiple}!"
        assert (
            FixedPoint("1.0") + elfpy.PRECISION_THRESHOLD >= time_remaining.stretched_time >= -elfpy.PRECISION_THRESHOLD
        ), (
            f"expected {1 + int(elfpy.PRECISION_THRESHOLD)} > "
            f"time_remaining.stretched_time >= {-int(elfpy.PRECISION_THRESHOLD)}"
            f", not {time_remaining.stretched_time}!"
        )
        assert (
            FixedPoint("1.0") + elfpy.PRECISION_THRESHOLD
            >= time_remaining.normalized_time
            >= -elfpy.PRECISION_THRESHOLD
        ), (
            f"expected {1 + int(elfpy.PRECISION_THRESHOLD)} > time_remaining >= {-int(elfpy.PRECISION_THRESHOLD)}"
            f", not {time_remaining.normalized_time}!"
        )

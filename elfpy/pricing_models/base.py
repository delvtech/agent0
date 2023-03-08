"""The base pricing model"""
from __future__ import annotations  # types will be strings by default in 3.11

from abc import ABC
from decimal import Decimal, getcontext
from typing import TYPE_CHECKING

from elfpy import (
    MAX_RESERVES_DIFFERENCE,
    WEI,
)
import elfpy.pricing_models.trades as trades
import elfpy.utils.price as price_utils
import elfpy.time as time
import elfpy.types as types

if TYPE_CHECKING:
    import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market


# Set the Decimal precision to be higher than the default of 28. This ensures
# that the pricing models can safely a lowest possible input of 1e-18 with an
# reserves difference of up to 20 billion.
getcontext().prec = 30


class PricingModel(ABC):
    """Contains functions for calculating AMM variables

    Base class should not be instantiated on its own; it is assumed that a user will instantiate a child class
    """

    def calc_in_given_out(
        self,
        out: types.Quantity,
        market_state: hyperdrive_market.MarketState,
        time_remaining: time.StretchedTime,
    ) -> trades.TradeResult:
        """Calculate fees and asset quantity adjustments"""
        raise NotImplementedError

    def calc_out_given_in(
        self,
        in_: types.Quantity,
        market_state: hyperdrive_market.MarketState,
        time_remaining: time.StretchedTime,
    ) -> trades.TradeResult:
        """Calculate fees and asset quantity adjustments"""
        raise NotImplementedError

    def calc_lp_out_given_tokens_in(
        self,
        d_base: float,
        rate: float,
        market_state: hyperdrive_market.MarketState,
        time_remaining: time.StretchedTime,
    ) -> tuple[float, float, float]:
        """Computes the amount of LP tokens to be minted for a given amount of base asset"""
        raise NotImplementedError

    def calc_lp_in_given_tokens_out(
        self,
        d_base: float,
        rate: float,
        market_state: hyperdrive_market.MarketState,
        time_remaining: time.StretchedTime,
    ) -> tuple[float, float, float]:
        """Computes the amount of LP tokens to be minted for a given amount of base asset"""
        raise NotImplementedError

    def calc_tokens_out_given_lp_in(
        self,
        lp_in: float,
        rate: float,
        market_state: hyperdrive_market.MarketState,
        time_remaining: time.StretchedTime,
    ) -> tuple[float, float, float]:
        """Calculate how many tokens should be returned for a given lp addition"""
        raise NotImplementedError

    def model_name(self) -> str:
        """Unique name given to the model, can be based on member variable states"""
        raise NotImplementedError

    def model_type(self) -> str:
        """Unique identifier given to the model, should be lower snake_cased name"""
        raise NotImplementedError

    def _calc_k_const(self, market_state: hyperdrive_market.MarketState, time_remaining: time.StretchedTime) -> Decimal:
        """Returns the 'k' constant variable for trade mathematics"""
        raise NotImplementedError

    def calc_bond_reserves(
        self,
        target_apr: float,
        time_remaining: time.StretchedTime,
        market_state: hyperdrive_market.MarketState,
    ) -> float:
        """Returns the assumed bond (i.e. token asset) reserve amounts given
        the share (i.e. base asset) reserves and APR

        Parameters
        ----------
        target_apr : float
            Target fixed APR in decimal units (for example, 5% APR would be 0.05)
        time_remaining : StretchedTime
            Amount of time left until bond maturity
        market_state : MarketState
            MarketState object; the following attributes are used:
                share_reserves : float
                    Base asset reserves in the pool
                init_share_price : float
                    Original share price when the pool started
                share_price : float
                    Current share price

        Returns
        -------
        float
            The expected amount of bonds (token asset) in the pool, given the inputs

        .. todo:: test_market.test_initialize_market uses this, but this should also have a unit test
        """
        # Only want to renormalize time for APR ("annual", so hard coded to 365)
        # Don't want to renormalize stretched time
        annualized_time = time.norm_days(time_remaining.days, 365)
        bond_reserves = (market_state.share_reserves / 2) * (
            market_state.init_share_price * (1 + target_apr * annualized_time) ** (1 / time_remaining.stretched_time)
            - market_state.share_price
        )  # y = z/2 * (mu * (1 + rt)**(1/tau) - c)
        return bond_reserves

    def calc_share_reserves(
        self,
        target_apr: float,
        bond_reserves: float,
        time_remaining: time.StretchedTime,
        init_share_price: float = 1,
    ):
        """Returns the assumed share (i.e. base asset) reserve amounts given
        the bond (i.e. token asset) reserves and APR

        Parameters
        ----------
        target_apr : float
            Target fixed APR in decimal units (for example, 5% APR would be 0.05)
        bond_reserves : float
            Token asset (pt) reserves in the pool
        days_remaining : float
            Amount of days left until bond maturity
        time_stretch : float
            Time stretch parameter, in years
        init_share_price : float
            Original share price when the pool started
        share_price : float
            Current share price

        Returns
        -------
        float
            The expected amount of base asset in the pool, calculated from the provided parameters

        .. todo:: Write a test for this function
        """
        # y = (z / 2) * (mu * (1 + rt)**(1/tau) - c)
        # z = (2 * y) / (mu * (1 + rt)**(1/tau) - c)
        # Only want to renormalize time for APR ("annual", so hard coded to 365)
        # Don't want to renormalize stretched time
        annualized_time = time.norm_days(time_remaining.days, 365)
        share_reserves = (
            2
            * bond_reserves
            / (
                init_share_price * (1 - target_apr * annualized_time) ** (1 / time_remaining.stretched_time)
                - init_share_price
            )
        )
        return share_reserves

    def calc_base_for_target_apr(
        self,
        target_apr: float,
        bond: float,
        position_duration: time.StretchedTime,
        share_price: float = 1.0,
    ) -> float:
        """Returns the base required to buy the given bonds at the target APR
        For a long, this is maximum amount of base in required to get the given bonds out.
        For a short, this is the minimum amount of base out for the given bonds in.

        Parameters
        ----------
        target_apr : float
            Target fixed APR in decimal units (for example, 5% APR would be 0.05)
        bond_out: float
            The amount of bonds to purchase
        position_duration: StretchedTime
            The term length of the bond
        share_price : float
            The current share price

        Returns
        -------
        float
            The base amount for a given bond at the target_apr.
        """
        # delta_z / delta_y = p = 1 - r
        # delta_z = delta_y * (1 - r)
        # delta_x = c * delta_y * (1 - r)
        # Only want to renormalize time for APR ("annual", so hard coded to 365)
        # Don't want to renormalize stretched time
        annualized_time = time.norm_days(position_duration.days, 365)
        base = share_price * bond * (1 - target_apr * annualized_time)
        assert base >= 0, "base value negative"
        return base

    def calc_bond_for_target_apr(
        self,
        target_apr: float,
        base: float,
        position_duration: time.StretchedTime,
        share_price: float = 1.0,
    ) -> float:
        """Returns the bonds for a given base at the target APR.
        For a long this is the minimum amount of bonds out for a given base in.
        For a short this is the maximum amount of base in for a given base out.

        Parameters
        ----------
        target_apr : float
            Target fixed APR in decimal units (for example, 5% APR would be 0.05)
        bond_out: float
            The amount of bonds to purchase
        position_duration: StretchedTime
            The term length of the bond
        share_price : float
            The current share price

        Returns
        -------
        float
            The bond amount for a given base in at the target APR
        """
        # delta_z / delta_y = p = 1 - r
        # delta_y = delta_z / (1 - r)
        # delta_y = (delta_x / c) / (1 - r)
        # Only want to renormalize time for APR ("annual", so hard coded to 365)
        # Don't want to renormalize stretched time
        annualized_time = time.norm_days(position_duration.days, 365)
        bond = (base / share_price) / (1 - target_apr * annualized_time)
        assert bond >= 0, "bond value negative"
        return bond

    def calc_total_liquidity_from_reserves_and_price(
        self, market_state: hyperdrive_market.MarketState, share_price: float
    ) -> float:
        """Returns the total liquidity in the pool in terms of base

        Parameters
        ----------
        MarketState : MarketState
            The following member variables are used:
                share_reserves : float
                    Base asset reserves in the pool
                bond_reserves : float
                    Token asset (pt) reserves in the pool
        share_price : float
            Variable (underlying) yield source price

        Returns
        -------
        float
            Total liquidity in the pool in terms of base, calculated from the provided parameters

        .. todo:: Write a test for this function
        """
        return market_state.share_reserves * share_price

    def calc_spot_price_from_reserves(
        self,
        market_state: hyperdrive_market.MarketState,
        time_remaining: time.StretchedTime,
    ) -> float:
        r"""
        Calculates the spot price of base in terms of bonds.

        The spot price is defined as:

        .. math::
            \begin{align}
            p = (\frac{2y + cz}{\mu z})^{-\tau}
            \end{align}

        Parameters
        ----------
        market_state: MarketState
            The reserves and share prices of the pool.
        time_remaining : StretchedTime
            The time remaining for the asset (uses time stretch).

        Returns
        -------
        float
            The spot price of principal tokens.
        """
        return float(
            self._calc_spot_price_from_reserves_high_precision(market_state=market_state, time_remaining=time_remaining)
        )

    def _calc_spot_price_from_reserves_high_precision(
        self,
        market_state: hyperdrive_market.MarketState,
        time_remaining: time.StretchedTime,
    ) -> Decimal:
        r"""
        Calculates the current market spot price of base in terms of bonds.
        This variant returns the result in a high precision format.

        The spot price is defined as:

        .. math::
            \begin{align}
            p = (\frac{2y + cz}{\mu z})^{-\tau}
            \end{align}

        Parameters
        ----------
        market_state: MarketState
            The reserves and share prices of the pool.
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch).

        Returns
        -------
        Decimal
            The spot price of principal tokens.
        """
        # TODO: in general s != y + c*z, we'll want to update this to have s = lp_total_supply
        # issue #94
        # s = y + c*z
        total_reserves = Decimal(market_state.bond_reserves) + Decimal(market_state.share_price) * Decimal(
            market_state.share_reserves
        )
        # p = ((y + s)/(mu*z))^(-tau) = ((2y + cz)/(mu*z))^(-tau)
        spot_price = (
            (Decimal(market_state.bond_reserves) + total_reserves)
            / (Decimal(market_state.init_share_price) * Decimal(market_state.share_reserves))
        ) ** Decimal(-time_remaining.stretched_time)
        return spot_price

    def calc_apr_from_reserves(
        self,
        market_state: hyperdrive_market.MarketState,
        time_remaining: time.StretchedTime,
    ) -> float:
        r"""Returns the apr given reserve amounts

        Parameters
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

    def get_max_long(
        self,
        market_state: hyperdrive_market.MarketState,
        time_remaining: time.StretchedTime,
    ) -> tuple[float, float]:
        r"""
        Calculates the maximum long the market can support

        .. math::
            \begin{align}
            \Delta z' = \mu^{-1} \cdot (\frac{\mu}{c} \cdot (k-(y+c \cdot z)^{1-\tau(d)}))^{\frac{1}{1-\tau(d)}}
            -c \cdot z
            \end{align}

        Parameters
        ----------
        market_state : MarketState
            The reserves and share prices of the pool
        fee_percent : float
            The fee percent charged by the market
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch)

        Returns
        -------
        float
            The maximum amount of base that can be used to purchase bonds.
        float
            The maximum amount of bonds that can be purchased.
        """
        base = self.calc_in_given_out(
            out=types.Quantity(market_state.bond_reserves - market_state.bond_buffer, unit=types.TokenType.PT),
            market_state=market_state,
            time_remaining=time_remaining,
        ).breakdown.with_fee
        bonds = self.calc_out_given_in(
            in_=types.Quantity(amount=base, unit=types.TokenType.BASE),
            market_state=market_state,
            time_remaining=time_remaining,
        ).breakdown.with_fee
        return (base, bonds)

    def get_max_short(
        self,
        market_state: hyperdrive_market.MarketState,
        time_remaining: time.StretchedTime,
    ) -> tuple[float, float]:
        r"""
        Calculates the maximum short the market can support using the bisection
        method.

        \begin{align}
        \Delta y' = \mu^{-1} \cdot (\frac{\mu}{c} \cdot k)^{\frac{1}{1-\tau(d)}}-2y-c \cdot z
        \end{align}

        Parameters
        ----------
        market_state : MarketState
            The reserves and share prices of the pool.
        fee_percent : float
            The fee percent charged by the market.
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch).

        Returns
        -------
        float
            The max loss associated with the maximum short, that a short seller needs to cover.
        float
            The maximum amount of bonds that can be shorted.
        """
        base_amount = market_state.share_reserves * market_state.share_price - market_state.base_buffer
        max_short_pt = self.calc_in_given_out(
            out=types.Quantity(
                base_amount,
                unit=types.TokenType.BASE,
            ),
            market_state=market_state,
            time_remaining=time_remaining,
        ).breakdown.without_fee
        max_short_max_loss = max_short_pt - base_amount
        return max_short_max_loss, max_short_pt

    def calc_time_stretch(self, apr) -> float:
        """Returns fixed time-stretch value based on current apr (as a decimal)"""
        apr_percent = apr * 100  # bounded between 0 and 100
        return 3.09396 / (0.02789 * apr_percent)  # bounded between ~1.109 (apr=1) and inf (apr=0)

    def check_input_assertions(
        self,
        quantity: types.Quantity,
        market_state: hyperdrive_market.MarketState,
        time_remaining: time.StretchedTime,
    ):
        """Applies a set of assertions to the input of a trading function."""

        assert quantity.amount >= WEI, (
            "pricing_models.check_input_assertions: ERROR: "
            f"expected quantity.amount >= {WEI}, not {quantity.amount}!"
        )
        assert market_state.share_reserves >= 0, (
            "pricing_models.check_input_assertions: ERROR: "
            f"expected share_reserves >= {WEI}, not {market_state.share_reserves}!"
        )
        assert market_state.bond_reserves >= 0, (
            "pricing_models.check_input_assertions: ERROR: "
            f"expected bond_reserves >= {WEI} or bond_reserves == 0, not {market_state.bond_reserves}!"
        )
        assert market_state.share_price >= market_state.init_share_price, (
            f"pricing_models.check_input_assertions: ERROR: "
            f"expected share_price >= {market_state.init_share_price}, not share_price={market_state.share_price}"
        )
        assert market_state.init_share_price >= 1, (
            f"pricing_models.check_input_assertions: ERROR: "
            f"expected init_share_price >= 1, not share_price={market_state.init_share_price}"
        )
        reserves_difference = abs(market_state.share_reserves * market_state.share_price - market_state.bond_reserves)
        assert reserves_difference < MAX_RESERVES_DIFFERENCE, (
            "pricing_models.check_input_assertions: ERROR: "
            f"expected reserves_difference < {MAX_RESERVES_DIFFERENCE}, not {reserves_difference}!"
        )
        assert 1 >= market_state.trade_fee_percent >= 0, (
            "pricing_models.check_input_assertions: ERROR: "
            f"expected 1 >= trade_fee_percent >= 0, not {market_state.trade_fee_percent}!"
        )
        assert 1 >= market_state.redemption_fee_percent >= 0, (
            "pricing_models.check_input_assertions: ERROR: "
            f"expected 1 >= redemption_fee_percent >= 0, not {market_state.redemption_fee_percent}!"
        )
        assert 1 >= time_remaining.stretched_time >= 0, (
            "pricing_models.check_input_assertions: ERROR: "
            f"expected 1 > time_remaining.stretched_time >= 0, not {time_remaining.stretched_time}!"
        )
        assert 1 >= time_remaining.normalized_time >= 0, (
            "pricing_models.check_input_assertions: ERROR: "
            f"expected 1 > time_remaining >= 0, not {time_remaining.normalized_time}!"
        )

    # TODO: Add checks for TradeResult's other outputs.
    # issue #57
    def check_output_assertions(
        self,
        trade_result: trades.TradeResult,
    ):
        """Applies a set of assertions to a trade result."""

        assert isinstance(trade_result.breakdown.fee, float), (
            "pricing_models.check_output_assertions: ERROR: "
            f"fee should be a float, not {type(trade_result.breakdown.fee)}!"
        )
        assert trade_result.breakdown.fee >= 0, (
            "pricing_models.check_output_assertions: ERROR: "
            f"Fee should not be negative, but is {trade_result.breakdown.fee}!"
        )
        assert isinstance(trade_result.breakdown.without_fee, float), (
            "pricing_models.check_output_assertions: ERROR: "
            f"without_fee should be a float, not {type(trade_result.breakdown.without_fee)}!"
        )
        assert trade_result.breakdown.without_fee >= 0, (
            "pricing_models.check_output_assertions: ERROR: "
            f"without_fee should be non-negative, not {trade_result.breakdown.without_fee}!"
        )

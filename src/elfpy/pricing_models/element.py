"""The Element pricing model."""

import logging
from elfpy.pricing_models.base import PricingModel

from elfpy.types import (
    MarketTradeResult,
    Quantity,
    MarketState,
    StretchedTime,
    TradeBreakdown,
    TradeResult,
    UserTradeResult,
)
import elfpy.utils.price as price_utils


class ElementPricingModel(PricingModel):
    """
    Element v1 pricing model
    Does not use the Yield Bearing Vault `init_share_price` (μ) and `share_price` (c) variables.
    TODO: Update element pricing model to include lp calcs
    """

    # TODO: The too many locals disable can be removed after refactoring the LP
    #       functions.
    #
    # pylint: disable=line-too-long
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=duplicate-code

    def calc_lp_out_given_tokens_in(
        self,
        d_base: float,
        share_reserves: float,
        bond_reserves: float,
        share_buffer: float,
        init_share_price: float,
        share_price: float,
        lp_reserves: float,
        rate: float,
        time_remaining: StretchedTime,
        stretched_time_remaining: StretchedTime,
    ) -> tuple[float, float, float]:
        raise NotImplementedError

    def calc_lp_in_given_tokens_out(
        self,
        d_base: float,
        share_reserves: float,
        bond_reserves: float,
        share_buffer: float,
        init_share_price: float,
        share_price: float,
        lp_reserves: float,
        rate: float,
        time_remaining: StretchedTime,
        stretched_time_remaining: StretchedTime,
    ) -> tuple[float, float, float]:
        raise NotImplementedError

    def calc_tokens_out_given_lp_in(
        self,
        lp_in: float,
        share_reserves: float,
        bond_reserves: float,
        share_buffer: float,
        init_share_price: float,
        share_price: float,
        lp_reserves: float,
        rate: float,
        time_remaining: StretchedTime,
        stretched_time_remaining: StretchedTime,
    ) -> tuple[float, float, float]:
        raise NotImplementedError

    def model_name(self) -> str:
        return "Element"

    def calc_in_given_out(
        self,
        out: Quantity,
        market_state: MarketState,
        fee_percent: float,
        time_remaining: StretchedTime,
    ) -> TradeResult:
        r"""
        Calculates the amount of an asset that must be provided to receive a
        specified amount of the other asset given the current AMM reserves.

        The input is calculated as:

        .. math::
            in' =
            \begin{cases}
            (\frac{k - (2y + x - \Delta y)^{1 - \tau}})^{\frac{1}{1 - \tau}} -
             x, &\text{ if } token\_in = \text{"base"} \\
            (k - (x - \Delta x)^{1 - \tau})^{\frac{1}{1 - \tau}} - (2y + x), &\text{ if } token\_in = \text{"pt"}
            \end{cases} \\
            f =
            \begin{cases}
            (\Delta y - in') \cdot \phi, &\text{ if } token\_in = \text{"base"} \\
            (in' - \Delta x) \cdot \phi, &\text{ if } token\_in = \text{"pt"}
            \end{cases} \\
            in = in' + f

        Arguments
        ---------
        out : Quantity
            The quantity of tokens that the user wants to receive (the amount
            and the unit of the tokens).
        market_state : MarketState
            The state of the AMM's reserves and share prices.
        fee_percent : float
            The percentage of the difference between the amount paid without
            slippage and the amount received that will be added to the input
            as a fee.
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch).

        Returns
        -------
        float
            The amount the user pays without fees or slippage. The units
            are always in terms of bonds or base.
        float
            The amount the user pays with fees and slippage. The units are
            always in terms of bonds or base.
        float
            The amount the user pays with slippage and no fees. The units are
            always in terms of bonds or base.
        float
            The fee the user pays. The units are always in terms of bonds or
            base.
        """

        time_elapsed = 1 - time_remaining.stretched_time
        bond_reserves_ = 2 * market_state.bond_reserves + market_state.share_reserves
        spot_price = self.calc_spot_price_from_reserves(market_state, time_remaining)
        # We precompute the YieldSpace constant k using the current reserves and
        # share price:
        #
        # k = (c / μ) * (μ * z)**(1 - t) + (2y + cz)**(1 - t)
        k = price_utils.calc_k_const(market_state, time_elapsed)
        # Solve for the amount that must be paid to receive the specified amount
        # of the output.
        if out.unit == "base":
            d_base = out.amount

            # The amount the user pays without fees or slippage is the amount of
            # bonds the user receives times the inverse of the spot price
            # of base in terms of bonds. If we let p be the conventional spot
            # price, then we can write this as:
            #
            # without_fee_or_slippage = (1 / p) * d_x
            without_fee_or_slippage = (1 / spot_price) * d_base

            # We solve the YieldSpace invariant for the bonds required to
            # purchase the requested amount of base. We set up the invariant
            # where the user pays d_y bonds and receives d_x base:
            #
            # (x - d_x)**(1 - t) + (2y + x + d_y')**(1 - t) = k
            #
            # Solving for d_y' gives us the amount of bonds the user must pay
            # without including fees:
            #
            # d_y' = (k - (x - d_x)**(1 - t))**(1 / (1 - t)) - (2y + x)
            #
            # without_fee = d_y'
            without_fee = (k - (market_state.share_reserves - d_base) ** time_elapsed) ** (
                1 / time_elapsed
            ) - bond_reserves_

            # The fees are calculated as the difference between the bonds
            # paid without fees and the base received times the fee percentage.
            # This can also be expressed as:
            #
            # fee = phi * (d_y' - d_x)
            fee = fee_percent * (without_fee - d_base)

            # To get the amount paid with fees, add the fee to the calculation that
            # excluded fees. Adding the fees results in more tokens paid, which
            # indicates that the fees are working correctly.
            with_fee = without_fee + fee

            # Create the user and market trade results.
            user_result = UserTradeResult(
                d_base=out.amount,
                d_bonds=-with_fee,
            )
            market_result = MarketTradeResult(
                d_base=-out.amount,
                d_bonds=with_fee,
            )
        elif out.unit == "pt":
            d_bonds = out.amount

            # The amount the user pays without fees or slippage is the amount of
            # bonds the user receives times the spot price of base in terms
            # of bonds. If we let p be the conventional spot price, then we can
            # write this as:
            #
            # without_fee_or_slippage = p * d_y
            without_fee_or_slippage = spot_price * d_bonds

            # We solve the YieldSpace invariant for the base required to
            # purchase the requested amount of bonds. We set up the invariant
            # where the user pays d_x' base and receives d_y bonds:
            #
            # (x + d_x')**(1 - t) + (2y + x - d_y)**(1 - t) = k
            #
            # Solving for d_x' gives us the amount of base the user must pay
            # without including fees:
            #
            # d_x' = (k - (2y + x - d_y)**(1 - t))**(1 / (1 - t)) - x
            #
            # without_fee = d_x'
            without_fee = (k - (bond_reserves_ - d_bonds) ** time_elapsed) ** (
                1 / time_elapsed
            ) - market_state.share_reserves

            # The fees are calculated as the difference between the bonds
            # received and the base paid without fees times the fee percentage.
            # This can also be expressed as:
            #
            # fee = phi * (d_y - d_x')
            fee = fee_percent * (d_bonds - without_fee)

            # To get the amount paid with fees, add the fee to the calculation that
            # excluded fees. Adding the fees results in more tokens paid, which
            # indicates that the fees are working correctly.
            with_fee = without_fee + fee

            # Create the user and market trade results.
            user_result = UserTradeResult(
                d_base=-with_fee,
                d_bonds=out.amount,
            )
            market_result = MarketTradeResult(
                d_base=with_fee,
                d_bonds=-out.amount,
            )
        else:
            raise AssertionError(
                f'pricing_models.calc_in_given_out: ERROR: expected token_in to be "base" or "pt", not {out.unit}!'
            )

        logging.debug(
            (
                "\n\tout = %s\n\tshare_reserves = %d\n\tbond_reserves = %d"
                "\n\ttotal_reserves = %d\n\tinit_share_price = %g"
                "\n\tshare_price = %d\n\tfee_percent = %g"
                "\n\ttime_remaining = %s\n\ttime_elapsed = %g"
                "\n\tspot_price = %g\n\tk = %g\n\twithout_fee_or_slippage = %s"
                "\n\twithout_fee = %s\n\twith_fee = %s\n\tfee = %s"
            ),
            out,
            market_state.share_reserves,
            market_state.bond_reserves,
            market_state.share_reserves + market_state.bond_reserves,
            market_state.init_share_price,
            market_state.share_price,
            fee_percent,
            time_remaining,
            time_elapsed,
            spot_price,
            k,
            without_fee_or_slippage,
            without_fee,
            with_fee,
            fee,
        )

        return TradeResult(
            user_result=user_result,
            market_result=market_result,
            breakdown=TradeBreakdown(
                without_fee_or_slippage=without_fee_or_slippage,
                with_fee=with_fee,
                without_fee=without_fee,
                fee=fee,
            ),
        )

    def calc_out_given_in(
        self,
        in_: Quantity,
        market_state: MarketState,
        fee_percent: float,
        time_remaining: StretchedTime,
    ) -> TradeResult:
        r"""
        Calculates the amount of an asset that must be provided to receive a
        specified amount of the other asset given the current AMM reserves.

        The output is calculated as:

        .. math::
            out' =
            \begin{cases}
            (x - (k - (2y + x + \Delta y)^{1 - \tau})^{\frac{1}{1 - \tau}}), &\text{ if } token\_out = \text{"base"} \\
            2y + x - (k - (x + \Delta x)^{1 - \tau})^{\frac{1}{1 - \tau}}, &\text{ if } token\_out = \text{"pt"}
            \end{cases} \\
            f =
            \begin{cases}
            (\Delta y - out') \cdot \phi, &\text{ if } token\_out = \text{"base"} \\
            (out' - \Delta x) \cdot \phi, &\text{ if } token\_out = \text{"pt"}
            \end{cases} \\
            out = out' + f

        Arguments
        in_ : Quantity
            The quantity of tokens that the user wants to pay (the amount
            and the unit of the tokens).
        market_state : MarketState
            The state of the AMM's reserves and share prices.
        fee_percent : float
            The percentage of the difference between the amount paid without
            slippage and the amount received that will be added to the input
            as a fee.
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch).

        Returns
        -------
        float
            The amount the user receives without fees or slippage. The units
            are always in terms of bonds or base.
        float
            The amount the user receives with fees and slippage. The units are
            always in terms of bonds or base.
        float
            The amount the user receives with slippage and no fees. The units are
            always in terms of bonds or base.
        float
            The fee the user pays. The units are always in terms of bonds or
            base.
        """

        time_elapsed = 1 - time_remaining.stretched_time
        bond_reserves_ = 2 * market_state.bond_reserves + market_state.share_reserves
        spot_price = self.calc_spot_price_from_reserves(market_state, time_remaining)
        # We precompute the YieldSpace constant k using the current reserves and
        # share price:
        #
        # k = x**(1 - t) + (2y + x)**(1 - t)
        k = price_utils.calc_k_const(market_state, time_elapsed)
        # Solve for the amount that received if the specified amount is paid.
        if in_.unit == "base":
            d_base = in_.amount

            # The amount the user pays without fees or slippage is the amount of
            # base the user pays times the inverse of the spot price of base in
            # terms of bonds. If we let p be the conventional spot price, then
            # we can write this as:
            #
            # without_fee_or_slippage = (1 / p) * d_x
            without_fee_or_slippage = (1 / spot_price) * d_base

            # We solve the YieldSpace invariant for the bonds received from
            # paying the specified amount of base. We set up the invariant
            # where the user pays d_x base and receives d_y' bonds:
            #
            # (x + d_x)**(1 - t) + (2y + x - d_y')**(1 - t) = k
            #
            # Solving for d_x' gives us the amount of base the user must pay
            # without including fees:
            #
            # d_y' = 2y + x - (k - (x + d_x)**(1 - t))**(1 / (1 - t))
            #
            # without_fee = d_x'
            without_fee = bond_reserves_ - (k - (market_state.share_reserves + d_base) ** time_elapsed) ** (
                1 / time_elapsed
            )

            # The fees are calculated as the difference between the bonds paid
            # and the base received without fees times the fee percentage. This
            # can also be expressed as:
            #
            # fee = phi * (d_y' - d_x)
            fee = fee_percent * (without_fee - d_base)

            # To get the amount paid with fees, subtract the fee from the
            # calculation that excluded fees. Subtracting the fees results in less
            # tokens received, which indicates that the fees are working correctly.
            with_fee = without_fee - fee

            # Create the user and market trade results.
            user_result = UserTradeResult(
                d_base=-in_.amount,
                d_bonds=with_fee,
            )
            market_result = MarketTradeResult(
                d_base=in_.amount,
                d_bonds=-with_fee,
            )
        elif in_.unit == "pt":
            d_bonds = in_.amount

            # The amount the user pays without fees or slippage is the amount of
            # bonds the user pays times the spot price of base in terms of bonds.
            # If we let p be the conventional spot price, then we can write this
            # as:
            #
            # without_fee_or_slippage = p * d_y
            without_fee_or_slippage = spot_price * d_bonds

            # We solve the YieldSpace invariant for the base received from
            # paying the specified amount of bonds. We set up the invariant
            # where the user pays d_y bonds and receives d_x' base:
            #
            # (x - d_x')**(1 - t) + (2y + x + d_y)**(1 - t) = k
            #
            # Solving for d_x' gives us the amount of base the user must pay
            # without including fees:
            #
            # d_x' = x - (k - (2y + x + d_y)**(1 - t))**(1 / (1 - t))
            #
            # without_fee = d_x'
            without_fee = market_state.share_reserves - (k - (bond_reserves_ + d_bonds) ** time_elapsed) ** (
                1 / time_elapsed
            )

            # The fees are calculated as the difference between the bonds paid
            # and the base received without fees times the fee percentage. This
            # can also be expressed as:
            #
            # fee = phi * (d_y - d_x')
            fee = fee_percent * (d_bonds - without_fee)

            # To get the amount paid with fees, subtract the fee from the
            # calculation that excluded fees. Subtracting the fees results in less
            # tokens received, which indicates that the fees are working correctly.
            with_fee = without_fee - fee

            # Create the user and market trade results.
            user_result = UserTradeResult(
                d_base=with_fee,
                d_bonds=-in_.amount,
            )
            market_result = MarketTradeResult(
                d_base=-with_fee,
                d_bonds=in_.amount,
            )
        else:
            raise AssertionError(
                f'pricing_models.calc_out_given_in: ERROR: expected token_out to be "base" or "pt", not {in_.unit}!'
            )

        logging.debug(
            (
                "\n\tin_ = %s\n\tshare_reserves = %d\n\tbond_reserves = %d"
                "\n\ttotal_reserves = %d\n\tinit_share_price = %g"
                "\n\tshare_price = %g\n\tfee_percent = %g"
                "\n\ttime_remaining = %s\n\ttime_elapsed = %g"
                "\n\tspot_price = %g\n\tk = %g\n\twithout_fee_or_slippage = %s"
                "\n\twithout_fee = %s\n\twith_fee = %s\n\tfee = %s"
            ),
            in_,
            market_state.share_reserves,
            market_state.bond_reserves,
            market_state.share_reserves + market_state.bond_reserves,
            market_state.init_share_price,
            market_state.share_price,
            fee_percent,
            time_remaining,
            time_elapsed,
            spot_price,
            k,
            without_fee_or_slippage,
            without_fee,
            with_fee,
            fee,
        )

        return TradeResult(
            user_result=user_result,
            market_result=market_result,
            breakdown=TradeBreakdown(
                without_fee_or_slippage=without_fee_or_slippage,
                with_fee=with_fee,
                without_fee=without_fee,
                fee=fee,
            ),
        )

    def check_input_assertions(
        self,
        quantity: Quantity,
        market_state: MarketState,
        fee_percent: float,
        time_remaining: StretchedTime,
    ):
        assert (
            quantity.amount > 0
        ), f"pricing_models.check_input_assertions: ERROR: expected quantity.amount > 0, not {quantity.amount}!"
        assert (
            market_state.share_reserves >= 0
        ), f"pricing_models.check_input_assertions: ERROR: expected share_reserves >= 0, not {market_state.share_reserves}!"
        assert (
            market_state.bond_reserves >= 0
        ), f"pricing_models.check_input_assertions: ERROR: expected bond_reserves >= 0, not {market_state.bond_reserves}!"
        assert market_state.share_price == market_state.init_share_price == 1, (
            "pricing_models.check_input_assertions: ERROR: expected share_price == init_share_price == 1,"
            f"not share_price={market_state.share_price} and init_share_price={market_state.init_share_price}!"
        )
        assert (
            1 >= fee_percent >= 0
        ), f"pricing_models.calc_in_given_out: ERROR: expected 1 >= fee_percent >= 0, not {fee_percent}!"
        assert (
            1 > time_remaining.stretched_time >= 0
        ), f"pricing_models.calc_in_given_out: ERROR: expected 1 > time_remaining.stretched_time >= 0, not {time_remaining.stretched_time}!"

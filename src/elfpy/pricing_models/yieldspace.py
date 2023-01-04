"""The YieldSpace pricing model."""

import logging
from elfpy.pricing_models.base import PricingModel

from elfpy.types import (
    MarketTradeResult,
    Quantity,
    MarketState,
    StretchedTime,
    TokenType,
    TradeBreakdown,
    TradeResult,
    UserTradeResult,
)
import elfpy.utils.price as price_utils


class YieldSpacePricingModel(PricingModel):
    """
    YieldSpace Pricing Model

    This pricing model uses the YieldSpace invariant with modifications to
    enable the base reserves to be deposited into yield bearing vaults
    """

    # TODO: The too many locals disable can be removed after refactoring the LP
    #       functions.
    #
    # pylint: disable=too-many-locals
    # pylint: disable=duplicate-code

    def model_name(self) -> str:
        return "YieldSpace"

    def calc_lp_out_given_tokens_in(
        self,
        d_base: float,
        rate: float,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> tuple[float, float, float]:
        r"""
        Computes the amount of LP tokens to be minted for a given amount of base asset

        .. math::

        y = \frac{(z + \Delta z)(\mu \cdot (\frac{1}{1 + r \cdot t(d)})^{\frac{1}{\tau(d_b)}} - c)}{2}

        """
        assert d_base > 0, f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected d_base > 0, not {d_base}!"
        assert (
            market_state.share_reserves >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected share_reserves >= 0, not {market_state.share_reserves}!"
        assert (
            market_state.bond_reserves >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected bond_reserves >= 0, not {market_state.bond_reserves}!"
        assert (
            market_state.base_buffer >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected base_buffer >= 0, not {market_state.base_buffer}!"
        assert (
            market_state.lp_reserves >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected lp_reserves >= 0, not {market_state.lp_reserves}!"
        assert rate >= 0, f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected rate >= 0, not {rate}!"
        assert 1 > time_remaining.normalized_time >= 0, (
            "pricing_models.calc_lp_out_given_tokens_in: ERROR: "
            f"expected 1 > time_remaining >= 0, not {time_remaining.normalied_time}!"
        )
        assert time_remaining.stretched_time >= 0, (
            "pricing_models.calc_lp_out_given_tokens_in: ERROR: "
            f"expected stretched_time_remaining >= 0, not {time_remaining.stretched_time}!"
        )
        assert market_state.share_price >= market_state.init_share_price >= 1, (
            "pricing_models.calc_lp_out_given_tokens_in: ERROR: "
            "expected share_price >= init_share_price >= 1, not "
            f"share_price={market_state.share_price} and init_share_price={market_state.init_share_price}!"
        )
        d_shares = d_base / market_state.share_price
        if market_state.share_reserves > 0:  # normal case where we have some share reserves
            # TODO: We need to update these LP calculations to address the LP
            #       exploit scenario.
            lp_out = (d_shares * market_state.lp_reserves) / (market_state.share_reserves - market_state.base_buffer)
        else:  # initial case where we have 0 share reserves or final case where it has been removed
            lp_out = d_shares
        # TODO: Move this calculation to a helper function.
        d_bonds = (market_state.share_reserves + d_shares) / 2 * (
            market_state.init_share_price
            * (1 + rate * time_remaining.normalized_time) ** (1 / time_remaining.stretched_time)
            - market_state.share_price
        ) - market_state.bond_reserves
        logging.debug(
            (
                "inputs: d_base=%g, share_reserves=%d, "
                "bond_reserves=%d, base_buffer=%g, "
                "init_share_price=%g, share_price=%g, "
                "lp_reserves=%g, rate=%g, "
                "time_remaining=%g, stretched_time_remaining=%g"
                "\nd_shares=%g (d_base / share_price = %g / %g)"
                "\nlp_out=%g\n"
                "(d_share_reserves * lp_reserves / (share_reserves - base_buffer / share_price) = "
                "%g * %g / (%g - %g / %g))"
                "\nd_bonds=%g\n"
                "((share_reserves + d_share_reserves) / 2 * (init_share_price * (1 + rate * time_remaining) ** "
                "(1 / stretched_time_remaining) - share_price) - bond_reserves = "
                "(%g + %g) / 2 * (%g * (1 + %g * %g) ** "
                "(1 / %g) - %g) - %g)"
            ),
            d_base,
            market_state.share_reserves,
            market_state.bond_reserves,
            market_state.base_buffer,
            market_state.init_share_price,
            market_state.share_price,
            market_state.lp_reserves,
            rate,
            time_remaining.normalized_time,
            time_remaining.stretched_time,
            d_shares,
            d_base,
            market_state.share_price,
            lp_out,
            d_shares,
            market_state.lp_reserves,
            market_state.share_reserves,
            market_state.base_buffer,
            market_state.share_price,
            d_bonds,
            market_state.share_reserves,
            d_shares,
            market_state.init_share_price,
            rate,
            time_remaining.normalized_time,
            time_remaining.stretched_time,
            market_state.share_price,
            market_state.bond_reserves,
        )
        return lp_out, d_base, d_bonds

    def calc_lp_in_given_tokens_out(
        self,
        d_base: float,
        rate: float,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> tuple[float, float, float]:
        r"""
        Computes the amount of LP tokens to be minted for a given amount of base asset
        .. math::
        y = \frac{(z - \Delta z)(\mu \cdot (\frac{1}{1 + r \cdot t(d)})^{\frac{1}{\tau(d_b)}} - c)}{2}
        """
        assert d_base > 0, f"pricing_models.calc_lp_in_given_tokens_out: ERROR: expected d_base > 0, not {d_base}!"
        assert (
            market_state.share_reserves >= 0
        ), f"pricing_models.calc_lp_in_given_tokens_out: ERROR: expected share_reserves >= 0, not {market_state.share_reserves}!"
        assert (
            market_state.bond_reserves >= 0
        ), f"pricing_models.calc_lp_in_given_tokens_out: ERROR: expected bond_reserves >= 0, not {market_state.bond_reserves}!"
        assert (
            market_state.base_buffer >= 0
        ), f"pricing_models.calc_lp_in_given_tokens_out: ERROR: expected base_buffer >= 0, not {market_state.base_buffer}!"
        assert (
            market_state.lp_reserves >= 0
        ), f"pricing_models.calc_lp_in_given_tokens_out: ERROR: expected lp_reserves >= 0, not {market_state.lp_reserves}!"
        assert rate >= 0, f"pricing_models.calc_lp_in_given_tokens_out: ERROR: expected rate >= 0, not {rate}!"
        assert 1 > time_remaining.normalized_time >= 0, (
            "pricing_models.calc_lp_in_given_tokens_out: ERROR: "
            f"expected 1 > time_remaining >= 0, not {time_remaining.normalized_time}!"
        )
        assert time_remaining.stretched_time >= 0, (
            "pricing_models.calc_lp_in_given_tokens_out: ERROR: "
            f"expected stretched_time_remaining >= 0, not {time_remaining.stretched_time}!"
        )
        assert market_state.share_price >= market_state.init_share_price >= 1, (
            "pricing_models.calc_lp_in_given_tokens_out: ERROR: "
            "expected share_price >= init_share_price >= 1, not "
            f"share_price={market_state.share_price}, and init_share_price={market_state.init_share_price}"
        )
        d_shares = d_base / market_state.share_price
        lp_in = (d_shares * market_state.lp_reserves) / (market_state.share_reserves - market_state.base_buffer)
        # TODO: Move this calculation to a helper function.
        d_bonds = (market_state.share_reserves - d_shares) / 2 * (
            market_state.init_share_price
            * (1 + rate * time_remaining.normalized_time) ** (1 / time_remaining.stretched_time)
            - market_state.share_price
        ) - market_state.bond_reserves
        return lp_in, d_base, d_bonds

    def calc_tokens_out_given_lp_in(
        self,
        lp_in: float,
        rate: float,
        market_state: MarketState,
        time_remaining: StretchedTime,
    ) -> tuple[float, float, float]:
        """Calculate how many tokens should be returned for a given lp addition"""
        assert lp_in > 0, f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected lp_in > 0, not {lp_in}!"
        assert (
            market_state.share_reserves >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected share_reserves >= 0, not {market_state.share_reserves}!"
        assert (
            market_state.bond_reserves >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected bond_reserves >= 0, not {market_state.bond_reserves}!"
        assert (
            market_state.base_buffer >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected base_buffer >= 0, not {market_state.base_buffer}!"
        assert (
            market_state.lp_reserves >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected lp_reserves >= 0, not {market_state.lp_reserves}!"
        assert rate >= 0, f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected rate >= 0, not {rate}!"
        assert (
            1 > time_remaining.normalized_time >= 0
        ), f"pricing_models.calc_lp_out_given_tokens_in: ERROR: expected 1 > time_remaining >= 0, not {time_remaining.normalized_time}!"
        assert time_remaining.stretched_time >= 0, (
            "pricing_models.calc_lp_out_given_tokens_in: ERROR: "
            f"expected stretched_time_remaining >= 0, not {time_remaining.stretched_time}!"
        )
        assert market_state.share_price >= market_state.init_share_price >= 1, (
            "pricing_models.calc_lp_out_given_tokens_in: ERROR: "
            "expected share_price >= init_share_price >= 1, not "
            f"share_price={market_state.share_price}, and init_share_price={market_state.init_share_price}"
        )
        d_base = (
            market_state.share_price
            * (market_state.share_reserves - market_state.base_buffer)
            * lp_in
            / market_state.lp_reserves
        )
        d_shares = d_base / market_state.share_price
        # TODO: Move this calculation to a helper function.
        d_bonds = (market_state.share_reserves - d_shares) / 2 * (
            market_state.init_share_price
            * (1 + rate * time_remaining.normalized_time) ** (1 / time_remaining.stretched_time)
            - market_state.share_price
        ) - market_state.bond_reserves
        logging.debug(
            (
                "inputs: lp_in=%g, share_reserves=%d, "
                "bond_reserves=%d, base_buffer=%g, "
                "init_share_price=%g, share_price=%g, lp_reserves=%g, "
                "rate=%g, time_remaining=%g, stretched_time_remaining=%g"
                "  d_shares=%g (d_base / share_price = %g / %g)"
                "  d_bonds=%g\n"
                "((share_reserves + d_share_reserves) / 2 * (init_share_price * (1 + rate * time_remaining) "
                "** (1 / stretched_time_remaining) - share_price) - bond_reserves = "
                "(%g + %g) / 2 * (%g * (1 + %g * %g) "
                "** (1 / %g) - %g) - %g)"
            ),
            lp_in,
            market_state.share_reserves,
            market_state.bond_reserves,
            market_state.base_buffer,
            market_state.init_share_price,
            market_state.share_price,
            market_state.lp_reserves,
            rate,
            time_remaining.normalized_time,
            time_remaining.stretched_time,
            d_shares,
            d_base,
            market_state.share_price,
            d_bonds,
            market_state.share_reserves,
            d_shares,
            market_state.init_share_price,
            rate,
            time_remaining.normalized_time,
            time_remaining.stretched_time,
            market_state.share_price,
            market_state.bond_reserves,
        )
        return lp_in, d_base, d_bonds

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
            c (\frac{1}{\mu} (\frac{k - (2y + cz - \Delta y)^{1-t}}{\frac{c}{\mu}})^{\frac{1}{1-t}} - z),
            &\text{ if } token\_in = \text{"base"} \\
            (k - \frac{c}{\mu} (\mu * (z - \Delta z))^{1 - t})^{\frac{1}{1 - t}} - (2y + cz),
            &\text{ if } token\_in = \text{"pt"}
            \end{cases} \\
            f =
            \begin{cases}
            (1 - \frac{1}{(\frac{2y + cz}{\mu z})^{\tau}}) \phi \Delta y, &\text{ if } token\_in = \text{"base"} \\
            (\frac{2y + cz}{\mu z})^{\tau} - 1) \phi (c \Delta z), &\text{ if } token\_in = \text{"pt"}
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

        # Calculate some common values up front.
        time_elapsed = 1 - time_remaining.stretched_time
        scale = market_state.share_price / market_state.init_share_price
        total_reserves = market_state.share_price * market_state.share_reserves + market_state.bond_reserves
        spot_price = self.calc_spot_price_from_reserves(
            market_state,
            time_remaining,
        )

        # We precompute the YieldSpace constant k using the current reserves and
        # share price:
        #
        # k = (c / μ) * (μ * z)**(1 - t) + (2y + cz)**(1 - t)
        k = price_utils.calc_k_const(market_state, time_elapsed)
        if out.unit == TokenType.BASE:
            in_reserves = market_state.bond_reserves + total_reserves
            out_reserves = market_state.share_reserves
            d_shares = out.amount / market_state.share_price

            # The amount the user pays without fees or slippage is simply the
            # amount of base the user would receive times the inverse of the
            # spot price of base in terms of bonds. The amount of base the user
            # receives is given by c * d_z where d_z is the number of shares the
            # pool will need to unwrap to give the user their base. If we let p
            # be the conventional spot price, then we can write this as:
            #
            # without_fee_or_slippage = (1 / p) * c * d_z
            without_fee_or_slippage = (1 / spot_price) * market_state.share_price * d_shares

            # We solve the YieldSpace invariant for the bonds paid to receive
            # the requested amount of base. We set up the invariant where the
            # user pays d_y' bonds and receives d_z shares:
            #
            # (c / μ) * (μ * (z - d_z))**(1 - t) + (2y + cz + d_y')**(1 - t) = k
            #
            # Solving for d_y' gives us the amount of bonds the user must pay
            # without including fees:
            #
            # d_y' = (k - (c / μ) * (μ * (z - d_z))**(1 - t))**(1 / (1 - t)) - (2y + cz)
            #
            # without_fee = d_y'
            without_fee = (
                pow(
                    k - scale * pow((market_state.init_share_price * (out_reserves - d_shares)), time_elapsed),
                    1 / time_elapsed,
                )
                - in_reserves
            )

            # The fees are calculated as the difference between the bonds paid
            # without slippage and the base received times the fee percentage.
            # This can also be expressed as:
            #
            # fee = ((1 / p) - 1) * φ * c * d_z
            logging.debug(
                (
                    "fee = ((1 / spot_price) - 1) * fee_percent * share_price * d_shares = "
                    "((1 / %g) - 1) * %g * %g * %g = %g"
                ),
                spot_price,
                fee_percent,
                market_state.share_price,
                d_shares,
                ((1 / spot_price) - 1) * fee_percent * market_state.share_price * d_shares,
            )
            fee = ((1 / spot_price) - 1) * fee_percent * market_state.share_price * d_shares

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
        elif out.unit == TokenType.PT:
            in_reserves = market_state.share_reserves
            out_reserves = market_state.bond_reserves + total_reserves
            d_bonds = out.amount

            # The amount the user pays without fees or slippage is simply
            # the amount of bonds the user would receive times the spot price of
            # base in terms of bonds. If we let p be the conventional spot price,
            # then we can write this as:
            #
            # without_fee_or_slippage = p * d_y
            without_fee_or_slippage = spot_price * d_bonds

            # We solve the YieldSpace invariant for the base paid for the
            # requested amount of bonds. We set up the invariant where the user
            # pays d_z' shares and receives d_y bonds:
            #
            # (c / μ) * (μ * (z + d_z'))**(1 - t) + (2y + cz - d_y)**(1 - t) = k
            #
            # Solving for d_z' gives us the amount of shares the user pays
            # without including fees:
            #
            # d_z' = (1 / μ) * ((k - (2y + cz - d_y)**(1 - t)) / (c / μ))**(1 / (1 - t)) - z
            #
            # We really want to know the value of d_x', the amount of base the
            # user pays. This is given by d_x' = c * d_z'.
            #
            # without_fee = d_x'
            without_fee = (
                (1 / market_state.init_share_price)
                * pow(
                    (k - pow(out_reserves - d_bonds, time_elapsed)) / scale,
                    1 / time_elapsed,
                )
                - in_reserves
            ) * market_state.share_price

            # The fees are calculated as the difference between the bonds
            # received and the base paid without slippage times the fee
            # percentage. This can also be expressed as:
            #
            # fee = (1 - p) * φ * d_y
            fee = (1 - spot_price) * fee_percent * d_bonds
            logging.debug(
                ("fee = (1 - spot_price) * fee_percent * d_bonds = (1 - %g) * %g * %g = %g"),
                spot_price,
                fee_percent,
                d_bonds,
                (1 - spot_price) * fee_percent * d_bonds,
            )

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
                # pylint: disable-next=line-too-long
                f"pricing_models.calc_in_given_out: ERROR: expected out.unit to be {TokenType.BASE} or {TokenType.PT}, not {out.unit}!"
            )

        return TradeResult(
            user_result=user_result,
            market_result=market_result,
            breakdown=TradeBreakdown(
                without_fee_or_slippage=without_fee_or_slippage, with_fee=with_fee, without_fee=without_fee, fee=fee
            ),
        )

    # TODO: The high slippage tests in tests/test_pricing_model.py should
    # arguably have much higher slippage. This is something we should
    # consider more when thinking about the use of a time stretch parameter.
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
            c (z - \frac{1}{\mu} (\frac{k - (2y + cz + \Delta y)^{1 - t}}{\frac{c}{\mu}})^{\frac{1}{1 - t}}),
            &\text{ if } token\_out = \text{"base"} \\
            2y + cz - (k - \frac{c}{\mu} (\mu (z + \Delta z))^{1 - t})^{\frac{1}{1 - t}},
            &\text{ if } token\_out = \text{"pt"}
            \end{cases} \\
            f =
            \begin{cases}
            (1 - \frac{1}{(\frac{2y + cz}{\mu z})^{\tau}}) \phi \Delta y, &\text{ if } token\_out = \text{"base"} \\
            (\frac{2y + cz}{\mu z})^{\tau} - 1) \phi (c \Delta z), &\text{ if } token\_out = \text{"pt"}
            \end{cases} \\
            out = out' + f

        Arguments
        ---------
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

        # Calculate some common values up front.
        scale = market_state.share_price / market_state.init_share_price
        time_elapsed = 1 - time_remaining.stretched_time
        total_reserves = market_state.share_price * market_state.share_reserves + market_state.bond_reserves
        spot_price = self.calc_spot_price_from_reserves(
            market_state,
            time_remaining,
        )

        # We precompute the YieldSpace constant k using the current reserves and
        # share price:
        #
        # k = (c / μ) * (μ * z)**(1 - t) + (2y + cz)**(1 - t)
        k = price_utils.calc_k_const(market_state, time_elapsed)
        if in_.unit == TokenType.BASE:
            d_shares = in_.amount / market_state.share_price  # convert from base_asset to z (x=cz)
            in_reserves = market_state.share_reserves
            out_reserves = market_state.bond_reserves + total_reserves

            # The amount the user would receive without fees or slippage is
            # the amount of base the user pays times inverse of the spot price
            # of base in terms of bonds. If we let p be the conventional spot
            # price, then we can write this as:
            #
            # (1 / p) * c * d_z
            without_fee_or_slippage = (1 / spot_price) * market_state.share_price * d_shares

            # We solve the YieldSpace invariant for the bonds received from
            # paying the specified amount of base. We set up the invariant where
            # the user pays d_z shares and receives d_y' bonds:
            #
            # (c / μ) * (μ * (z + d_z))**(1 - t) + (2y + cz - d_y')**(1 - t) = k
            #
            # Solving for d_y' gives us the amount of bonds the user receives
            # without including fees:
            #
            # d_y' = 2y + cz - (k - (c / μ) * (μ * (z + d_z))**(1 - t))**(1 / (1 - t))
            without_fee = out_reserves - pow(
                k - scale * pow(market_state.init_share_price * (in_reserves + d_shares), time_elapsed),
                1 / time_elapsed,
            )

            # The fees are calculated as the difference between the bonds
            # received without slippage and the base paid times the fee
            # percentage. This can also be expressed as:
            #
            # ((1 / p) - 1) * φ * c * d_z
            fee = ((1 / spot_price) - 1) * fee_percent * market_state.share_price * d_shares

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
        elif in_.unit == TokenType.PT:
            d_bonds = in_.amount
            in_reserves = market_state.bond_reserves + total_reserves
            out_reserves = market_state.share_reserves

            # The amount the user would receive without fees or slippage is the
            # amount of bonds the user pays times the spot price of base in
            # terms of bonds. If we let p be the conventional spot price, then
            # we can write this as:
            #
            # p * d_y
            without_fee_or_slippage = spot_price * d_bonds

            # We solve the YieldSpace invariant for the base received from
            # selling the specified amount of bonds. We set up the invariant
            # where the user pays d_y bonds and receives d_z' shares:
            #
            # (c / μ) * (μ * (z - d_z'))**(1 - t) + (2y + cz + d_y)**(1 - t) = k
            #
            # Solving for d_z' gives us the amount of shares the user receives
            # without fees:
            #
            # d_z' = z - (1 / μ) * ((k - (2y + cz + d_y)**(1 - t)) / (c / μ))**(1 / (1 - t))
            #
            # We really want to know the value of d_x', the amount of base the
            # user receives without fees. This is given by d_x' = c * d_z'.
            #
            # without_fee = d_x'
            without_fee = (
                market_state.share_reserves
                - (1 / market_state.init_share_price)
                * ((k - (in_reserves + d_bonds) ** time_elapsed) / scale) ** (1 / time_elapsed)
            ) * market_state.share_price

            # The fees are calculated as the difference between the bonds paid
            # and the base received without slippage times the fee percentage.
            # This can also be expressed as:
            #
            # fee = (1 - p) * φ * d_y
            fee = (1 - spot_price) * fee_percent * d_bonds
            with_fee = without_fee - fee

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
                # pylint: disable-next=line-too-long
                f"pricing_models.calc_out_given_in: ERROR: expected in_.unit to be {TokenType.BASE} or {TokenType.PT}, not {in_.unit}!"
            )

        return TradeResult(
            user_result=user_result,
            market_result=market_result,
            breakdown=TradeBreakdown(
                without_fee_or_slippage=without_fee_or_slippage, with_fee=with_fee, without_fee=without_fee, fee=fee
            ),
        )

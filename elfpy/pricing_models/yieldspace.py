"""The YieldSpace pricing model"""
from __future__ import annotations  # types will be strings by default in 3.11

from decimal import Decimal
import logging
from typing import TYPE_CHECKING

from elfpy.pricing_models.base import PricingModel
import elfpy.time as time
import elfpy.markets.hyperdrive as hyperdrive
from elfpy.agents.agent import AgentTradeResult
import elfpy.pricing_models.trades as trades
import elfpy.types as types

if TYPE_CHECKING:
    from elfpy.markets.hyperdrive import MarketState


class YieldspacePricingModel(PricingModel):
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

    def model_type(self) -> str:
        return "yieldspace"

    def calc_lp_out_given_tokens_in(
        self,
        d_base: float,
        rate: float,
        market_state: MarketState,
        time_remaining: time.StretchedTime,
    ) -> tuple[float, float, float]:
        r"""Computes the amount of LP tokens to be minted for a given amount of base asset

        .. math::
            y = \frac{(z + \Delta z)(\mu \cdot (\frac{1}{1 + r \cdot t(d)})^{\frac{1}{\tau(d_b)}} - c)}{2}
        """
        d_shares = d_base / market_state.share_price
        if market_state.share_reserves > 0:  # normal case where we have some share reserves
            # TODO: We need to update these LP calculations to address the LP
            #       exploit scenario.
            lp_out = (d_shares * market_state.lp_total_supply) / (
                market_state.share_reserves - market_state.base_buffer
            )
        else:  # initial case where we have 0 share reserves or final case where it has been removed
            lp_out = d_shares
        # TODO: Move this calculation to a helper function.
        annualized_time = time.norm_days(time_remaining.days, 365)
        d_bonds = (market_state.share_reserves + d_shares) / 2 * (
            market_state.init_share_price * (1 + rate * annualized_time) ** (1 / time_remaining.stretched_time)
            - market_state.share_price
        ) - market_state.bond_reserves
        logging.debug(
            (
                "inputs: d_base=%g, share_reserves=%d, "
                "bond_reserves=%d, base_buffer=%g, "
                "init_share_price=%g, share_price=%g, "
                "lp_total_supply=%g, rate=%g, "
                "time_remaining=%g, stretched_time_remaining=%g"
                "\nd_shares=%g (d_base / share_price = %g / %g)"
                "\nlp_out=%g\n"
                "(d_share_reserves * lp_total_supply / (share_reserves - base_buffer / share_price) = "
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
            market_state.lp_total_supply,
            rate,
            time_remaining.normalized_time,
            time_remaining.stretched_time,
            d_shares,
            d_base,
            market_state.share_price,
            lp_out,
            d_shares,
            market_state.lp_total_supply,
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

    # TODO: Delete this function from here & base? It is not used or tested.
    def calc_lp_in_given_tokens_out(
        self,
        d_base: float,
        rate: float,
        market_state: MarketState,
        time_remaining: time.StretchedTime,
    ) -> tuple[float, float, float]:
        r"""Computes the amount of LP tokens to be minted for a given amount of base asset

        .. math::
            y = \frac{(z - \Delta z)(\mu \cdot (\frac{1}{1 + r \cdot t(d)})^{\frac{1}{\tau(d_b)}} - c)}{2}
        """
        d_shares = d_base / market_state.share_price
        lp_in = (d_shares * market_state.lp_total_supply) / (
            market_state.share_reserves - market_state.base_buffer / market_state.share_price
        )
        # TODO: Move this calculation to a helper function.
        annualized_time = time.norm_days(time_remaining.days, 365)
        d_bonds = (market_state.share_reserves - d_shares) / 2 * (
            market_state.init_share_price * (1 + rate * annualized_time) ** (1 / time_remaining.stretched_time)
            - market_state.share_price
        ) - market_state.bond_reserves
        return lp_in, d_base, d_bonds

    def calc_tokens_out_given_lp_in(
        self,
        lp_in: float,
        rate: float,
        market_state: MarketState,
        time_remaining: time.StretchedTime,
    ) -> tuple[float, float, float]:
        """Calculate how many tokens should be returned for a given lp addition

        .. todo:: add test for this function; improve function documentation w/ parameters, returns, and equations used
        """
        # d_z = (z - b_x / c) * (dl / l)
        # d_x = (c * z - b_x) * (dl / l)
        d_base = (market_state.share_price * market_state.share_reserves - market_state.base_buffer) * (
            lp_in / market_state.lp_total_supply
        )
        d_shares = d_base / market_state.share_price
        # TODO: Move this calculation to a helper function.
        # rate is an APR, which is annual, so we normalize time by 365 to correct for units
        annualized_time = time.norm_days(time_remaining.days, 365)

        d_bonds = ((market_state.share_reserves - d_shares) / 2) * (
            market_state.init_share_price * (1 + rate * annualized_time) ** (1 / time_remaining.stretched_time)
            - market_state.share_price
        ) - market_state.bond_reserves

        annualized_time = time.norm_days(time_remaining.days, 365)
        # bond_reserves = (market_state.share_reserves / 2) * (
        #     market_state.init_share_price * (1 + target_apr * annualized_time) ** (1 / time_remaining.stretched_time)
        #     - market_state.share_price
        # )  # y = z/2 * (mu * (1 + rt)**(1/tau) - c)
        # return bond_reserves
        logging.debug(
            (
                "inputs:\n\tlp_in=%g,\n\tshare_reserves=%d, "
                "bond_reserves=%d,\n\tbase_buffer=%g, "
                "init_share_price=%g,\n\tshare_price=%g,\n\tlp_reserves=%g,\n\t"
                "rate=%g,\n\ttime_remaining=%g,\n\tstretched_time_remaining=%g\n\t"
                "\n\td_shares=%g\n\t(d_base / share_price = %g / %g)"
                "\n\td_bonds=%g"
                "\n\t((share_reserves - d_shares) / 2 * (init_share_price * (1 + apr * annualized_time) "
                "** (1 / stretched_time_remaining) - share_price) - bond_reserves = "
                "\n\t((%g - %g) / 2 * (%g * (1 + %g * %g) "
                "** (1 / %g) - %g) - %g =\n\t%g"
            ),
            lp_in,
            market_state.share_reserves,
            market_state.bond_reserves,
            market_state.base_buffer,
            market_state.init_share_price,
            market_state.share_price,
            market_state.lp_total_supply,
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
            annualized_time,
            time_remaining.stretched_time,
            market_state.share_price,
            market_state.bond_reserves,
            d_bonds,
        )
        return lp_in, d_base, d_bonds

    def calc_in_given_out(
        self,
        out: types.Quantity,
        market_state: MarketState,
        time_remaining: time.StretchedTime,
    ) -> trades.TradeResult:
        r"""
        Calculates the amount of an asset that must be provided to receive a
        specified amount of the other asset given the current AMM reserves.

        The input is calculated as:

        .. math::
            \begin{align*}
            & s \;\;\;\; = \;\;\;\; \text{total_supply}\\
            & p \;\;\;\; = \;\;\;\; \Bigg(\dfrac{y + s}{\mu z}\Bigg)^{-\tau}
            \\\\
            & in' \;\;\:  = \;\;\:
            \begin{cases}
            \\
            \text{ if $token\_in$ = "base", }\\
            \quad\quad\quad c \big(\mu^{-1} \big(\mu \cdot c^{-1} \big(k -
            \big(y + s - \Delta y\big)
            ^{1-\tau}\big)\big)
            ^ {\tfrac{1}{1-\tau}} - z\big)
            \\\\
            \text{ if $token\_in$ = "pt", }\\
            \quad\quad\quad (k -
            \big(c \cdot \mu^{-1} \cdot
            \big(\mu \cdot\big(z - \Delta z \big)\big)
            ^{1 - \tau} \big)^{\tfrac{1}{1 - \tau}}) - \big(y + s\big)
            \\\\
            \end{cases}
            \\\\
            & f \;\;\;\; = \;\;\;\;
            \begin{cases}
            \\
            \text{ if $token\_in$ = "base", }\\\\
            \quad\quad\quad (1 - p) \phi\;\; \Delta y
            \\\\
            \text{ if $token\_in$ = "pt", }\\\\
            \quad\quad\quad (p^{-1} - 1) \enspace \phi \enspace (c \cdot \Delta z)
            \\\\
            \end{cases}
            \\\\\\
            & in = in' + f
            \\
            \end{align*}

        .. note::
           The pool total supply is a function of the base and bond reserves, and is modified in
           :func:`calc_lp_in_given_tokens_out
           <elfpy.pricing_models.yieldspace.YieldSpacePricingModel.calc_lp_in_given_tokens_out>`,
           :func:`calc_tokens_out_given_lp_in
           <elfpy.pricing_models.yieldspace.YieldSpacePricingModel.calc_tokens_out_given_lp_in>`,
           and :func:`calc_lp_out_given_tokens_in
           <elfpy.pricing_models.yieldspace.YieldSpacePricingModel.calc_lp_out_given_tokens_in>`.

           It can be approximated as :math:`s \approx y + cz`.

        Parameters
        ----------
        out : Quantity
            The quantity of tokens that the user wants to receive (the amount
            and the unit of the tokens).
        market_state : MarketState
            The state of the AMM's reserves and share prices.
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
        # Calculate some common values up front
        time_elapsed = 1 - Decimal(time_remaining.stretched_time)
        init_share_price = Decimal(market_state.init_share_price)
        share_price = Decimal(market_state.share_price)
        scale = share_price / init_share_price
        share_reserves = Decimal(market_state.share_reserves)
        bond_reserves = Decimal(market_state.bond_reserves)
        total_reserves = share_price * share_reserves + bond_reserves
        spot_price = self._calc_spot_price_from_reserves_high_precision(
            market_state,
            time_remaining,
        )
        out_amount = Decimal(out.amount)
        trade_fee_percent = Decimal(market_state.trade_fee_percent)
        # We precompute the YieldSpace constant k using the current reserves and
        # share price:
        #
        # k = (c / mu) * (mu * z)**(1 - tau) + (2y + cz)**(1 - tau)
        k = self._calc_k_const(market_state, time_remaining)
        if out.unit == types.TokenType.BASE:
            in_reserves = bond_reserves + total_reserves
            out_reserves = share_reserves
            d_shares = out_amount / share_price
            # The amount the user pays without fees or slippage is simply the
            # amount of base the user would receive times the inverse of the
            # spot price of base in terms of bonds. The amount of base the user
            # receives is given by c * d_z where d_z is the number of shares the
            # pool will need to unwrap to give the user their base. If we let p
            # be the conventional spot price, then we can write this as:
            #
            # without_fee_or_slippage = (1 / p) * c * d_z
            without_fee_or_slippage = (1 / spot_price) * share_price * d_shares
            # We solve the YieldSpace invariant for the bonds paid to receive
            # the requested amount of base. We set up the invariant where the
            # user pays d_y' bonds and receives d_z shares:
            #
            # (c / mu) * (mu * (z - d_z))**(1 - tau) + (2y + cz + d_y')**(1 - tau)) = k
            #
            # Solving for d_y' gives us the amount of bonds the user must pay
            # without including fees:
            #
            # d_y' = (k - (c / mu) * (mu * (z - d_z))**(1 - tau))**(1 / (1 - tau)) - (2y + cz)
            #
            # without_fee = d_y'
            base_of_exponent = init_share_price * (out_reserves - d_shares)
            if base_of_exponent < 0:
                raise ValueError(f"ERROR: {base_of_exponent=} <= 0")
            without_fee = (k - scale * base_of_exponent**time_elapsed) ** (1 / time_elapsed) - in_reserves
            # The fees are calculated as the difference between the bonds paid
            # without slippage and the base received times the fee percentage.
            # This can also be expressed as:
            #
            # fee = ((1 / p) - 1) * phi * c * d_z
            fee = ((1 / spot_price) - 1) * trade_fee_percent * share_price * d_shares
            logging.debug(
                (
                    "fee = ((1 / spot_price) - 1) * _fee_percent * share_price * d_shares = "
                    "((1 / %g) - 1) * %g * %g * %g = %g"
                ),
                spot_price,
                trade_fee_percent,
                share_price,
                d_shares,
                fee,
            )
            # To get the amount paid with fees, add the fee to the calculation that
            # excluded fees. Adding the fees results in more tokens paid, which
            # indicates that the fees are working correctly.
            with_fee = without_fee + fee
            # Create the user and market trade results.
            user_result = AgentTradeResult(
                d_base=out.amount,
                d_bonds=float(-with_fee),
            )
            market_result = hyperdrive.MarketTradeResult(
                d_base=-out.amount,
                d_bonds=float(with_fee),
            )
        elif out.unit == types.TokenType.PT:
            in_reserves = share_reserves
            out_reserves = bond_reserves + total_reserves
            d_bonds = out_amount
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
            # (c / mu) * (mu * (z + d_z'))**(1 - tau) + (2y + cz - d_y)**(1 - tau) = k
            #
            # Solving for d_z' gives us the amount of shares the user pays
            # without including fees:
            #
            # d_z' = (1 / mu) * ((k - (2y + cz - d_y)**(1 - tau)) / (c / mu))**(1 / (1 - tau)) - z
            #
            # We really want to know the value of d_x', the amount of base the
            # user pays. This is given by d_x' = c * d_z'.
            #
            # without_fee = d_x'
            base_of_exponent = out_reserves - d_bonds
            if base_of_exponent < 0:
                raise ValueError(f"ERROR: {base_of_exponent=} <= 0")
            without_fee = (
                (1 / init_share_price) * ((k - base_of_exponent**time_elapsed) / scale) ** (1 / time_elapsed)
                - in_reserves
            ) * share_price
            # The fees are calculated as the difference between the bonds
            # received and the base paid without slippage times the fee
            # percentage. This can also be expressed as:
            #
            # fee = (1 - p) * phi * d_y
            fee = (1 - spot_price) * trade_fee_percent * d_bonds
            logging.debug(
                ("fee = (1 - spot_price) * _fee_percent * d_bonds = (1 - %g) * %g * %g = %g"),
                spot_price,
                trade_fee_percent,
                d_bonds,
                fee,
            )
            # To get the amount paid with fees, add the fee to the calculation that
            # excluded fees. Adding the fees results in more tokens paid, which
            # indicates that the fees are working correctly.
            with_fee = without_fee + fee
            # Create the user and market trade results.
            user_result = AgentTradeResult(
                d_base=float(-with_fee),
                d_bonds=out.amount,
            )
            market_result = hyperdrive.MarketTradeResult(
                d_base=float(with_fee),
                d_bonds=-out.amount,
            )
        else:
            raise AssertionError(
                # pylint: disable-next=line-too-long
                f"pricing_models.calc_in_given_out: ERROR: expected out.unit to be {types.TokenType.BASE} or {types.TokenType.PT}, not {out.unit}!"
            )
        return trades.TradeResult(
            user_result=user_result,
            market_result=market_result,
            breakdown=trades.TradeBreakdown(
                without_fee_or_slippage=float(without_fee_or_slippage),
                with_fee=float(with_fee),
                without_fee=float(without_fee),
                fee=float(fee),
            ),
        )

    # TODO: The high slippage tests in tests/test_pricing_model.py should
    # arguably have much higher slippage. This is something we should
    # consider more when thinking about the use of a time stretch parameter.
    def calc_out_given_in(
        self,
        in_: types.Quantity,
        market_state: MarketState,
        time_remaining: time.StretchedTime,
    ) -> trades.TradeResult:
        r"""
        Calculates the amount of an asset that must be provided to receive a
        specified amount of the other asset given the current AMM reserves.

        The output is calculated as:

        .. math::
            \begin{align*}
            & s \;\;\;\; = \;\;\;\; \text{total_supply}\\
            & p \;\;\;\; = \;\;\;\; \Bigg(\dfrac{y + s}{\mu z}\Bigg)^{-\tau}
            \\\\
            & out'\;\; = \;\;
            \begin{cases}
            \\
            \text{ if $token\_out$ = "base", }\\
            \quad\quad\quad c \big(z - \mu^{-1}
            \big(c \cdot \mu^{-1} \big(k - \big(y + s + \Delta y\big)
            ^{1 - \tau}\big)\big)
            ^{\tfrac{1}{1 - \tau}}\big)
            \\\\
            \text{ if $token\_out$ = "pt", }\\
            \quad\quad\quad y + s - (k - c \cdot
            \mu^{-1} \cdot (\mu (z + \Delta z))^{1 - \tau})
            ^{\tfrac{1}{(1 - \tau)}}
            \\\\
            \end{cases}
            \\\\
            & f \;\;\;\; = \;\;\;\;
            \begin{cases}
            \\
            \text{ if $token\_out$ = "base", }\\\\
            \quad\quad\quad (1 - p) \phi\;\; \Delta y
            \\\\
            \text{ if $token\_out$ = "pt", }\\\\
            \quad\quad\quad (p^{-1} - 1) \enspace \phi \enspace (c \cdot \Delta z)
            \\\\
            \end{cases}
            \\\\\\
            & out = out' + f
            \\
            \end{align*}

        .. note::
           The pool total supply is a function of the base and bond reserves, and is modified in
           :func:`calc_lp_in_given_tokens_out
           <elfpy.pricing_models.yieldspace.YieldSpacePricingModel.calc_lp_in_given_tokens_out>`,
           :func:`calc_tokens_out_given_lp_in
           <elfpy.pricing_models.yieldspace.YieldSpacePricingModel.calc_tokens_out_given_lp_in>`,
           and :func:`calc_lp_out_given_tokens_in
           <elfpy.pricing_models.yieldspace.YieldSpacePricingModel.calc_lp_out_given_tokens_in>`.

           It can be approximated as :math:`s \approx y + cz`.

        Parameters
        ----------
        in_ : Quantity
            The quantity of tokens that the user wants to pay (the amount
            and the unit of the tokens).
        market_state : MarketState
            The state of the AMM's reserves and share prices.
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
        # Calculate some common values up front
        time_elapsed = 1 - Decimal(time_remaining.stretched_time)
        init_share_price = Decimal(market_state.init_share_price)
        share_price = Decimal(market_state.share_price)
        scale = share_price / init_share_price
        share_reserves = Decimal(market_state.share_reserves)
        bond_reserves = Decimal(market_state.bond_reserves)
        total_reserves = share_price * share_reserves + bond_reserves
        spot_price = self._calc_spot_price_from_reserves_high_precision(
            market_state,
            time_remaining,
        )
        in_amount = Decimal(in_.amount)
        trade_fee_percent = Decimal(market_state.trade_fee_percent)
        # We precompute the YieldSpace constant k using the current reserves and
        # share price:
        #
        # k = (c / mu) * (mu * z)**(1 - tau) + (2y + cz)**(1 - tau)
        k = self._calc_k_const(market_state, time_remaining)
        if in_.unit == types.TokenType.BASE:
            d_shares = in_amount / share_price  # convert from base_asset to z (x=cz)
            in_reserves = share_reserves
            out_reserves = bond_reserves + total_reserves
            # The amount the user would receive without fees or slippage is
            # the amount of base the user pays times inverse of the spot price
            # of base in terms of bonds. If we let p be the conventional spot
            # price, then we can write this as:
            #
            # (1 / p) * c * d_z
            without_fee_or_slippage = (1 / spot_price) * share_price * d_shares
            # We solve the YieldSpace invariant for the bonds received from
            # paying the specified amount of base. We set up the invariant where
            # the user pays d_z shares and receives d_y' bonds:
            #
            # (c / mu) * (mu * (z + d_z))**(1 - tau) + (2y + cz - d_y')**(1 - tau) = k
            #
            # Solving for d_y' gives us the amount of bonds the user receives
            # without including fees:
            #
            # d_y' = 2y + cz - (k - (c / mu) * (mu * (z + d_z))**(1 - tau))**(1 / (1 - tau))
            base_of_exponent = init_share_price * (in_reserves + d_shares)
            if base_of_exponent < 0:
                raise ValueError(f"ERROR: {base_of_exponent=} <= 0")
            without_fee = out_reserves - (k - scale * base_of_exponent**time_elapsed) ** (1 / time_elapsed)
            # The fees are calculated as the difference between the bonds
            # received without slippage and the base paid times the fee
            # percentage. This can also be expressed as:
            #
            # ((1 / p) - 1) * phi * c * d_z
            fee = ((1 / spot_price) - 1) * trade_fee_percent * share_price * d_shares
            # To get the amount paid with fees, subtract the fee from the
            # calculation that excluded fees. Subtracting the fees results in less
            # tokens received, which indicates that the fees are working correctly.
            with_fee = without_fee - fee
            # Create the user and market trade results.
            user_result = AgentTradeResult(
                d_base=-in_.amount,
                d_bonds=float(with_fee),
            )
            market_result = hyperdrive.MarketTradeResult(
                d_base=in_.amount,
                d_bonds=float(-with_fee),
            )
        elif in_.unit == types.TokenType.PT:
            d_bonds = in_amount
            in_reserves = bond_reserves + total_reserves
            out_reserves = share_reserves
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
            # (c / mu) * (mu * (z - d_z'))**(1 - tau) + (2y + cz + d_y)**(1 - tau) = k
            #
            # Solving for d_z' gives us the amount of shares the user receives
            # without fees:
            #
            # d_z' = z - (1 / mu) * ((k - (2y + cz + d_y)**(1 - tau)) / (c / mu))**(1 / (1 - tau))
            #
            # We really want to know the value of d_x', the amount of base the
            # user receives without fees. This is given by d_x' = c * d_z'.
            #
            # without_fee = d_x'
            base_of_exponent = in_reserves + d_bonds
            if base_of_exponent < 0:
                raise ValueError(f"ERROR: {base_of_exponent=} <= 0")
            without_fee = (
                share_reserves
                - (1 / init_share_price) * ((k - base_of_exponent**time_elapsed) / scale) ** (1 / time_elapsed)
            ) * share_price
            # The fees are calculated as the difference between the bonds paid
            # and the base received without slippage times the fee percentage.
            # This can also be expressed as:
            #
            # fee = (1 - p) * phi * d_y
            fee = (1 - spot_price) * trade_fee_percent * d_bonds
            # To get the amount paid with fees, subtract the fee from the
            # calculation that excluded fees. Subtracting the fees results in less
            # tokens received, which indicates that the fees are working correctly.
            with_fee = without_fee - fee
            # Create the user and market trade results.
            user_result = AgentTradeResult(
                d_base=float(with_fee),
                d_bonds=-in_.amount,
            )
            market_result = hyperdrive.MarketTradeResult(
                d_base=float(-with_fee),
                d_bonds=in_.amount,
            )
        else:
            raise AssertionError(
                f"pricing_models.calc_out_given_in: ERROR: expected in_.unit"
                f" to be {types.TokenType.BASE} or {types.TokenType.PT}, not {in_.unit}!"
            )
        return trades.TradeResult(
            user_result=user_result,
            market_result=market_result,
            breakdown=trades.TradeBreakdown(
                without_fee_or_slippage=float(without_fee_or_slippage),
                with_fee=float(with_fee),
                without_fee=float(without_fee),
                fee=float(fee),
            ),
        )

    def _calc_k_const(self, market_state: MarketState, time_remaining: time.StretchedTime) -> Decimal:
        """
        Returns the 'k' constant variable for trade mathematics

        .. math::
            k = \frac{c / mu} (mu z)^{1 - \tau} + (2y + c z)^(1 - \tau)

        Parameters
        ----------
        market_state : MarketState
            The state of the AMM
        time_remaining : StretchedTime
            Time until expiry for the token

        Returns
        -------
        Decimal
            'k' constant used for trade mathematics, calculated from the provided parameters
        """
        scale = Decimal(market_state.share_price) / Decimal(market_state.init_share_price)
        total_reserves = Decimal(market_state.bond_reserves) + Decimal(market_state.share_price) * Decimal(
            market_state.share_reserves
        )
        time_elapsed = Decimal(1) - Decimal(time_remaining.stretched_time)
        return (
            scale * (Decimal(market_state.init_share_price) * Decimal(market_state.share_reserves)) ** time_elapsed
            + (Decimal(market_state.bond_reserves) + Decimal(total_reserves)) ** time_elapsed
        )

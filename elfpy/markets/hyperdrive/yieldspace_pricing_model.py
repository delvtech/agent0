"""The YieldSpace pricing model"""
from __future__ import annotations  # types will be strings by default in 3.11

import logging
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

import elfpy.agents.agent_trade_result as agent_trade_result
import elfpy.markets.hyperdrive.market_action_result as market_action_result
import elfpy.markets.trades as trades
import elfpy.time as time
import elfpy.types as types
from elfpy.markets.base import BasePricingModel

if TYPE_CHECKING:
    from .hyperdrive_market import HyperdriveMarketState


class YieldspacePricingModel(BasePricingModel):
    """YieldSpace Pricing Model.

    This pricing model uses the YieldSpace invariant with modifications to
    enable the base reserves to be deposited into yield bearing vaults
    """

    # TODO: The too many locals disable can be removed after refactoring the LP
    #       functions.
    #
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-arguments

    def model_name(self) -> str:
        return "YieldSpace"

    def model_type(self) -> str:
        return "yieldspace"

    def calc_lp_out_given_tokens_in(
        self,
        d_base: FixedPoint,
        rate: FixedPoint,
        market_state: HyperdriveMarketState,
        time_remaining: time.StretchedTime,
    ) -> tuple[FixedPoint, FixedPoint, FixedPoint]:
        r"""Computes the amount of LP tokens to be minted for a given amount of base asset

        .. math::
            y = \frac{(z + \Delta z)(\mu \cdot (\frac{1}{1 + r \cdot t(d)})^{\frac{1}{\tau(d_b)}} - c)}{2}
        """
        d_shares = d_base / market_state.share_price
        if market_state.share_reserves > FixedPoint(0):  # normal case where we have some share reserves
            # TODO: We need to update these LP calculations to address the LP
            #       exploit scenario.
            lp_out = (d_shares * market_state.lp_total_supply) / (
                market_state.share_reserves - market_state.base_buffer
            )
        else:  # initial case where we have 0 share reserves or final case where it has been removed
            lp_out = d_shares
        # TODO: Move this calculation to a helper function.
        annualized_time = time_remaining.days / FixedPoint("365.0")
        d_bonds = (market_state.share_reserves + d_shares) / FixedPoint("2.0") * (
            market_state.init_share_price
            * (FixedPoint("1.0") + rate * annualized_time) ** (FixedPoint("1.0").div_up(time_remaining.stretched_time))
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

    def calc_in_given_out(
        self,
        out: types.Quantity,
        market_state: HyperdriveMarketState,
        time_remaining: time.StretchedTime,
    ) -> trades.TradeResult:
        r"""Calculates the amount of an asset that must be provided to receive a
        specified amount of the other asset given the current AMM reserves.

        The input is calculated as:

        .. math::
            \begin{align*}
            & s \;\;\;\; = \;\;\;\; \text{lp_total_supply}\\
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
           :func:`calc_tokens_out_given_lp_in
           <elfpy.pricing_models.yieldspace.YieldSpacePricingModel.calc_tokens_out_given_lp_in>`,
           and :func:`calc_lp_out_given_tokens_in
           <elfpy.pricing_models.yieldspace.YieldSpacePricingModel.calc_lp_out_given_tokens_in>`.

           It can be approximated as :math:`s \approx y + cz`.

        Arguments
        ----------
        out : Quantity
            The quantity of tokens that the agent wants to receive (the amount
            and the unit of the tokens).
        market_state : MarketState
            The state of the AMM's reserves and share prices.
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch).

        Returns
        -------
        FixedPoint
            The amount the agent pays without fees or slippage. The units
            are always in terms of bonds or base.
        FixedPoint
            The amount the agent pays with fees and slippage. The units are
            always in terms of bonds or base.
        FixedPoint
            The amount the agent pays with slippage and no fees. The units are
            always in terms of bonds or base.
        FixedPoint
            The fee the agent pays. The units are always in terms of bonds or
            base.
        """
        # Calculate some common values up front
        time_elapsed = FixedPoint("1.0") - time_remaining.stretched_time
        spot_price = self.calc_spot_price_from_reserves(
            market_state,
            time_remaining,
        )
        if out.unit == types.TokenType.BASE:
            d_shares = out.amount / market_state.share_price
            # The amount the agent pays without fees or slippage is simply the
            # amount of base the agent would receive times the inverse of the
            # spot price of base in terms of bonds. The amount of base the agent
            # receives is given by c * dz where dz is the number of shares the
            # pool will need to unwrap to give the agent their base. If we let p
            # be the conventional spot price, then we can write this as:
            #
            # without_fee_or_slippage = (1 / p) * c * dz
            without_fee_or_slippage = (FixedPoint("1.0") / spot_price) * market_state.share_price * d_shares
            # We solve the YieldSpace invariant for the bonds paid to receive
            # the requested amount of base. We set up the invariant where the
            # agent pays dy bonds and receives dz shares:
            #
            # k = (c / mu) * (mu * (z - dz))**(1 - tau) + (y + s + dy)**(1 - tau)
            #
            # Solving for dy (without_fee) gives us the amount of bonds the agent must pay
            # without including fees:
            #
            # dy = (k - (c / mu) * (mu * (z - dz))**(1 - tau))**(1 / (1 - tau)) - (y + s)
            without_fee = self.calc_bonds_in_given_shares_out(
                share_reserves=market_state.share_reserves,
                bond_reserves=market_state.bond_reserves,
                lp_total_supply=market_state.lp_total_supply,
                d_shares=d_shares,
                time_elapsed=time_elapsed,
                share_price=market_state.share_price,
                init_share_price=market_state.init_share_price,
            )
            curve_fee = abs(out.amount - without_fee_or_slippage) * market_state.curve_fee_multiple
            gov_curve_fee = curve_fee * market_state.governance_fee_multiple
            # To get the amount paid with fees, add the fee to the calculation that
            # excluded fees. Adding the fees results in more tokens paid, which
            # indicates that the fees are working correctly.
            with_fee = without_fee + curve_fee + gov_curve_fee
            # Create the agent and market trade results.
            user_result = agent_trade_result.AgentTradeResult(
                d_base=out.amount,
                d_bonds=-with_fee,
            )
            market_result = market_action_result.MarketActionResult(
                d_base=-out.amount,
                d_bonds=with_fee,
            )
        elif out.unit == types.TokenType.PT:
            d_bonds = out.amount
            # The amount the agent pays without fees or slippage is simply
            # the amount of bonds the agent would receive times the spot price of
            # base in terms of bonds. If we let p be the conventional spot price,
            # then we can write this as:
            #
            # without_fee_or_slippage = p * dy
            without_fee_or_slippage = spot_price * d_bonds
            # We solve the YieldSpace invariant for the base paid for the
            # requested amount of bonds. We set up the invariant where the agent
            # pays d_z' shares and receives d_y bonds:
            #
            # k = (c / mu) * (mu * (z + dz))**(1 - tau) + (y + s - dy)**(1 - tau)
            #
            # Solving for dz gives us the amount of shares the agent pays
            # without including fees:
            #
            # dz = (1 / mu) * ((k - (y + s - dy)**(1 - tau)) / (c / mu))**(1 / (1 - tau)) - z
            #
            # We really want to know the value of dx (without_fee), the amount of base the
            # agent pays. This is given by dx = c * dz.
            without_fee = (
                self.calc_shares_in_given_bonds_out(
                    share_reserves=market_state.share_reserves,
                    bond_reserves=market_state.bond_reserves,
                    lp_total_supply=market_state.lp_total_supply,
                    d_bonds=d_bonds,
                    time_elapsed=time_elapsed,
                    share_price=market_state.share_price,
                    init_share_price=market_state.init_share_price,
                )
                * market_state.share_price  # convert to base
            )
            curve_fee = abs(d_bonds - without_fee_or_slippage) * market_state.curve_fee_multiple
            gov_curve_fee = curve_fee * market_state.governance_fee_multiple
            # To get the amount paid with fees, add the fee to the calculation that
            # excluded fees. Adding the fees results in more tokens paid, which
            # indicates that the fees are working correctly.
            with_fee = without_fee + curve_fee + gov_curve_fee
            # Create the agent and market trade results.
            user_result = agent_trade_result.AgentTradeResult(
                d_base=-with_fee,
                d_bonds=out.amount,
            )
            market_result = market_action_result.MarketActionResult(
                d_base=with_fee,
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
                without_fee_or_slippage=without_fee_or_slippage,
                with_fee=with_fee,
                without_fee=without_fee,
                curve_fee=curve_fee,
                gov_curve_fee=gov_curve_fee,
            ),
        )

    # TODO: The high slippage tests in tests/test_pricing_model.py should
    # arguably have much higher slippage. This is something we should
    # consider more when thinking about the use of a time stretch parameter.
    def calc_out_given_in(
        self,
        in_: types.Quantity,
        market_state: HyperdriveMarketState,
        time_remaining: time.StretchedTime,
    ) -> trades.TradeResult:
        r"""Calculates the amount of an asset that must be provided to receive a
        specified amount of the other asset given the current AMM reserves.

        The output is calculated as:

        .. math::
            \begin{align*}
            & s \;\;\;\; = \;\;\;\; \text{lp_total_supply}\\
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
           :func:`calc_tokens_out_given_lp_in
           <elfpy.pricing_models.yieldspace.YieldSpacePricingModel.calc_tokens_out_given_lp_in>`
           and :func:`calc_lp_out_given_tokens_in
           <elfpy.pricing_models.yieldspace.YieldSpacePricingModel.calc_lp_out_given_tokens_in>`.

           It can be approximated as :math:`s \approx y + cz`.

        Arguments
        ----------
        in_ : Quantity
            The quantity of tokens that the agent wants to pay (the amount
            and the unit of the tokens).
        market_state : MarketState
            The state of the AMM's reserves and share prices.
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch).

        Returns
        -------
        FixedPoint
            The amount the agent receives without fees or slippage. The units
            are always in terms of bonds or base.
        FixedPoint
            The amount the agent receives with fees and slippage. The units are
            always in terms of bonds or base.
        FixedPoint
            The amount the agent receives with slippage and no fees. The units are
            always in terms of bonds or base.
        FixedPoint
            The fee the agent pays. The units are always in terms of bonds or
            base.
        """
        # Calculate some common values up front
        time_elapsed = FixedPoint("1.0") - time_remaining.stretched_time
        spot_price = self.calc_spot_price_from_reserves(
            market_state,
            time_remaining,
        )
        if in_.unit == types.TokenType.BASE:
            d_shares = in_.amount / market_state.share_price  # convert from base_asset to z (x=cz)
            # The amount the agent would receive without fees or slippage is
            # the amount of base the agent pays times inverse of the spot price
            # of base in terms of bonds. If we let p be the conventional spot
            # price, then we can write this as:
            #
            # (1 / p) * c * dz
            without_fee_or_slippage = (FixedPoint("1.0") / spot_price) * market_state.share_price * d_shares
            # We solve the YieldSpace invariant for the bonds received from
            # paying the specified amount of base. We set up the invariant where
            # the agent pays dz shares and receives dy bonds:
            #
            # k = (c / mu) * (mu * (z + dz))**(1 - tau) + (y + s - dy)**(1 - tau)
            #
            # Where the left hand side, k, is defined above. Solving for dy (without_fee) gives
            # us the amount of bonds the agent receives without including fees:
            #
            # dy = y + s - (k - (c / mu) * (mu * (z + dz))**(1 - tau))**(1 / (1 - tau))
            without_fee = self.calc_bonds_out_given_shares_in(
                share_reserves=market_state.share_reserves,
                bond_reserves=market_state.bond_reserves,
                lp_total_supply=market_state.lp_total_supply,
                d_shares=d_shares,
                time_elapsed=time_elapsed,
                share_price=market_state.share_price,
                init_share_price=market_state.init_share_price,
            )
            curve_fee = (without_fee_or_slippage - in_.amount) * market_state.curve_fee_multiple
            gov_curve_fee = curve_fee * market_state.governance_fee_multiple
            # To get the amount paid with fees, subtract the fee from the
            # calculation that excluded fees. Subtracting the fees results in less
            # tokens received, which indicates that the fees are working correctly.
            with_fee = without_fee - curve_fee - gov_curve_fee
            # Create the agent and market trade results.
            user_result = agent_trade_result.AgentTradeResult(
                d_base=-in_.amount,
                d_bonds=with_fee,
            )
            market_result = market_action_result.MarketActionResult(
                d_base=in_.amount,
                d_bonds=-with_fee,
            )
        elif in_.unit == types.TokenType.PT:
            d_bonds = in_.amount
            # The amount the agent would receive without fees or slippage is the
            # amount of bonds the agent pays times the spot price of base in
            # terms of bonds. If we let p be the conventional spot price, then
            # we can write this as:
            #
            # p * dy
            without_fee_or_slippage = spot_price * d_bonds
            # We solve the YieldSpace invariant for the base received from
            # selling the specified amount of bonds. We set up the invariant
            # where the agent pays dy bonds and receives dz shares:
            #
            # k = (c / mu) * (mu * (z - dz))**(1 - tau) + (y + s + dy)**(1 - tau)
            #
            # Solving for dz gives us the amount of shares the agent receives
            # without fees:
            #
            # dz = z - (1 / mu) * ((k - (y + s + dy)**(1 - tau)) / (c / mu))**(1 / (1 - tau))
            #
            # We really want to know the value of dx (without_fee), the amount of base the
            # agent receives without fees. This is given by dx = c * dz.
            without_fee = (
                self.calc_shares_out_given_bonds_in(
                    share_reserves=market_state.share_reserves,
                    bond_reserves=market_state.bond_reserves,
                    lp_total_supply=market_state.lp_total_supply,
                    d_bonds=d_bonds,
                    time_elapsed=time_elapsed,
                    share_price=market_state.share_price,
                    init_share_price=market_state.init_share_price,
                )
                * market_state.share_price  # convert back to base
            )
            curve_fee = (d_bonds - without_fee_or_slippage) * market_state.curve_fee_multiple
            gov_curve_fee = curve_fee * market_state.governance_fee_multiple
            # To get the amount paid with fees, subtract the fee from the
            # calculation that excluded fees. Subtracting the fees results in less
            # tokens received, which indicates that the fees are working correctly.
            with_fee = without_fee - curve_fee - gov_curve_fee
            # Create the agent and market trade results.
            user_result = agent_trade_result.AgentTradeResult(
                d_base=with_fee,
                d_bonds=-in_.amount,
            )
            market_result = market_action_result.MarketActionResult(
                d_base=-with_fee,
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
                without_fee_or_slippage=without_fee_or_slippage,
                with_fee=with_fee,
                without_fee=without_fee,
                curve_fee=curve_fee,
                gov_curve_fee=gov_curve_fee,
            ),
        )

    def calc_bonds_in_given_shares_out(
        self,
        share_reserves: FixedPoint,
        bond_reserves: FixedPoint,
        lp_total_supply: FixedPoint,
        d_shares: FixedPoint,
        time_elapsed: FixedPoint,
        share_price: FixedPoint,
        init_share_price: FixedPoint,
    ) -> FixedPoint:
        """Calculates the amount of bonds a agent must provide the pool to receive a specified amount of shares.

        Arguments
        ----------
            share_reserves : FixedPoint
                "z"; Amount of share reserves in the pool.
            bond_reserves : FixedPoint
                "y"; Amount of bond reserves in the pool.
            lp_total_supply : FixedPoint
                "s"; An adjustment to the bond reserve that is equal to the total number of lp tokens issued
            d_shares : FixedPoint
                "dz"; Amount of shares agent wants to provide.
            time_elapsed : FixedPoint
                "1 - tau"; Amount of time elapsed since term start.
            share_price : FixedPoint
                "c"; Conversion rate between base and shares.
            init_share_price : FixedPoint
                "mu"; Interest normalization factor for shares.

        Returns
        -------
            d_bonds : FixedPoint
                "dy"; Amount of bonds in required to get the d_shares out.
        """
        # k = (c / mu) * (mu * z)**(1 - tau) + (y + s)**(1 - tau)
        yieldspace_const = self.calc_yieldspace_const(
            share_reserves, bond_reserves, lp_total_supply, time_elapsed, share_price, init_share_price
        )
        # dy = (k - (c / mu) * (mu * (z - dz))**(1 - tau))**(1 / (1 - tau)) - (y + s)
        return (
            yieldspace_const
            - (share_price / init_share_price) * (init_share_price * (share_reserves - d_shares)) ** (time_elapsed)
        ) ** (FixedPoint("1.0").div_up(time_elapsed)) - (bond_reserves + lp_total_supply)

    # TODO: have this wrap the solidity mirrored version as a part of the parity effort.
    def calc_bonds_out_given_shares_in(
        self,
        share_reserves: FixedPoint,
        bond_reserves: FixedPoint,
        lp_total_supply: FixedPoint,
        d_shares: FixedPoint,
        time_elapsed: FixedPoint,
        share_price: FixedPoint,
        init_share_price: FixedPoint,
    ) -> FixedPoint:
        """Calculates the amount of bonds a agent will receive from the pool by providing a specified amount of shares

        Arguments
        ----------
            share_reserves : FixedPoint
                "z"; Amount of share reserves in the pool.
            bond_reserves : FixedPoint
                "y"; Amount of bond reserves in the pool.
            lp_total_supply : FixedPoint
                "s"; An adjustment to the bond reserve that is equal to the total number of lp tokens issued
            d_shares : FixedPoint
                "dz"; Amount of shares agent wants to provide.
            time_elapsed : FixedPoint
                "1 - tau"; Amount of time elapsed since term start.
            share_price : FixedPoint
                "c"; Conversion rate between base and shares.
            init_share_price : FixedPoint
                "mu"; Interest normalization factor for shares.

        Returns
        -------
            d_bonds : FixedPoint
                "dy"; Amount of bonds for the input shares amount.
        """
        # k = (c / mu) * (mu * z)**(1 - tau) + (y + s)**(1 - tau)
        yieldspace_const = self.calc_yieldspace_const(
            share_reserves, bond_reserves, lp_total_supply, time_elapsed, share_price, init_share_price
        )
        # dy = y + s - (k - (c / mu) * (mu * (z + dz))**(1 - tau))**(1 / (1 - tau))
        return (bond_reserves + lp_total_supply) - (
            yieldspace_const
            - (share_price / init_share_price) * (init_share_price * (share_reserves + d_shares)) ** time_elapsed
        ) ** (FixedPoint("1.0").div_up(time_elapsed))

    def calc_shares_in_given_bonds_out(
        self,
        share_reserves: FixedPoint,
        bond_reserves: FixedPoint,
        lp_total_supply: FixedPoint,
        d_bonds: FixedPoint,
        time_elapsed: FixedPoint,
        share_price: FixedPoint,
        init_share_price: FixedPoint,
    ) -> FixedPoint:
        """Calculates the amount of shares a agent must provide the pool to receive a specified amount of bonds.

        Arguments
        ----------
            share_reserves : FixedPoint
                "z"; Amount of share reserves in the pool.
            bond_reserves : FixedPoint
                "y"; Amount of bond reserves in the pool.
            lp_total_supply : FixedPoint
                "s"; An adjustment to the bond reserve that is equal to the total number of lp tokens issued
            d_bonds : FixedPoint
                "dy"; Amount of bonds agent wants to provide.
            time_elapsed : FixedPoint
                "1 - tau"; Amount of time elapsed since term start.
            share_price : FixedPoint
                "c"; Conversion rate between base and shares.
            init_share_price : FixedPoint
                "mu"; Interest normalization factor for shares, aka the conversion rate at time=0.

        Returns
        -------
            delta_shares : FixedPoint
                "dz"; The amount of bonds the agent wants to provide.
        """
        # k = (c / mu) * (mu * z)**(1 - tau) + (y + s)**(1 - tau)
        yieldspace_const = self.calc_yieldspace_const(
            share_reserves, bond_reserves, lp_total_supply, time_elapsed, share_price, init_share_price
        )
        return (
            (
                (
                    (yieldspace_const - (bond_reserves + lp_total_supply - d_bonds) ** time_elapsed)
                    / (share_price / init_share_price)
                )
                ** (FixedPoint("1.0").div_up(time_elapsed))
                # div up here to prevent negative values when trade amount is very small (100-ish wei hor less)
            ).div_up(init_share_price)
        ) - share_reserves

    def calc_shares_out_given_bonds_in(
        self,
        share_reserves: FixedPoint,
        bond_reserves: FixedPoint,
        lp_total_supply: FixedPoint,
        d_bonds: FixedPoint,
        time_elapsed: FixedPoint,
        share_price: FixedPoint,
        init_share_price: FixedPoint,
    ) -> FixedPoint:
        """Calculates the amount of shares a agent will receive from the pool by providing a specified amount of bonds.

        Arguments
        ----------
            share_reserves : FixedPoint
                "z"; The amount of share reserves in the pool.
            bond_reserves : FixedPoint
                "y"; The amount of bond reserves in the pool.
            lp_total_supply : FixedPoint
                "s"; An adjustment to the bond reserve that is equal to the total number of lp tokens issued
            d_bonds : FixedPoint
                "dy"; The amount of bonds the agent wants to provide.
            time_elapsed : FixedPoint
                "1 - tau"; Amount of time elapsed since term start.
                Elsewhere, this is also depicted as (1 - tau), where tau is stretched_time.
            share_price : FixedPoint
                "c"; Conversion rate between base and shares.
            init_share_price : FixedPoint
                "mu"; Interest normalization factor for shares, aka the conversion rate at time=0.

        Returns
        -------
            delta_shares : FixedPoint
                "dz"; The change in shares that resulted from bonds coming in.
        """
        # k = (c / mu) * (mu * z)**(1 - tau) + (y + s)**(1 - tau)
        yieldspace_const = self.calc_yieldspace_const(
            share_reserves, bond_reserves, lp_total_supply, time_elapsed, share_price, init_share_price
        )
        # dz = z - (1 / mu) * ((k - (y + s + dy)**(1 - tau)) / (c / mu))**(1 / (1 - tau))
        return share_reserves - (FixedPoint("1.0") / init_share_price) * (
            (yieldspace_const - (bond_reserves + lp_total_supply + d_bonds) ** time_elapsed)
            / (share_price / init_share_price)
        ) ** (FixedPoint("1.0").div_up(time_elapsed))

    # TODO: have this wrap the solidity mirrored version as a part of the parity effort.
    def calc_yieldspace_const(
        self,
        share_reserves: FixedPoint,
        bond_reserves: FixedPoint,
        lp_total_supply: FixedPoint,
        time_elapsed: FixedPoint,
        share_price: FixedPoint,
        init_share_price: FixedPoint,
    ) -> FixedPoint:
        r"""Helper function to derive invariant constant K

        .. math::
            k = \frac{c}{\mu} (\mu z)^{1 - \tau} + (y + s)^{1 - \tau}

        Arguments
        ----------
            share_reserves : FixedPoint
                "z"; The amount of share reserves in the pool.
            bond_reserves : FixedPoint
                "y"; The amount of bond reserves in the pool.
            lp_total_supply : FixedPoint
                "s"; An adjustment to the bond reserve that is equal to the total number of lp tokens issued
            time_elapsed : FixedPoint
                "t"; Amount of time elapsed since term start.
                This is also depicted as (1 - tau), where tau is stretched_time.
            share_price : FixedPoint
                "c"; The conversion rate between base and shares.
            init_share_price : FixedPoint
                "mu"; The interest normalization factor for shares, aka the conversion rate at time=0.

        Returns
        -------
            yieldspace_constant : FixedPoint
                "k"; The yieldspace constant.
        """
        # k = (c / mu) * (mu * z)^(1 - tau) + (y + s)^(1 - tau)
        return (share_price / init_share_price) * (init_share_price * share_reserves) ** time_elapsed + (
            bond_reserves + lp_total_supply
        ) ** time_elapsed

    def calc_tokens_out_given_lp_in(
        self, lp_in: FixedPoint, market_state: HyperdriveMarketState
    ) -> tuple[FixedPoint, FixedPoint]:
        """Calculates the amount of base shares and bonds released from burning
        a a specified amount of LP shares from the pool.

        Arguments
        ----------
        lp_in : FixedPoint
            The amount of lp shares that are given back to the pool
        market_state : MarketStateFP
            The state of the AMM's reserves and share prices.

        Returns
        -------
        FixedPoint
            The amount of shares taken out of reserves
        FixedPoint
            The amount of bonds taken out of reserves
        """
        # get the shares out to the user
        percent_of_lp_shares = lp_in / market_state.lp_total_supply
        # dz = (z - o_l / c) * (dl / l)
        shares_delta = (
            market_state.share_reserves - market_state.longs_outstanding / market_state.share_price
        ) * percent_of_lp_shares

        bonds_delta = (
            market_state.bond_reserves
            - market_state.bond_reserves * (market_state.share_reserves - shares_delta) / market_state.share_reserves
        )
        # these are both positive values
        return shares_delta, bonds_delta

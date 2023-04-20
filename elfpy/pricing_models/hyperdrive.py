"""The Hyperdrive pricing model"""
from __future__ import annotations  # types will be strings by default in 3.11

from decimal import Decimal
from typing import TYPE_CHECKING

import elfpy.agents.agent_trade_result as agent_trade_result
import elfpy.markets.hyperdrive.market_action_result as market_action_result
import elfpy.pricing_models.trades as trades
import elfpy.pricing_models.yieldspace as yieldspace_pm
import elfpy.time as time
import elfpy.types as types
from elfpy.utils.math import FixedPoint

if TYPE_CHECKING:
    import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market

# TODO: remove this after FixedPoint PRs are finished
# pylint: disable=too-many-lines


class HyperdrivePricingModel(yieldspace_pm.YieldspacePricingModel):
    """
    Hyperdrive Pricing Model

    This pricing model uses a combination of the Constant Sum and Yield Space
    invariants with modifications to the Yield Space invariant that enable the
    base reserves to be deposited into yield bearing vaults
    """

    def model_name(self) -> str:
        return "Hyperdrive"

    def model_type(self) -> str:
        return "hyperdrive"

    def calc_in_given_out(
        self,
        out: types.Quantity,
        market_state: hyperdrive_market.MarketState,
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
            \quad\quad\quad c \big(\mu^{-1} \big(\mu \cdot c^{-1}
            \big(k - \big(y + s - \Delta y \cdot t\big)
            ^{1-\tau}\big)\big)
            ^ {\tfrac{1}{1-\tau}} - z\big) + \Delta y \cdot\big(1 - \tau\big)
            \\\\
            \text{ if $token\_in$ = "pt", }\\
            \quad\quad\quad (k - \big(
            c \cdot \mu^{-1} \cdot\big(\mu \cdot
            \big(z - \Delta z \cdot t\big)\big)^{1 - \tau} \big))
            ^{\tfrac{1}{1 - \tau}} - \big(y + s\big)
            + c \cdot \Delta z \cdot\big(1 - \tau\big)
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
           <elfpy.pricing_models.yieldspace.YieldSpacePricingModel.calc_tokens_out_given_lp_in>`
           and :func:`calc_lp_out_given_tokens_in
           <elfpy.pricing_models.yieldspace.YieldSpacePricingModel.calc_lp_out_given_tokens_in>`.

           It can be approximated as :math:`s \approx y + cz`.

        Parameters
        ----------
        out : Quantity
            The quantity of tokens that the user wants to receive (the amount and the unit of the tokens).
        market_state : MarketState
            The state of the AMM's reserves and share prices.
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch).

        Returns
        -------
        TradeResult
            The result of performing the trade
        """
        # Calculate some common values up front
        out_amount = Decimal(out.amount)
        normalized_time_remaining = Decimal(time_remaining.normalized_time)
        d_bonds = out_amount * (
            1 - normalized_time_remaining
        )  # whether out_.unit is base or pt, at maturity d_bonds = d_base
        d_shares = d_bonds / Decimal(market_state.share_price)
        # Redeem the matured bonds 1:1 and simulate these updates hitting the reserves.
        market_state = market_state.copy()
        if out.unit == types.TokenType.BASE:
            market_state.share_reserves -= float(d_shares)
            market_state.bond_reserves += float(d_bonds)
        elif out.unit == types.TokenType.PT:
            market_state.share_reserves += float(d_shares)
            market_state.bond_reserves -= float(d_bonds)
        else:
            raise AssertionError(
                "pricing_models.calc_in_given_out: ERROR: "
                f"Expected out.unit to be {types.TokenType.BASE} or {types.TokenType.PT}, not {out.unit}!"
            )
        # Compute flat part with fee
        flat_without_fee = out_amount * (1 - normalized_time_remaining)
        flat_fee = flat_without_fee * Decimal(market_state.flat_fee_multiple)
        gov_flat_fee = flat_fee * Decimal(market_state.governance_fee_multiple)
        flat_with_fee = flat_without_fee + flat_fee + gov_flat_fee
        # Trade the bonds that haven't matured on the YieldSpace curve.
        curve = super().calc_in_given_out(
            out=types.Quantity(amount=float(out_amount * normalized_time_remaining), unit=out.unit),
            market_state=market_state,
            time_remaining=time.StretchedTime(  # time remaining is always fixed to the full term for flat+curve
                days=time_remaining.normalizing_constant,  # position duration is the normalizing constant
                time_stretch=time_remaining.time_stretch,
                normalizing_constant=time_remaining.normalizing_constant,
            ),
        )
        # Compute the user's trade result including both the flat and the curve parts of the trade.
        if out.unit == types.TokenType.BASE:
            user_result = agent_trade_result.AgentTradeResult(
                d_base=out.amount,
                d_bonds=float(-flat_with_fee + Decimal(curve.user_result.d_bonds)),
            )
            market_result = market_action_result.MarketActionResult(
                d_base=-out.amount,
                d_bonds=curve.market_result.d_bonds,
            )
        elif out.unit == types.TokenType.PT:
            user_result = agent_trade_result.AgentTradeResult(
                d_base=float(-flat_with_fee + Decimal(curve.user_result.d_base)),
                d_bonds=out.amount,
            )
            market_result = market_action_result.MarketActionResult(
                d_base=float(flat_with_fee + Decimal(curve.market_result.d_base)),
                d_bonds=curve.market_result.d_bonds,
            )
        else:
            raise AssertionError(
                f"ERROR: Expected out.unit to be {types.TokenType.BASE} or {types.TokenType.PT}, not {out.unit}!"
            )
        return trades.TradeResult(
            user_result=user_result,
            market_result=market_result,
            breakdown=trades.TradeBreakdown(
                without_fee_or_slippage=float(flat_without_fee + Decimal(curve.breakdown.without_fee_or_slippage)),
                without_fee=float(flat_without_fee + Decimal(curve.breakdown.without_fee)),
                with_fee=float(flat_with_fee + Decimal(curve.breakdown.with_fee)),
                curve_fee=float(curve.breakdown.curve_fee),
                gov_curve_fee=float(curve.breakdown.gov_curve_fee),
                flat_fee=float(flat_fee),
                gov_flat_fee=float(gov_flat_fee),
            ),
        )

    # TODO: The high slippage tests in tests/test_pricing_model.py should
    # arguably have much higher slippage. This is something we should
    # consider more when thinking about the use of a time stretch parameter.
    def calc_out_given_in(
        self,
        in_: types.Quantity,
        market_state: hyperdrive_market.MarketState,
        time_remaining: time.StretchedTime,
    ) -> trades.TradeResult:
        r"""
        Calculates the amount of an asset that must be provided to receive a specified amount of the
        other asset given the current AMM reserves.

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
            \big(c \cdot \mu^{-1} \big(k - \big(y + s + \Delta y \cdot t\big)
            ^{1 - \tau}\big)\big)
            ^{\tfrac{1}{1 - \tau}}\big) + \Delta y \cdot (1 - \tau)
            \\\\
            \text{ if $token\_out$ = "pt", }\\
            \quad\quad\quad y + s - (k - c \cdot \mu^{-1} \cdot
            (\mu (z + \Delta z \cdot t))^{1 - \tau})
            ^{\tfrac{1}{1 - \tau}} + c \cdot \Delta z \cdot (1 - \tau)
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
        TradeResult
            The result of performing the trade.
        """
        # Calculate some common values up front
        in_amount = Decimal(in_.amount)
        normalized_time_remaining = Decimal(time_remaining.normalized_time)
        d_bonds = in_amount * (
            1 - normalized_time_remaining
        )  # whether in_.unit is base or pt, at maturity d_bonds = d_base
        d_shares = d_bonds / Decimal(market_state.share_price)
        # Redeem the matured bonds 1:1 and simulate these updates hitting the reserves.
        market_state = market_state.copy()  # don't want to modify the actual market state
        if in_.unit == types.TokenType.BASE:
            market_state.share_reserves += float(d_shares)
            market_state.bond_reserves -= float(d_bonds)
        elif in_.unit == types.TokenType.PT:
            market_state.share_reserves -= float(d_shares)
            market_state.bond_reserves += float(d_bonds)
        else:
            raise AssertionError(
                "pricing_models.calc_out_given_in: ERROR: "
                f"Expected in_.unit to be {types.TokenType.BASE} or {types.TokenType.PT}, not {in_.unit}!"
            )
        # Compute flat part with fee
        flat_without_fee = in_amount * (1 - normalized_time_remaining)
        flat_fee = flat_without_fee * Decimal(market_state.flat_fee_multiple)
        gov_flat_fee = flat_fee * Decimal(market_state.governance_fee_multiple)
        flat_with_fee = flat_without_fee - (flat_fee + gov_flat_fee)
        # Trade the bonds that haven't matured on the YieldSpace curve.
        curve = super().calc_out_given_in(
            in_=types.Quantity(amount=float(in_amount * normalized_time_remaining), unit=in_.unit),
            market_state=market_state,
            time_remaining=time.StretchedTime(  # time remaining is always fixed to the full term for the curve
                days=time_remaining.normalizing_constant,  # position duration is the normalizing constant
                time_stretch=time_remaining.time_stretch,
                normalizing_constant=time_remaining.normalizing_constant,
            ),
        )
        # Compute the user's trade result including both the flat and the curve parts of the trade.
        if in_.unit == types.TokenType.BASE:
            user_result = agent_trade_result.AgentTradeResult(
                d_base=-in_.amount,
                d_bonds=float(flat_with_fee + Decimal(curve.user_result.d_bonds)),
            )
            market_result = market_action_result.MarketActionResult(
                d_base=in_.amount,
                d_bonds=curve.market_result.d_bonds,
            )
        elif in_.unit == types.TokenType.PT:
            user_result = agent_trade_result.AgentTradeResult(
                d_base=float(flat_with_fee + Decimal(curve.user_result.d_base)),
                d_bonds=-in_.amount,
            )
            market_result = market_action_result.MarketActionResult(
                d_base=float(-flat_with_fee + Decimal(curve.market_result.d_base)),
                d_bonds=curve.market_result.d_bonds,
            )
        else:
            raise AssertionError(
                "pricing_models.calc_out_given_in: ERROR: "
                f"Expected in_.unit to be {types.TokenType.BASE} or {types.TokenType.PT}, not {in_.unit}!"
            )
        return trades.TradeResult(
            user_result=user_result,
            market_result=market_result,
            breakdown=trades.TradeBreakdown(
                without_fee_or_slippage=float(flat_without_fee + Decimal(curve.breakdown.without_fee_or_slippage)),
                without_fee=float(flat_without_fee + Decimal(curve.breakdown.without_fee)),
                with_fee=float(flat_with_fee + Decimal(curve.breakdown.with_fee)),
                curve_fee=float(curve.breakdown.curve_fee),
                gov_curve_fee=float(curve.breakdown.gov_curve_fee),
                flat_fee=float(flat_fee),
                gov_flat_fee=float(gov_flat_fee),
            ),
        )

    def calc_tokens_out_given_lp_in(
        self, lp_in: float, market_state: hyperdrive_market.MarketState
    ) -> tuple[float, float]:
        """
        Calculates the amount of base shares and bonds released from burning a specified amount of
        LP shares from the pool.

        Parameters
        ----------
        lp_in: float
            The amount of lp shares that are given back to the pool
        market_state : MarketState
            The state of the AMM's reserves and share prices.

        Returns
        -------
        float
            The amount of shares taken out of reserves
        float
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


class HyperdrivePricingModelFP(yieldspace_pm.YieldspacePricingModelFP):
    """
    Hyperdrive Pricing Model

    This pricing model uses a combination of the Constant Sum and Yield Space
    invariants with modifications to the Yield Space invariant that enable the
    base reserves to be deposited into yield bearing vaults
    """

    def model_name(self) -> str:
        return "Hyperdrive"

    def model_type(self) -> str:
        return "hyperdrive"

    def calc_in_given_out(
        self,
        out: types.QuantityFP,
        market_state: hyperdrive_market.MarketStateFP,
        time_remaining: time.StretchedTimeFP,
    ) -> trades.TradeResultFP:
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
            \quad\quad\quad c \big(\mu^{-1} \big(\mu \cdot c^{-1}
            \big(k - \big(y + s - \Delta y \cdot t\big)
            ^{1-\tau}\big)\big)
            ^ {\tfrac{1}{1-\tau}} - z\big) + \Delta y \cdot\big(1 - \tau\big)
            \\\\
            \text{ if $token\_in$ = "pt", }\\
            \quad\quad\quad (k - \big(
            c \cdot \mu^{-1} \cdot\big(\mu \cdot
            \big(z - \Delta z \cdot t\big)\big)^{1 - \tau} \big))
            ^{\tfrac{1}{1 - \tau}} - \big(y + s\big)
            + c \cdot \Delta z \cdot\big(1 - \tau\big)
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
           <elfpy.pricing_models.yieldspace.YieldSpacePricingModel.calc_tokens_out_given_lp_in>`
           and :func:`calc_lp_out_given_tokens_in
           <elfpy.pricing_models.yieldspace.YieldSpacePricingModel.calc_lp_out_given_tokens_in>`.

           It can be approximated as :math:`s \approx y + cz`.

        Parameters
        ----------
        out : Quantity
            The quantity of tokens that the user wants to receive (the amount and the unit of the tokens).
        market_state : MarketState
            The state of the AMM's reserves and share prices.
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch).

        Returns
        -------
        TradeResult
            The result of performing the trade
        """
        # Calculate some common values up front
        d_bonds = out.amount * (
            FixedPoint("1.0") - time_remaining.normalized_time
        )  # whether out_.unit is base or pt, at maturity d_bonds = d_base
        d_shares = d_bonds / market_state.share_price
        # Redeem the matured bonds 1:1 and simulate these updates hitting the reserves.
        market_state = market_state.copy()
        if out.unit == types.TokenType.BASE:
            market_state.share_reserves -= d_shares
            market_state.bond_reserves += d_bonds
        elif out.unit == types.TokenType.PT:
            market_state.share_reserves += d_shares
            market_state.bond_reserves -= d_bonds
        else:
            raise AssertionError(
                "pricing_models.calc_in_given_out: ERROR: "
                f"Expected out.unit to be {types.TokenType.BASE} or {types.TokenType.PT}, not {out.unit}!"
            )
        # Compute flat part with fee
        flat_without_fee = out.amount * (FixedPoint("1.0") - time_remaining.normalized_time)
        flat_fee = flat_without_fee * market_state.flat_fee_multiple
        gov_flat_fee = flat_fee * market_state.governance_fee_multiple
        flat_with_fee = flat_without_fee + flat_fee + gov_flat_fee
        # Trade the bonds that haven't matured on the YieldSpace curve.
        curve = super().calc_in_given_out(
            out=types.QuantityFP(amount=out.amount * time_remaining.normalized_time, unit=out.unit),
            market_state=market_state,
            time_remaining=time.StretchedTimeFP(  # time remaining is always fixed to the full term for flat+curve
                days=time_remaining.normalizing_constant,  # position duration is the normalizing constant
                time_stretch=time_remaining.time_stretch,
                normalizing_constant=time_remaining.normalizing_constant,
            ),
        )
        # Compute the user's trade result including both the flat and the curve parts of the trade.
        if out.unit == types.TokenType.BASE:
            user_result = agent_trade_result.AgentTradeResultFP(
                d_base=out.amount,
                d_bonds=-flat_with_fee + curve.user_result.d_bonds,
            )
            market_result = market_action_result.MarketActionResultFP(
                d_base=-out.amount,
                d_bonds=curve.market_result.d_bonds,
            )
        elif out.unit == types.TokenType.PT:
            user_result = agent_trade_result.AgentTradeResultFP(
                d_base=-flat_with_fee + curve.user_result.d_base,
                d_bonds=out.amount,
            )
            market_result = market_action_result.MarketActionResultFP(
                d_base=flat_with_fee + curve.market_result.d_base,
                d_bonds=curve.market_result.d_bonds,
            )
        else:
            raise AssertionError(
                f"ERROR: Expected out.unit to be {types.TokenType.BASE} or {types.TokenType.PT}, not {out.unit}!"
            )
        return trades.TradeResultFP(
            user_result=user_result,
            market_result=market_result,
            breakdown=trades.TradeBreakdownFP(
                without_fee_or_slippage=flat_without_fee + curve.breakdown.without_fee_or_slippage,
                without_fee=flat_without_fee + curve.breakdown.without_fee,
                with_fee=flat_with_fee + curve.breakdown.with_fee,
                curve_fee=curve.breakdown.curve_fee,
                gov_curve_fee=curve.breakdown.gov_curve_fee,
                flat_fee=flat_fee,
                gov_flat_fee=gov_flat_fee,
            ),
        )

    # TODO: The high slippage tests in tests/test_pricing_model.py should
    # arguably have much higher slippage. This is something we should
    # consider more when thinking about the use of a time stretch parameter.
    def calc_out_given_in(
        self,
        in_: types.QuantityFP,
        market_state: hyperdrive_market.MarketStateFP,
        time_remaining: time.StretchedTimeFP,
    ) -> trades.TradeResultFP:
        r"""
        Calculates the amount of an asset that must be provided to receive a specified amount of the
        other asset given the current AMM reserves.

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
            \big(c \cdot \mu^{-1} \big(k - \big(y + s + \Delta y \cdot t\big)
            ^{1 - \tau}\big)\big)
            ^{\tfrac{1}{1 - \tau}}\big) + \Delta y \cdot (1 - \tau)
            \\\\
            \text{ if $token\_out$ = "pt", }\\
            \quad\quad\quad y + s - (k - c \cdot \mu^{-1} \cdot
            (\mu (z + \Delta z \cdot t))^{1 - \tau})
            ^{\tfrac{1}{1 - \tau}} + c \cdot \Delta z \cdot (1 - \tau)
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
        TradeResult
            The result of performing the trade.
        """
        # Calculate some common values up front
        d_bonds = in_.amount * (
            FixedPoint("1.0") - time_remaining.normalized_time
        )  # whether in_.unit is base or pt, at maturity d_bonds = d_base
        d_shares = d_bonds / market_state.share_price
        # Redeem the matured bonds 1:1 and simulate these updates hitting the reserves.
        market_state = market_state.copy()  # don't want to modify the actual market state
        if in_.unit == types.TokenType.BASE:
            market_state.share_reserves += d_shares
            market_state.bond_reserves -= d_bonds
        elif in_.unit == types.TokenType.PT:
            market_state.share_reserves -= d_shares
            market_state.bond_reserves += d_bonds
        else:
            raise AssertionError(
                "pricing_models.calc_out_given_in: ERROR: "
                f"Expected in_.unit to be {types.TokenType.BASE} or {types.TokenType.PT}, not {in_.unit}!"
            )
        # Compute flat part with fee
        flat_without_fee = in_.amount * (FixedPoint("1.0") - time_remaining.normalized_time)
        flat_fee = flat_without_fee * market_state.flat_fee_multiple
        gov_flat_fee = flat_fee * market_state.governance_fee_multiple
        flat_with_fee = flat_without_fee - (flat_fee + gov_flat_fee)
        # Trade the bonds that haven't matured on the YieldSpace curve.
        curve = super().calc_out_given_in(
            in_=types.QuantityFP(amount=in_.amount * time_remaining.normalized_time, unit=in_.unit),
            market_state=market_state,
            time_remaining=time.StretchedTimeFP(  # time remaining is always fixed to the full term for the curve
                days=time_remaining.normalizing_constant,  # position duration is the normalizing constant
                time_stretch=time_remaining.time_stretch,
                normalizing_constant=time_remaining.normalizing_constant,
            ),
        )
        # Compute the user's trade result including both the flat and the curve parts of the trade.
        if in_.unit == types.TokenType.BASE:
            user_result = agent_trade_result.AgentTradeResultFP(
                d_base=-in_.amount,
                d_bonds=flat_with_fee + curve.user_result.d_bonds,
            )
            market_result = market_action_result.MarketActionResultFP(
                d_base=in_.amount,
                d_bonds=curve.market_result.d_bonds,
            )
        elif in_.unit == types.TokenType.PT:
            user_result = agent_trade_result.AgentTradeResultFP(
                d_base=flat_with_fee + curve.user_result.d_base,
                d_bonds=-in_.amount,
            )
            market_result = market_action_result.MarketActionResultFP(
                d_base=-flat_with_fee + curve.market_result.d_base,
                d_bonds=curve.market_result.d_bonds,
            )
        else:
            raise AssertionError(
                "pricing_models.calc_out_given_in: ERROR: "
                f"Expected in_.unit to be {types.TokenType.BASE} or {types.TokenType.PT}, not {in_.unit}!"
            )
        return trades.TradeResultFP(
            user_result=user_result,
            market_result=market_result,
            breakdown=trades.TradeBreakdownFP(
                without_fee_or_slippage=flat_without_fee + curve.breakdown.without_fee_or_slippage,
                without_fee=flat_without_fee + curve.breakdown.without_fee,
                with_fee=flat_with_fee + curve.breakdown.with_fee,
                curve_fee=curve.breakdown.curve_fee,
                gov_curve_fee=curve.breakdown.gov_curve_fee,
                flat_fee=flat_fee,
                gov_flat_fee=gov_flat_fee,
            ),
        )

    def calc_tokens_out_given_lp_in(
        self, lp_in: FixedPoint, market_state: hyperdrive_market.MarketStateFP
    ) -> tuple[FixedPoint, FixedPoint]:
        """
        Calculates the amount of base shares and bonds released from burning a specified amount of
        LP shares from the pool.

        Parameters
        ----------
        lp_in: FixedPoint
            The amount of lp shares that are given back to the pool
        market_state : MarketState
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

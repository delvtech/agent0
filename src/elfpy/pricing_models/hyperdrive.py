"""The Hyperdrive pricing model"""
from __future__ import annotations  # types will be strings by default in 3.11

from decimal import Decimal
from typing import TYPE_CHECKING

from elfpy.pricing_models.yieldspace import YieldSpacePricingModel
import elfpy.markets.hyperdrive as hyperdrive
import elfpy.simulators.trades as trades
import elfpy.utils.time as time_utils
from elfpy.agents.agent import AgentTradeResult

if TYPE_CHECKING:
    from elfpy.markets.hyperdrive import MarketState


class HyperdrivePricingModel(YieldSpacePricingModel):
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
        out: trades.Quantity,
        market_state: MarketState,
        time_remaining: time_utils.StretchedTime,
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
        out_amount = Decimal(out.amount)
        normalized_time = Decimal(time_remaining.normalized_time)
        share_price = Decimal(market_state.share_price)
        d_bonds = out_amount * (1 - normalized_time)
        d_shares = d_bonds / share_price

        market_state = market_state.copy()

        # TODO: This is somewhat strange since these updates never actually hit the reserves.
        # Redeem the matured bonds 1:1 and simulate these updates hitting the reserves.
        if out.unit == trades.TokenType.BASE:
            market_state.share_reserves -= float(d_shares)
            market_state.bond_reserves += float(d_bonds)
        elif out.unit == trades.TokenType.PT:
            market_state.share_reserves += float(d_shares)
            market_state.bond_reserves -= float(d_bonds)
        else:
            raise AssertionError(
                "pricing_models.calc_in_given_out: ERROR: "
                f"Expected out.unit to be {trades.TokenType.BASE} or {trades.TokenType.PT}, not {out.unit}!"
            )
        # Trade the bonds that haven't matured on the YieldSpace curve.
        curve = super().calc_in_given_out(
            out=trades.Quantity(amount=float(out_amount * normalized_time), unit=out.unit),
            market_state=market_state,
            time_remaining=time_utils.StretchedTime(  # time remaining is always fixed to the full term for flat+curve
                days=time_remaining.normalizing_constant,  # position duration is the normalizing constant
                time_stretch=time_remaining.time_stretch,
                normalizing_constant=time_remaining.normalizing_constant,
            ),
        )

        # Compute flat part with fee
        flat_without_fee = out_amount * (1 - normalized_time)
        redemption_fee = flat_without_fee * Decimal(market_state.redemption_fee_percent)
        flat_with_fee = flat_without_fee + redemption_fee

        # Compute the user's trade result including both the flat and the curve parts of the trade.
        if out.unit == trades.TokenType.BASE:
            user_result = AgentTradeResult(
                d_base=out.amount,
                d_bonds=float(-flat_with_fee + Decimal(curve.user_result.d_bonds)),
            )
            market_result = hyperdrive.MarketTradeResult(
                d_base=-out.amount,
                d_bonds=curve.market_result.d_bonds,
            )
        elif out.unit == trades.TokenType.PT:
            user_result = AgentTradeResult(
                d_base=float(-flat_with_fee + Decimal(curve.user_result.d_base)),
                d_bonds=out.amount,
            )
            market_result = hyperdrive.MarketTradeResult(
                d_base=float(flat_with_fee + Decimal(curve.market_result.d_base)),
                d_bonds=curve.market_result.d_bonds,
            )
        else:
            raise AssertionError(
                f"ERROR: Expected out.unit to be {trades.TokenType.BASE} or {trades.TokenType.PT}, not {out.unit}!"
            )

        return trades.TradeResult(
            user_result=user_result,
            market_result=market_result,
            breakdown=trades.TradeBreakdown(
                without_fee_or_slippage=float(flat_without_fee + Decimal(curve.breakdown.without_fee_or_slippage)),
                without_fee=float(flat_without_fee + Decimal(curve.breakdown.without_fee)),
                fee=float(redemption_fee + Decimal(curve.breakdown.fee)),
                with_fee=float(flat_with_fee + Decimal(curve.breakdown.with_fee)),
            ),
        )

    # TODO: The high slippage tests in tests/test_pricing_model.py should
    # arguably have much higher slippage. This is something we should
    # consider more when thinking about the use of a time stretch parameter.
    def calc_out_given_in(
        self,
        in_: trades.Quantity,
        market_state: MarketState,
        time_remaining: time_utils.StretchedTime,
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
        TradeResult
            The result of performing the trade.
        """

        # Calculate some common values up front
        in_amount = Decimal(in_.amount)
        normalized_time = Decimal(time_remaining.normalized_time)
        share_price = Decimal(market_state.share_price)
        d_bonds = in_amount * (1 - normalized_time)
        d_shares = d_bonds / share_price

        market_state = market_state.copy()

        # TODO: This is somewhat strange since these updates never actually hit the reserves.
        # Redeem the matured bonds 1:1 and simulate these updates hitting the reserves.
        if in_.unit == trades.TokenType.BASE:
            market_state.share_reserves += float(d_shares)
            market_state.bond_reserves -= float(d_bonds)
        elif in_.unit == trades.TokenType.PT:
            market_state.share_reserves -= float(d_shares)
            market_state.bond_reserves += float(d_bonds)
        else:
            raise AssertionError(
                "pricing_models.calc_out_given_in: ERROR: "
                f"Expected in_.unit to be {trades.TokenType.BASE} or {trades.TokenType.PT}, not {in_.unit}!"
            )

        # Trade the bonds that haven't matured on the YieldSpace curve.
        curve = super().calc_out_given_in(
            in_=trades.Quantity(amount=float(in_amount * normalized_time), unit=in_.unit),
            market_state=market_state,
            time_remaining=time_utils.StretchedTime(  # time remaining is always fixed to the full term for flat+curve
                days=time_remaining.normalizing_constant,  # position duration is the normalizing constant
                time_stretch=time_remaining.time_stretch,
                normalizing_constant=time_remaining.normalizing_constant,
            ),
        )

        # Compute flat part with fee
        flat_without_fee = in_amount * (1 - normalized_time)
        redemption_fee = flat_without_fee * Decimal(market_state.redemption_fee_percent)
        flat_with_fee = flat_without_fee - redemption_fee

        # Compute the user's trade result including both the flat and the curve parts of the trade.
        if in_.unit == trades.TokenType.BASE:
            user_result = AgentTradeResult(
                d_base=-in_.amount,
                d_bonds=float(flat_with_fee + Decimal(curve.user_result.d_bonds)),
            )
            market_result = hyperdrive.MarketTradeResult(
                d_base=in_.amount,
                d_bonds=curve.market_result.d_bonds,
            )
        elif in_.unit == trades.TokenType.PT:
            user_result = AgentTradeResult(
                d_base=float(flat_with_fee + Decimal(curve.user_result.d_base)),
                d_bonds=-in_.amount,
            )
            market_result = hyperdrive.MarketTradeResult(
                d_base=float(-flat_with_fee + Decimal(curve.market_result.d_base)),
                d_bonds=curve.market_result.d_bonds,
            )
        else:
            raise AssertionError(
                "pricing_models.calc_out_given_in: ERROR: "
                f"Expected in_.unit to be {trades.TokenType.BASE} or {trades.TokenType.PT}, not {in_.unit}!"
            )

        return trades.TradeResult(
            user_result=user_result,
            market_result=market_result,
            breakdown=trades.TradeBreakdown(
                without_fee_or_slippage=float(flat_without_fee + Decimal(curve.breakdown.without_fee_or_slippage)),
                without_fee=float(flat_without_fee + Decimal(curve.breakdown.without_fee)),
                fee=float(Decimal(curve.breakdown.fee) + redemption_fee),
                with_fee=float(flat_with_fee + Decimal(curve.breakdown.with_fee)),
            ),
        )

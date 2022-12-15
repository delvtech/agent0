"""The Hyperdrive pricing model."""

import copy

from elfpy.pricing_models.yieldspace import YieldSpacePricingModel
from elfpy.types import (
    Quantity,
    MarketState,
    StretchedTime,
    TradeBreakdown,
    TradeResult,
    UserTradeResult,
)


class HyperdrivePricingModel(YieldSpacePricingModel):
    """
    Hyperdrive Pricing Model

    This pricing model uses a combination of a constant sum invariant and a
    YieldSpace invariant with modifications to enable the base reserves to be
    deposited into yield bearing vaults
    """

    # pylint: disable=line-too-long

    def model_name(self) -> str:
        return "Hyperdrive"

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
            c (\frac{1}{\mu} (\frac{k - (2y + cz - \Delta y \cdot t)^{1-t}}{\frac{c}{\mu}})^{\frac{1}{1-t}} - z) + \Delta y \cdot (1 - t),
            &\text{ if } token\_in = \text{"base"} \\
            (k - \frac{c}{\mu} (\mu * (z - \Delta z \cdot t))^{1 - t})^{\frac{1}{1 - t}} - (2y + cz) + c \cdot \Delta z \cdot (1 - t),
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

        # TODO: Verify that this is needed.
        market_state = copy.copy(market_state)

        # TODO: This is somewhat strange since these updates never actually hit
        #       the reserves.
        #
        # Redeem the matured bonds 1:1 and simulate these updates hitting the
        # reserves.
        if out.unit == "base":
            market_state.share_reserves -= out.amount * (1 - time_remaining.stretched_time) / market_state.share_price
            market_state.bond_reserves += out.amount * (1 - time_remaining.stretched_time)
        elif out.unit == "pt":
            market_state.share_reserves += out.amount * (1 - time_remaining.stretched_time) / market_state.share_price
            market_state.bond_reserves -= out.amount * (1 - time_remaining.stretched_time)
        else:
            raise AssertionError(
                f'pricing_models.calc_in_given_out: ERROR: expected out.unit to be "base" or "pt", not {out.unit}!'
            )

        # Trade the bonds that haven't matured on the YieldSpace curve.
        curve = super().calc_in_given_out(
            out=Quantity(amount=out.amount * time_remaining.stretched_time, unit=out.unit),
            market_state=market_state,
            fee_percent=fee_percent,
            time_remaining=StretchedTime(days=365, time_stretch=time_remaining.time_stretch),
        )

        # Compute the user's trade result including both the flat and the curve
        # parts of the trade.
        flat = out.amount * (1 - time_remaining.stretched_time)
        if out.unit == "base":
            user_result = UserTradeResult(
                d_base=out.amount,
                d_bonds=-flat + curve.user_result.d_bonds,
            )
        elif out.unit == "pt":
            user_result = UserTradeResult(
                d_base=-flat + curve.user_result.d_base,
                d_bonds=out.amount,
            )
        else:
            raise AssertionError(
                f'pricing_models.calc_in_given_out: ERROR: expected in_.unit to be "base" or "pt", not {out.unit}!'
            )

        return TradeResult(
            user_result=user_result,
            market_result=curve.market_result,
            breakdown=TradeBreakdown(
                without_fee_or_slippage=flat + curve.breakdown.without_fee_or_slippage,
                without_fee=flat + curve.breakdown.without_fee,
                fee=curve.breakdown.fee,
                with_fee=flat + curve.breakdown.with_fee,
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
            c (z - \frac{1}{\mu} (\frac{k - (2y + cz + \Delta y \cdot t)^{1 - t}}{\frac{c}{\mu}})^{\frac{1}{1 - t}}) + \Delta y \cdot (1 - t),
            &\text{ if } token\_out = \text{"base"} \\
            2y + cz - (k - \frac{c}{\mu} (\mu (z + \Delta z \cdot t))^{1 - t})^{\frac{1}{1 - t}} + c \cdot \Delta z \cdot (1 - t),
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
        TradeResult
            The result of performing the trade.
        """

        # TODO: Verify that this is needed.
        market_state = copy.copy(market_state)

        # TODO: This is somewhat strange since these updates never actually hit
        #       the reserves.
        #
        # Redeem the matured bonds 1:1 and simulate these updates hitting the
        # reserves.
        if in_.unit == "base":
            market_state.share_reserves += (in_.amount * (1 - time_remaining.stretched_time)) / market_state.share_price
            market_state.bond_reserves -= in_.amount * (1 - time_remaining.stretched_time)
        elif in_.unit == "pt":
            market_state.share_reserves -= (in_.amount * (1 - time_remaining.stretched_time)) / market_state.share_price
            market_state.bond_reserves += in_.amount * (1 - time_remaining.stretched_time)
        else:
            raise AssertionError(
                f'pricing_models.calc_out_given_in: ERROR: expected token_out to be "base" or "pt", not {in_.unit}!'
            )

        # Trade the bonds that haven't matured on the YieldSpace curve.
        curve = super().calc_out_given_in(
            in_=Quantity(amount=in_.amount * time_remaining.stretched_time, unit=in_.unit),
            market_state=market_state,
            fee_percent=fee_percent,
            time_remaining=StretchedTime(days=365, time_stretch=time_remaining.time_stretch),
        )

        # Compute the user's trade result including both the flat and the curve
        # parts of the trade.
        flat = in_.amount * (1 - time_remaining.stretched_time)
        if in_.unit == "base":
            user_result = UserTradeResult(
                d_base=-in_.amount,
                d_bonds=flat + curve.user_result.d_bonds,
            )
        elif in_.unit == "pt":
            user_result = UserTradeResult(
                d_base=flat + curve.user_result.d_base,
                d_bonds=-in_.amount,
            )
        else:
            raise AssertionError(
                f'pricing_models.calc_out_given_in: ERROR: expected in_.unit to be "base" or "pt", not {in_.unit}!'
            )

        return TradeResult(
            user_result=user_result,
            market_result=curve.market_result,
            breakdown=TradeBreakdown(
                without_fee_or_slippage=flat + curve.breakdown.without_fee_or_slippage,
                without_fee=flat + curve.breakdown.without_fee,
                fee=curve.breakdown.fee,
                with_fee=flat + curve.breakdown.with_fee,
            ),
        )

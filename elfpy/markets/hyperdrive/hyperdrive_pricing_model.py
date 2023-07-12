"""The Hyperdrive pricing model"""
from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from fixedpointmath import FixedPoint

import elfpy.agents.agent_trade_result as agent_trade_result
import elfpy.markets.hyperdrive.market_action_result as market_action_result
import elfpy.markets.trades as trades
import elfpy.time as time
import elfpy.types as types

from .yieldspace_pricing_model import YieldspacePricingModel

if TYPE_CHECKING:
    from .hyperdrive_market import HyperdriveMarketState


class HyperdrivePricingModel(YieldspacePricingModel):
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

    def get_max_long(
        self,
        market_state: HyperdriveMarketState,
        time_remaining: time.StretchedTime,
    ) -> tuple[FixedPoint, FixedPoint]:
        r"""
        Calculates the maximum long the market can support

        .. math::
            \Delta z' = \mu^{-1} \cdot (\frac{\mu}{c} \cdot (k-(y+c \cdot z)^{1-\tau(d)}))^{\frac{1}{1-\tau(d)}}
            -c \cdot z

        Arguments
        ----------
        market_state : MarketState
            The reserves and share prices of the pool
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch)

        Returns
        -------
        FixedPoint
            The maximum amount of base that can be used to purchase bonds.
        FixedPoint
            The maximum amount of bonds that can be purchased.
        """
        # TODO: This shuld never be less than zero, but sometimes is. Need to investigate.
        out_amount = market_state.bond_reserves - market_state.bond_buffer
        if out_amount <= FixedPoint(0):
            return FixedPoint(0), FixedPoint(0)
        base = self.calc_in_given_out(
            out=types.Quantity(amount=out_amount, unit=types.TokenType.PT),
            market_state=market_state,
            time_remaining=time_remaining,
        ).breakdown.with_fee
        bonds = self.calc_out_given_in(
            in_=types.Quantity(amount=base, unit=types.TokenType.BASE),
            market_state=market_state,
            time_remaining=time_remaining,
        ).breakdown.with_fee
        return base, bonds

    def get_max_short(
        self,
        market_state: HyperdriveMarketState,
        time_remaining: time.StretchedTime,
    ) -> tuple[FixedPoint, FixedPoint]:
        r"""
        Calculates the maximum short the market can support using the bisection
        method.

        .. math::
            \Delta y' = \mu^{-1} \cdot (\frac{\mu}{c} \cdot k)^{\frac{1}{1-\tau(d)}}-2y-c \cdot z

        Arguments
        ----------
        market_state : MarketState
            The reserves and share prices of the pool.
        time_remaining : StretchedTime
            The time remaining for the asset (incorporates time stretch).

        Returns
        -------
        FixedPoint
            The maximum amount of base that can be used to short bonds.
        FixedPoint
            The maximum amount of bonds that can be shorted.
        """
        # TODO: This shuld never be less than zero, but sometimes is. Need to investigate.
        out_amount = market_state.share_reserves - market_state.base_buffer / market_state.share_price
        if out_amount <= FixedPoint(0):
            return FixedPoint(0), FixedPoint(0)
        bonds = self.calc_in_given_out(
            out=types.Quantity(amount=out_amount, unit=types.TokenType.PT),
            market_state=market_state,
            time_remaining=time_remaining,
        ).breakdown.with_fee
        base = self.calc_out_given_in(
            in_=types.Quantity(amount=bonds, unit=types.TokenType.PT),
            market_state=market_state,
            time_remaining=time_remaining,
        ).breakdown.with_fee
        return base, bonds

    def calc_in_given_out(
        self,
        out: types.Quantity,
        market_state: HyperdriveMarketState,
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

        Arguments
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
        if out.amount < FixedPoint(0):
            raise ValueError(f"{out.amount=} must be greater than or equal to zero.")
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
            out=types.Quantity(amount=out.amount * time_remaining.normalized_time, unit=out.unit),
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
                d_bonds=-flat_with_fee + curve.user_result.d_bonds,
            )
            market_result = market_action_result.MarketActionResult(
                d_base=-out.amount,
                d_bonds=curve.market_result.d_bonds,
            )
        elif out.unit == types.TokenType.PT:
            user_result = agent_trade_result.AgentTradeResult(
                d_base=-flat_with_fee + curve.user_result.d_base,
                d_bonds=out.amount,
            )
            market_result = market_action_result.MarketActionResult(
                d_base=flat_with_fee + curve.market_result.d_base,
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
        in_: types.Quantity,
        market_state: HyperdriveMarketState,
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

        Arguments
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
        if in_.amount < FixedPoint(0):
            raise ValueError(f"{in_.amount=} must be greater than or equal to zero.")
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
            in_=types.Quantity(amount=in_.amount * time_remaining.normalized_time, unit=in_.unit),
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
                d_bonds=flat_with_fee + curve.user_result.d_bonds,
            )
            market_result = market_action_result.MarketActionResult(
                d_base=in_.amount,
                d_bonds=curve.market_result.d_bonds,
            )
        elif in_.unit == types.TokenType.PT:
            user_result = agent_trade_result.AgentTradeResult(
                d_base=flat_with_fee + curve.user_result.d_base,
                d_bonds=-in_.amount,
            )
            market_result = market_action_result.MarketActionResult(
                d_base=-flat_with_fee + curve.market_result.d_base,
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
        self, lp_in: FixedPoint, market_state: HyperdriveMarketState
    ) -> tuple[FixedPoint, FixedPoint]:
        """
        Calculates the amount of base shares and bonds released from burning a specified amount of
        LP shares from the pool.

        Arguments
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


# Let the variable names be the same as their solidity counterpart so that it is easier to compare
# the two.  We can make python wrappers that just call these methods that have better variable names
# that conform to python standards.
# pylint: disable=invalid-name


class MaxLongResult(NamedTuple):
    """Result from calculate_max_long."""

    base_amount: FixedPoint
    bond_amount: FixedPoint


# mimic variable from solidity.
ONE_18 = FixedPoint("1.0")


def calculate_max_long(
    share_reserves: FixedPoint,
    bond_reserves: FixedPoint,
    longs_outstanding: FixedPoint,
    time_stretch: FixedPoint,
    share_price: FixedPoint,
    initial_share_price: FixedPoint,
    max_iterations: int,
) -> MaxLongResult:
    """Calculates the maximum amount of bonds that can be bought in the market.  This is necessarily
    done with an iterative approach as there is no closed form solution.

    Arguments
    ----------
    share_reserves : FixedPoint
        The pool's share reserves.
    bond_reserves : FixedPoint
        The pool's bond reserves.
    longs_outstanding : FixedPoint
        The amount of longs outstanding.
    time_stretch : FixedPoint
        The time stretch parameter.
    share_price : FixedPoint
        The current share price.
    initial_share_price : FixedPoint
        The initial share price.
    max_iterations : int
        The maximum number of iterations to perform before returning the result.

    Returns
    -------
    MaxLongResult
        The maximum amount of bonds that can be purchased and the amount of base that must be spent to purchase them.

    """
    # We first solve for the maximum buy that is possible on the YieldSpace curve. This will give us
    # an upper bound on our maximum buy by giving us the maximum buy that is possible without going
    # into negative interest territory. Hyperdrive has solvency requirements since it mints longs on
    # demand. If the maximum buy satisfies our solvency checks, then we're done. If not, then we
    # need to solve for the maximum trade size iteratively.
    dz, dy = calculate_max_buy(share_reserves, bond_reserves, ONE_18 - time_stretch, share_price, initial_share_price)
    if share_reserves + dz >= (longs_outstanding + dy) / share_price:
        return MaxLongResult(base_amount=dz * share_price, bond_amount=dy)

    # To make an initial guess for the iterative approximation, we consider
    # the solvency check to be the error that we want to reduce. The amount
    # the long buffer exceeds the share reserves is given by
    # (y_l + dy) / c - (z + dz). Since the error could be large, we'll use
    # the realized price of the trade instead of the spot price to
    # approximate the change in trade output. This gives us dy = c * 1/p * dz.
    # Substituting this into error equation and setting the error equal to
    # zero allows us to solve for the initial guess as:
    #
    # (y_l + c * 1/p * dz) / c - (z + dz) = 0
    #              =>
    # (1/p - 1) * dz = z - y_l/c
    #              =>
    # dz = (z - y_l/c) * (p / (p - 1))
    p = share_price * dz / dy
    dz = (share_reserves - longs_outstanding / share_price) * p / (ONE_18 - p)
    dy = calculate_bonds_out_given_shares_in(
        share_reserves, bond_reserves, dz, ONE_18 - time_stretch, share_price, initial_share_price
    )

    result = MaxLongResult(base_amount=FixedPoint(), bond_amount=FixedPoint())

    # Our maximum long will be the largest trade size that doesn't fail
    # the solvency check.
    for _ in range(max_iterations):
        # Even though YieldSpace isn't linear, we can use a linear approximation
        # to get closer to the optimal solution. Our guess should bring us close
        # enough to the optimal point that we can linearly approximate the
        # change in error using the current spot price.
        #
        # We can approximate the change in the trade output with respect to
        # trade size as dy' = c * (1/p) * dz'. Substituting this into our error
        # equation and setting the error equation equal to zero allows us to
        # solve for the trade size update:
        #
        # (y_l + dy + c * (1/p) * dz') / c - (z + dz + dz') = 0
        #                  =>
        # (1/p - 1) * dz' = (z + dz) - (y_l + dy) / c
        #                  =>
        # dz' = ((z + dz) - (y_l + dy) / c) * (p / (p - 1)).
        p = calculate_spot_price(share_reserves + dz, bond_reserves - dy, initial_share_price, time_stretch)
        error = int((share_reserves + dz) - (longs_outstanding + dy) / share_price)
        if error > 0 and dz * share_price > result.base_amount:
            result = MaxLongResult(base_amount=dz * share_price, bond_amount=dy)
        if p >= ONE_18:
            break
        if error < 0:
            dz -= -error * p / (ONE_18 - p)
        else:
            dz += error * p / (ONE_18 - p)
        dy = calculate_bonds_out_given_shares_in(
            share_reserves, bond_reserves, dz, ONE_18 - time_stretch, share_price, initial_share_price
        )

    return result


def calculate_max_buy(
    z: FixedPoint, y: FixedPoint, t: FixedPoint, c: FixedPoint, mu: FixedPoint
) -> tuple[FixedPoint, FixedPoint]:
    r"""
    Calculates the maximum amount of bonds that can be purchased with the specified reserves.

    Parameters
    ----------
    z : FixedPoint
        Amount of share reserves in the pool.
    y : FixedPoint
        Amount of bond reserves in the pool.
    t : FixedPoint
        Amount of time elapsed since term start.
    c : FixedPoint
        Conversion rate between base and shares.
    mu : FixedPoint
        Interest normalization factor for shares.

    Returns
    -------
    tuple[FixedPoint, FixedPoint]
        The cost in shares of the maximum bond purchase and the maximum amount of bonds that can be purchased.
    """
    # calculate c_div_mu by directly using regular division operator
    c_div_mu = c / mu
    k = modified_yield_space_constant(c_div_mu, mu, z, t, y)
    # calculate optimal_y and optimal_z using regular division and pow operator
    optimal_y = (k / (c_div_mu + ONE_18)) ** (ONE_18 / t)
    optimal_z = optimal_y / mu

    # calculate and return the optimal trade sizes by using regular subtraction operator
    return (optimal_z - z, y - optimal_y)


def modified_yield_space_constant(
    c_div_mu: FixedPoint, mu: FixedPoint, z: FixedPoint, t: FixedPoint, y: FixedPoint
) -> FixedPoint:
    r"""
    Helper function to derive invariant constant C for the YieldSpace.

    Parameters
    ----------
    c_div_mu : FixedPoint
        Normalized price of shares in terms of base.
    mu : FixedPoint
        Interest normalization factor for shares.
    z : FixedPoint
        Amount of share reserves in the pool.
    t : FixedPoint
        Amount of time elapsed since term start.
    y : FixedPoint
        Amount of bond reserves in the pool.

    Returns
    -------
    FixedPoint
        The modified YieldSpace constant C.
    """
    # calculate and return the modified YieldSpace constant using regular arithmetic operators
    return c_div_mu * (mu * z) ** t + y**t


def calculate_bonds_out_given_shares_in(
    z: FixedPoint, y: FixedPoint, dz: FixedPoint, t: FixedPoint, c: FixedPoint, mu: FixedPoint
) -> FixedPoint:
    r"""
    Calculates the amount of bonds a user will receive from the pool by providing a specified amount of shares.

    Parameters
    ----------
    z : FixedPoint
        Amount of share reserves in the pool.
    y : FixedPoint
        Amount of bond reserves in the pool.
    dz : FixedPoint
        Amount of shares user wants to provide.
    t : FixedPoint
        Amount of time elapsed since term start.
    c : FixedPoint
        Conversion rate between base and shares.
    mu : FixedPoint
        Interest normalization factor for shares.

    Returns
    -------
    FixedPoint
        The amount of bonds the user will receive.
    """
    c_div_mu = c / mu
    k = modified_yield_space_constant(c_div_mu, mu, z, t, y)
    z = (mu * (z + dz)) ** t
    z = c_div_mu * z
    _y = (k - z) ** (ONE_18.div_up(t))
    return y - _y


def calculate_spot_price(
    share_reserves: FixedPoint, bond_reserves: FixedPoint, initial_share_price: FixedPoint, time_stretch: FixedPoint
) -> FixedPoint:
    r"""
    Calculates the spot price without slippage of bonds in terms of base.

    Parameters
    ----------
    share_reserves : FixedPoint
        The pool's share reserves.
    bond_reserves : FixedPoint
        The pool's bond reserves.
    initial_share_price : FixedPoint
        The initial share price as an 18 fixed-point value.
    time_stretch : FixedPoint
        The time stretch parameter as an 18 fixed-point value.

    Returns
    -------
    FixedPoint
        The spot price of bonds in terms of base as an 18 fixed-point value.
    """
    spot_price = (initial_share_price * share_reserves / bond_reserves) ** time_stretch
    return spot_price


def calculate_max_short(
    share_reserves: FixedPoint,
    bond_reserves: FixedPoint,
    longs_outstanding: FixedPoint,
    time_stretch: FixedPoint,
    share_price: FixedPoint,
    initial_share_price: FixedPoint,
) -> FixedPoint:
    r"""
    Calculates the maximum amount of shares that can be used to open shorts.

    Parameters
    ----------
    share_reserves : FixedPoint
        The pool's share reserves.
    bond_reserves : FixedPoint
        The pool's bonds reserves.
    longs_outstanding : FixedPoint
        The amount of longs outstanding.
    time_stretch : FixedPoint
        The time stretch parameter.
    share_price : FixedPoint
        The share price.
    initial_share_price : FixedPoint
        The initial share price.

    Returns
    -------
    FixedPoint
        The maximum amount of shares that can be used to open shorts.
    """
    t = ONE_18 - time_stretch
    price_factor = share_price / initial_share_price
    k = modified_yield_space_constant(price_factor, initial_share_price, share_reserves, t, bond_reserves)
    optimal_bond_reserves = (k - price_factor * ((longs_outstanding / share_price) ** t)) ** (ONE_18 / t)

    # The optimal bond reserves imply a maximum short of dy = y - y0.
    return optimal_bond_reserves - bond_reserves

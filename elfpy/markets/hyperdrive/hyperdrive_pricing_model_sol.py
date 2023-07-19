"""The Hyperdrive pricing model"""
from __future__ import annotations

from typing import NamedTuple

from fixedpointmath import FixedPoint

from elfpy.markets.hyperdrive import yieldspace_pricing_model_sol

# Let the variable names be the same as their solidity counterpart so that it is easier to compare
# the two.  We can make python wrappers that just call these methods that have better variable names
# that conform to python standards.
# pylint: disable=invalid-name
# pylint: disable=too-many-arguments

ONE_18 = FixedPoint("1")


class MaxLongResult(NamedTuple):
    """Result from calculate_max_long."""

    base_amount: FixedPoint
    bond_amount: FixedPoint


def calculate_spot_price(
    share_reserves: FixedPoint, bond_reserves: FixedPoint, initial_share_price: FixedPoint, time_stretch: FixedPoint
) -> FixedPoint:
    r"""
    Calculates the spot price without slippage of bonds in terms of base.
    This is meant to mirror the solidity.

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


def calculate_max_long(
    share_reserves: FixedPoint,
    bond_reserves: FixedPoint,
    longs_outstanding: FixedPoint,
    time_stretch: FixedPoint,
    share_price: FixedPoint,
    initial_share_price: FixedPoint,
    minimum_share_reserves: FixedPoint,
    max_iterations: int = 20,
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
        The maximum amount of bonds that can be purchased and the amount of base that must be spent
        to purchase them.

    """
    # We first solve for the maximum buy that is possible on the YieldSpace curve. This will give us
    # an upper bound on our maximum buy by giving us the maximum buy that is possible without going
    # into negative interest territory. Hyperdrive has solvency requirements since it mints longs on
    # demand. If the maximum buy satisfies our solvency checks, then we're done. If not, then we
    # need to solve for the maximum trade size iteratively.
    time_remaining = FixedPoint(1)
    time_elapsed = ONE_18 - time_remaining * time_stretch
    dz, dy = yieldspace_pricing_model_sol.calculate_max_buy(
        share_reserves, bond_reserves, time_elapsed, share_price, initial_share_price
    )
    if share_reserves + dz >= (longs_outstanding + dy) / share_price + minimum_share_reserves:
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
    dz = (share_reserves - longs_outstanding / share_price - minimum_share_reserves) * p / (ONE_18 - p)
    dy = yieldspace_pricing_model_sol.calculate_bonds_out_given_shares_in(
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
        approximation_error = (share_reserves + dz) - (longs_outstanding + dy) / share_price - minimum_share_reserves

        if approximation_error > 0 and dz * share_price > result.base_amount:
            result = MaxLongResult(base_amount=dz * share_price, bond_amount=dy)

        p = calculate_spot_price(share_reserves + dz, bond_reserves - dy, initial_share_price, time_stretch)
        if p >= ONE_18:
            break
        if approximation_error < 0:
            delta = -approximation_error * p / (ONE_18 - p)
            if dz > delta:
                dz -= delta
            else:
                dz = FixedPoint(0)
        else:
            dz += approximation_error * p / (ONE_18 - p)
        new_dy = yieldspace_pricing_model_sol.calculate_bonds_out_given_shares_in(
            share_reserves, bond_reserves, dz, ONE_18 - time_stretch, share_price, initial_share_price
        )
        if bond_reserves - new_dy <= FixedPoint(0):
            break
        dy = new_dy

    return result


def calculate_max_short(
    share_reserves: FixedPoint,
    bond_reserves: FixedPoint,
    longs_outstanding: FixedPoint,
    time_stretch: FixedPoint,
    share_price: FixedPoint,
    initial_share_price: FixedPoint,
    minimum_share_reserves: FixedPoint,
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
    k = yieldspace_pricing_model_sol.modified_yield_space_constant(
        price_factor, initial_share_price, share_reserves, t, bond_reserves
    )
    inner_factor = initial_share_price * longs_outstanding / share_price + minimum_share_reserves**t
    optimal_bond_reserves = (k - price_factor * inner_factor) ** (ONE_18 / t)

    # The optimal bond reserves imply a maximum short of dy = y - y0.
    return optimal_bond_reserves - bond_reserves

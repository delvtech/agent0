"""The Hyperdrive pricing model"""
from __future__ import annotations

from fixedpointmath import FixedPoint

# Let the variable names be the same as their solidity counterpart so that it is easier to compare
# the two.  We can make python wrappers that just call these methods that have better variable names
# that conform to python standards.
# pylint: disable=invalid-name
# pylint: disable=too-many-arguments

ONE_18 = FixedPoint("1")


def modified_yield_space_constant(
    c_div_mu: FixedPoint, mu: FixedPoint, z: FixedPoint, t: FixedPoint, y: FixedPoint
) -> FixedPoint:
    r"""
    Helper function to derive invariant constant C for the YieldSpace.
    This is meant to mirror the solidity.

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
    This is meant to mirror the solidity.

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

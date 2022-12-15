"""
Utilities for price
"""

# Currently many functions use >5 arguments.
# These should be packaged up into shared variables, e.g.
#     reserves = (in_reserves, out_reserves)
#     share_prices = (init_share_price, share_price)
# pylint: disable=too-many-arguments

from . import time as time_utils

### Reserves ###
def calc_base_asset_reserves(
    apr,
    token_asset_reserves,
    days_remaining,
    time_stretch,
    init_share_price,
    share_price,
):
    """
    Returns the assumed base_asset reserve amounts given the token_asset reserves and APR

    Arguments
    ---------
    apr_decimal : float
        Current fixed APR in decimal units (for example, 5% APR would be 0.05)
    token_asset_reserves : float
        Bond (pt) reserves in the pool
    days_remaining : float
        Amount of days left until bond maturity
    time_stretch : float
        Time stretch parameter, in years
    init_share_price : float
        Original share price when the pool started
    share_price : float
        Current share price

    Returns
    -------
    float
        The expected amount of base asset in the pool, calculated from the provided parameters
    """
    normalized_days_remaining = time_utils.norm_days(days_remaining)
    time_stretch_exp = 1 / time_utils.stretch_time(normalized_days_remaining, time_stretch)
    numerator = 2 * share_price * token_asset_reserves  # 2*c*y
    scaled_apr_decimal = apr * normalized_days_remaining + 1  # assuming price_apr = 1/(1+r*t)
    denominator = init_share_price * scaled_apr_decimal**time_stretch_exp - share_price
    result = numerator / denominator  # 2*c*y/(u*(r*t + 1)**(1/T) - c)
    return result


### Spot Price and APR ###


def calc_apr_from_spot_price(price, normalized_days_remaining):
    """
    Returns the APR (decimal) given the current (positive) base asset price and the remaining pool duration

    Arguments
    ---------
    price : float
        Spot price of bonds in terms of base
    normalized_days_remaining : float
        Time remaining until bond maturity, in yearfracs

    Returns
    -------
    float
        APR (decimal) calculated from the provided parameters
    """
    assert price > 0, (
        "utils.price.calc_apr_from_spot_price: ERROR: "
        f"Price argument should be greater or equal to zero, not {price}"
    )
    assert normalized_days_remaining > 0, (
        "utils.price.calc_apr_from_spot_price: ERROR: "
        f"normalized_days_remaining argument should be greater than zero, not {normalized_days_remaining}"
    )
    return (1 - price) / price / normalized_days_remaining  # price = 1 / (1 + r * t)


def calc_spot_price_from_apr(apr_decimal, normalized_days_remaining):
    """
    Returns the current spot price based on the current APR (decimal) and the remaining pool duration

    Arguments
    ---------
    apr_decimal : float
        Current fixed APR in decimal units (for example, 5% APR would be 0.05)
    normalized_days_remaining : float
        Time remaining until bond maturity, in yearfracs

    Returns
    -------
    float
        Spot price of bonds in terms of base, calculated from the provided parameters
    """
    return 1 / (1 + apr_decimal * normalized_days_remaining)  # price = 1 / (1 + r * t)


### YieldSpace ###


def calc_k_const(share_reserves, bond_reserves, share_price, init_share_price, time_elapsed):
    """
    Returns the 'k' constant variable for trade mathematics

    Arguments
    ---------
    share_reserves : float
    bond_reserves : float
    share_price : float
        Current share price
    init_share_price : float
        Original share price when the pool started
    time_elapsed : float
        Amount of time that has elapsed in the current market, in yearfracs

    Returns
    -------
    float
        'k' constant used for trade mathematics, calculated from the provided parameters
    """
    scale = share_price / init_share_price
    total_reserves = bond_reserves + share_price * share_reserves
    return scale * (init_share_price * share_reserves) ** (time_elapsed) + (bond_reserves + total_reserves) ** (
        time_elapsed
    )

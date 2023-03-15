"""Utilities for price calculations"""
from __future__ import annotations  # types will be strings by default in 3.11

import elfpy.time as time
from decimal import Decimal


### Spot Price and APR ###
def calc_apr_from_spot_price(price: Decimal, time_remaining: time.StretchedTime):
    r"""
    Returns the APR (decimal) given the current (positive) base asset price and the remaining pool duration

    Parameters
    ----------
    price : Decimal
        Spot price of bonds in terms of base
    time_remaining : StretchedTime
        Time remaining until bond maturity, in years

    Returns
    -------
    Decimal
        APR (decimal) calculated from the provided parameters
    """
    assert price > 0, (
        "utils.price.calc_apr_from_spot_price: ERROR: "
        f"Price argument should be greater or equal to zero, not {price}"
    )
    assert time_remaining.normalized_time > 0, (
        "utils.price.calc_apr_from_spot_price: ERROR: "
        f"time_remaining.normalized_time should be greater than zero, not {time_remaining.normalized_time}"
    )
    annualized_time = time.norm_days(time_remaining.days, Decimal(365))
    return (1 - price) / (price * annualized_time)  # r = ((1/p)-1)/t = (1-p)/(pt)


def calc_spot_price_from_apr(apr: float, time_remaining: time.StretchedTime):
    r"""Returns the current spot price based on the current APR (decimal) and the remaining pool duration

    Parameters
    ----------
    apr : float
        Current fixed APR in decimal units (for example, 5% APR would be 0.05)
    time_remaining : StretchedTime
        Time remaining until bond maturity

    Returns
    -------
    float
        Spot price of bonds in terms of base, calculated from the provided parameters
    """
    annualized_time = time.norm_days(time_remaining.days, 365)
    return 1 / (1 + apr * annualized_time)  # price = 1 / (1 + r * t)

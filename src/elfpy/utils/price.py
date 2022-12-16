"""
Utilities for price
"""

# Currently many functions use >5 arguments.
# These should be packaged up into shared variables, e.g.
#     reserves = (in_reserves, out_reserves)
#     share_prices = (init_share_price, share_price)
# pylint: disable=too-many-arguments

from elfpy.types import MarketState, StretchedTime

### Reserves ###


def calc_total_liquidity_from_reserves_and_price(base_asset_reserves, token_asset_reserves, spot_price):
    """
    Returns the total liquidity in the pool in terms of base

    We are using spot_price when calculating total_liquidity to convert the two tokens into the same units.
    Otherwise we're comparing apples(base_asset_reserves in ETH) and oranges (token_asset_reserves in ptETH)
        ptEth = 1.0 ETH at maturity ONLY
        ptEth = 0.95 ETH ahead of time
    Discount factor from the time value of money
        Present Value = Future Value / (1 + r)^n
        Future Value = Present Value * (1 + r)^n
    The equation converts from future value to present value at the appropriate discount rate,
    which measures the opportunity cost of getting a dollar tomorrow instead of today.
    discount rate = (1 + r)^n
    spot price APR = 1 / (1 + r)^n

    Arguments
    ---------
    base_asset_reserves : float
        Base reserves in the pool
    token_asset_reserves : float
        Bond (pt) reserves in the pool
    spot_price : float
        Price of bonds (pts) in terms of base

    Returns
    -------
    float
        Total liquidity in the pool in terms of base, calculated from the provided parameters
    """
    return base_asset_reserves + token_asset_reserves * spot_price


def calc_base_asset_reserves(
    apr: float,
    token_asset_reserves: float,
    time_remaining: StretchedTime,
    init_share_price: float,
    share_price: float,
):
    """
    Returns the assumed base_asset reserve amounts given the token_asset reserves and APR

    Arguments
    ---------
    apr : float
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
    numerator = 2 * share_price * token_asset_reserves  # 2*c*y
    denominator = (
        init_share_price * (1 + apr * time_remaining.normalized_time) ** (1 / time_remaining.stretched_time)
        - share_price
    )
    result = numerator / denominator  # 2*c*y/(u*(r*t + 1)**(1/T) - c)
    return result


# TODO: This is a property of pricing models since it relies on a pricing
#       model's definition of price.
#
# TODO: Add verbose comments.
def calc_bond_reserves(
    apr: float,
    share_reserves: float,
    time_remaining: StretchedTime,
    init_share_price: float,
    share_price: float,
) -> float:
    return (share_reserves / 2) * (
        init_share_price * (1 + apr * time_remaining.normalized_time) ** (1 / time_remaining.stretched_time)
        - share_price
    )


def calc_liquidity(
    target_liquidity: float,
    market_price: float,
    apr: float,
    time_remaining: StretchedTime,
    init_share_price: float = 1,
    share_price: float = 1,
):
    """
    Returns the reserve volumes and total supply

    The scaling factor ensures token_asset_reserves and base_asset_reserves add
    up to target_liquidity, while keeping their ratio constant (preserves apr).

    total_liquidity = in base terms, used to target liquidity as passed in
    total_reserves  = in arbitrary units (AU), used for yieldspace math

    Arguments
    ---------
    target_liquidity_usd : float
        Amount of liquidity, denominated in USD, that the simulation is trying to achieve in a given market
    market_price : float
        Price of the base asset, denominated in USD
    apr : float
        Fixed APR that the bonds should provide, in decimal form (for example, 5% APR is 0.05)
    time_remaining : Stretched
        Amount of time left until bond maturity
    init_share_price : float
        Original share price when the pool started. Defaults to 1
    share_price : float
        Current share price. Defaults to 1

    Returns
    -------
    (float, float, float)
        Tuple that contains (base_asset_reserves, token_asset_reserves, total_liquidity)
        calculated from the provided parameters
    """
    # estimate reserve values with the information we have
    spot_price = calc_spot_price_from_apr(apr, time_remaining)
    token_asset_reserves = target_liquidity / 2 / spot_price  # guesstimate, in base units still
    base_asset_reserves = calc_base_asset_reserves(
        apr,
        token_asset_reserves,
        time_remaining,
        init_share_price,
        share_price,
    )  # ensures an accurate ratio of prices
    total_liquidity = calc_total_liquidity_from_reserves_and_price(
        base_asset_reserves, token_asset_reserves, spot_price
    )  # in base asset units
    # compute scaling factor to adjust reserves so that they match the target liquidity
    scaling_factor = (target_liquidity / market_price) / total_liquidity  # both in token units
    # update variables by rescaling the original estimates
    token_asset_reserves = token_asset_reserves * scaling_factor
    base_asset_reserves = base_asset_reserves * scaling_factor
    total_liquidity = calc_total_liquidity_from_reserves_and_price(
        base_asset_reserves, token_asset_reserves, spot_price
    )
    return (base_asset_reserves, token_asset_reserves, total_liquidity)


### Spot Price and APR ###


def calc_apr_from_spot_price(price: float, time_remaining: StretchedTime):
    """
    Returns the APR (decimal) given the current (positive) base asset price and the remaining pool duration

    Arguments
    ---------
    price : float
        Spot price of bonds in terms of base
    time_remaining : StretchedTime
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
    assert time_remaining.normalized_time > 0, (
        "utils.price.calc_apr_from_spot_price: ERROR: "
        f"time_remaining.normalized_time should be greater than zero, not {time_remaining.normalized_time}"
    )
    return (1 - price) / (price * time_remaining.normalized_time)  # price = 1 / (1 + r * t)


def calc_spot_price_from_apr(apr: float, time_remaining: StretchedTime):
    """
    Returns the current spot price based on the current APR (decimal) and the remaining pool duration

    Arguments
    ---------
    apr : float
        Current fixed APR in decimal units (for example, 5% APR would be 0.05)
    time_remaining : StretchedTime
        Time remaining until bond maturity

    Returns
    -------
    float
        Spot price of bonds in terms of base, calculated from the provided parameters
    """
    return 1 / (1 + apr * time_remaining.normalized_time)  # price = 1 / (1 + r * t)


### YieldSpace ###


# TODO: This should be updated to use StretchedTime.
def calc_k_const(market_state: MarketState, time_elapsed):
    """
    Returns the 'k' constant variable for trade mathematics

    Arguments
    ---------
    market_state : MarketState
        The state of the AMM
    time_elapsed : float
        Amount of time that has elapsed in the current market, in yearfracs

    Returns
    -------
    float
        'k' constant used for trade mathematics, calculated from the provided parameters
    """
    scale = market_state.share_price / market_state.init_share_price
    total_reserves = market_state.bond_reserves + market_state.share_price * market_state.share_reserves
    return scale * (market_state.init_share_price * market_state.share_reserves) ** (time_elapsed) + (
        market_state.bond_reserves + total_reserves
    ) ** (time_elapsed)

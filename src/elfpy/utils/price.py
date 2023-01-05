"""Utilities for price calculations"""


from __future__ import annotations  # types will be strings by default in 3.11
from typing import TYPE_CHECKING

from elfpy.types import MarketState, StretchedTime

if TYPE_CHECKING:
    from elfpy.markets import Market
    from elfpy.pricing_models.base import PricingModel


### Reserves ###


def calc_liquidity(
    target_liquidity: float,
    target_apr: float,
    market: Market,
    pricing_model: PricingModel,
) -> tuple[float, float]:
    """Returns the reserve volumes and total supply

    The scaling factor ensures bond_reserves and share_reserves add
    up to target_liquidity, while keeping their ratio constant (preserves apr).

    total_liquidity = in base terms, used to target liquidity as passed in
    total_reserves  = in arbitrary units (AU), used for yieldspace math

    Arguments
    ---------
    target_liquidity_usd : float
        amount of liquidity that the simulation is trying to achieve in a given market
    target_apr : float
        desired APR for the seeded market
    market : Market
        This function uses:
            market_state.init_share_price : float
                original share price when the pool started. Defaults to 1
            market_state.share_price : float
                current share price. Defaults to 1
            position_duration : StretchedTime
                amount of time left until bond maturity

    Returns
    -------
    (float, float)
        Tuple that contains (share_reserves, bond_reserves)
        calculated from the provided parameters
    """
    share_reserves = target_liquidity / market.market_state.share_price
    bond_reserves = pricing_model.calc_bond_reserves(
        target_apr,
        share_reserves,
        market.position_duration,
        market.market_state.init_share_price,
        market.market_state.share_price,
    )
    price = market.market_state.share_price
    total_liquidity = pricing_model.calc_total_liquidity_from_reserves_and_price(
        MarketState(
            share_reserves=share_reserves,
            bond_reserves=bond_reserves,
            base_buffer=market.market_state.base_buffer,
            bond_buffer=market.market_state.bond_buffer,
            lp_reserves=market.market_state.lp_reserves,
            share_price=market.market_state.share_price,
            init_share_price=market.market_state.init_share_price,
        ),
        price,
    )
    # compute scaling factor to adjust reserves so that they match the target liquidity
    scaling_factor = target_liquidity / total_liquidity  # both in token units
    # update variables by rescaling the original estimates
    bond_reserves = bond_reserves * scaling_factor
    share_reserves = share_reserves * scaling_factor
    return (share_reserves, bond_reserves)


### Spot Price and APR ###


def calc_apr_from_spot_price(price: float, time_remaining: StretchedTime):
    """
    Returns the APR (decimal) given the current (positive) base asset price and the remaining pool duration

    Arguments
    ---------
    price : float
        Spot price of bonds in terms of base
    normalized_time_remaining : StretchedTime
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
    return (1 - price) / (price * time_remaining.normalized_time)  # r = ((1/p)-1)/t = (1-p)/(pt)


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

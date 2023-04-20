"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Literal, Optional

import numpy as np

import elfpy.agents.wallet as wallet
import elfpy.markets.base as base_market
import elfpy.time as time
import elfpy.types as types
from elfpy.utils.math import FixedPoint
from elfpy.utils.math.update_weighted_average import update_weighted_average

if TYPE_CHECKING:
    import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market


# TODO: clean up to avoid these
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# TODO: this file is huge now, we should start separating concerrns
# pylint: disable=too-many-lines


class MarketActionType(Enum):
    r"""The descriptor of an action in a market"""
    INITIALIZE_MARKET = "initialize_market"

    ADD_LIQUIDITY = "add_liquidity"
    REMOVE_LIQUIDITY = "remove_liquidity"

    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"

    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketDeltas(base_market.MarketDeltas):
    r"""Specifies changes to values in the market"""
    # pylint: disable=too-many-instance-attributes
    d_base_asset: float = 0
    d_bond_asset: float = 0
    d_base_buffer: float = 0
    d_bond_buffer: float = 0
    d_lp_total_supply: float = 0
    d_share_price: float = 0
    longs_outstanding: float = 0
    shorts_outstanding: float = 0
    long_average_maturity_time: float = 0
    short_average_maturity_time: float = 0
    long_base_volume: float = 0
    short_base_volume: float = 0
    total_supply_withdraw_shares: float = 0
    withdraw_shares_ready_to_withdraw: float = 0
    withdraw_capital: float = 0
    withdraw_interest: float = 0
    long_checkpoints: defaultdict[float, float] = field(default_factory=lambda: defaultdict(float))
    short_checkpoints: defaultdict[float, float] = field(default_factory=lambda: defaultdict(float))
    total_supply_longs: defaultdict[float, float] = field(default_factory=lambda: defaultdict(float))
    total_supply_shorts: defaultdict[float, float] = field(default_factory=lambda: defaultdict(float))


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketActionResult(base_market.MarketActionResult):
    r"""The result to a market of performing a trade"""
    d_base: float
    d_bonds: float


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class MarketAction(base_market.MarketAction):
    r"""Market action specification"""
    # these two variables are required to be set by the strategy
    action_type: MarketActionType
    # amount to supply for the action
    trade_amount: float  # TODO: should this be a Quantity, not a float? Make sure, then delete fixme
    # the agent's wallet
    wallet: wallet.Wallet
    # min amount to receive for the action
    min_amount_out: float = 0
    # mint time is set only for trades that act on existing positions (close long or close short)
    mint_time: Optional[float] = None


def check_action(agent_action: MarketAction) -> None:
    r"""Ensure that the agent action is an allowed action for this market

    Parameters
    ----------
    action_type : MarketActionType
        See MarketActionType for all acceptable actions that can be performed on this market

    Returns
    -------
    None
    """
    if (
        agent_action.action_type
        in [
            MarketActionType.CLOSE_LONG,
            MarketActionType.CLOSE_SHORT,
        ]
        and agent_action.mint_time is None
    ):
        raise ValueError("ERROR: agent_action.mint_time must be provided when closing a short or long")


def calculate_lp_allocation_adjustment(
    positions_outstanding: float,
    base_volume: float,
    average_time_remaining: float,
    share_price: float,
) -> float:
    """Calculates an adjustment amount for lp shares.

    Calculates an amount to adjust an lp allocation based off of either shorts or longs outstanding via:
        base_adjustment = t * base_volume + (1 - t) * _positions_outstanding

    Parameters
    ----------
    positions_outstanding: float
        Either shorts_outstanding or longs_outstanding
    base_volume: float
        Either the aggregrate short_base_volume or long_base_volume
    average_time_remaining: float
        The normalized time remaining for either shorts or longs
    share_price: float
        The current share price

    Returns
    -------
    float
        An amount to adjust the lp shares by.  This ensures that lp's don't get access to interest
        already accrued by previous lps.
    """
    # base_adjustment = t * base_volume + (1 - t) * _positions_outstanding
    base_adjustment = (average_time_remaining * base_volume) + (1 - average_time_remaining) * positions_outstanding
    # adjustment = base_adjustment / c
    return base_adjustment / share_price


def calculate_short_adjustment(
    market_state: hyperdrive_market.MarketState,
    position_duration: time.StretchedTime,
    market_time: float,
) -> float:
    """Calculates an adjustment amount for lp shares based on the amount of shorts outstanding

    Parameters
    ----------
    market_state: hyperdrive_market.MarketState
        The state of the hyperdrive market.
    position_duration: time.StretechedTime
        Used to get the average normalized time remaining for the shorts.
    market_time: float
        The current time in years.

    Returns
    -------
    float
        An amount to adjust the lp shares by.  This ensures that lp's don't get access to interest
        already accrued by previous lps.
    """
    if market_time > market_state.short_average_maturity_time:
        return 0
    # (year_end - year_start) / (normalizing_constant / 365)
    normalized_time_remaining = (market_state.short_average_maturity_time - market_time) / (
        position_duration.normalizing_constant / 365
    )
    return calculate_lp_allocation_adjustment(
        market_state.shorts_outstanding,
        market_state.short_base_volume,
        normalized_time_remaining,
        market_state.share_price,
    )


def calculate_long_adjustment(
    market_state: hyperdrive_market.MarketState,
    position_duration: time.StretchedTime,
    market_time: float,
) -> float:
    """Calculates an adjustment amount for lp shares based on the amount of longs outstanding

    Parameters
    ----------
    market_state: hyperdrive_market.MarketState
        The state of the hyperdrive market.
    position_duration: time.StretechedTime
        Used to get the average normalized time remaining for the longs.
    market_time: float
        The current time in years.

    Returns
    -------
    float
        An amount to adjust the lp shares by.  This ensures that lp's don't get access to interest
        already accrued by previous lps.
    """
    if market_time > market_state.long_average_maturity_time:
        return 0
    # (year_end - year_start) / (normalizing_constant / 365)
    normalized_time_remaining = (market_state.long_average_maturity_time - market_time) / (
        position_duration.normalizing_constant / 365
    )
    return calculate_lp_allocation_adjustment(
        market_state.longs_outstanding,
        market_state.long_base_volume,
        normalized_time_remaining,
        market_state.share_price,
    )


def calc_lp_out_given_tokens_in(
    base_in: float,
    rate: float,
    market_state: hyperdrive_market.MarketState,
    market_time: float,
    position_duration: time.StretchedTime,
) -> tuple[float, float, float]:
    r"""Computes the amount of LP tokens to be minted for a given amount of base asset

    .. math::
        \Delta l = \frac{l \cdot \Delta z}{z + a_s - a_l}

    where a_s and a_l are the short and long adjustments. In order to calculate these we need to
    keep track of the long and short base volumes, amounts outstanding and average maturity
    times.

    Parameters
    ----------
    base_in: float
        The amount of base provided to exchange for lp tokens.
    rate: float
        The fixed rate value of the bonds.
    market_state: hyperdrive_market.MarketState
        Hyperdrive's market state.
    market_time: float
        The current time in years.
    position_duration: time.StretchedTime
        Position duration information of the bonds.

    Returns
    -------
    tuple[float, float, float]
        Returns the lp_out, delta_base and delta_bonds.  The delta_base and delta_bonds values are
        used to update the reserves of the pool.
    """
    delta_shares = base_in / market_state.share_price
    annualized_time = time.norm_days(position_duration.days, 365)
    # bonds computed as y = z/2 * (mu * (1 + rt)**(1/tau) - c)
    delta_bond_reserves = (market_state.share_reserves + delta_shares) / 2 * (
        market_state.init_share_price * (1 + rate * annualized_time) ** (1 / position_duration.stretched_time)
        - market_state.share_price
    ) - market_state.bond_reserves
    if market_state.share_reserves > 0:  # normal case where we have some share reserves
        short_adjustment = calculate_short_adjustment(market_state, position_duration, market_time)
        long_adjustment = calculate_long_adjustment(market_state, position_duration, market_time)
        lp_out = (delta_shares * market_state.lp_total_supply) / (
            market_state.share_reserves + short_adjustment - long_adjustment
        )
    else:  # initial case where we have 0 share reserves or final case where it has been removed
        lp_out = delta_shares
    return lp_out, base_in, delta_bond_reserves


def calculate_base_volume(base_amount: float, bond_amount: float, normalized_time_remaining: float) -> float:
    """Calculates the base volume of an open trade.
    Output is given the base amount, the bond amount, and the time remaining.
    Since the base amount takes into account backdating, we can't use this as our base volume.
    Since we linearly interpolate between the base volume and the bond amount as the time
    remaining goes from 1 to 0, the base volume can be determined as follows:

    .. math::
        base_amount = t * base_volume + (1 - t) * bond_amount
                            =>
        base_volume = (base_amount - (1 - t) * bond_amount) / t

    Parameters
    ----------
    base_amount: float
        The amount of base provided for the trade.
    bond_amount: float
        The amount of bonds used to close the position.
    normalized_time_remaining: str
        The normailzed time remaining of the trade from 1 -> 0.

    Returns
    -------
    float
        The base volume.
    """
    # If the time remaining is 0, the position has already matured and doesn't have an impact on
    # LP's ability to withdraw. This is a pathological case that should never arise.
    if normalized_time_remaining == 0:
        return 0
    return (base_amount - (1 - normalized_time_remaining) * bond_amount) / normalized_time_remaining


def calc_checkpoint_deltas(
    market: hyperdrive_market.Market, checkpoint_time: float, bond_amount: float, position: Literal["short", "long"]
) -> tuple[float, defaultdict[float, float], float]:
    """Compute deltas to close any outstanding positions at the checkpoint_time

    Parameters
    ----------
    market: hyperdrive_market.Market
        Deltas are computed for this market.
    checkpoint_time: float
        The checkpoint (mint) time to be used for updating.
    bond_amount: float
        The amount of bonds used to close the position.
    position: Literal["short", "long"]
        Either "short" or "long", indicating what type of position is being closed.

    Returns
    -------
    d_base_volume: float
        The change in base volume for the given position.
    d_checkpoints: defaultdict[float, float]
        The change in checkpoint volume for the given checkpoint_time (key) and position (value).
    lp_margin: float
        The amount of margin that LPs provided on the long position.
    """
    total_supply = "total_supply_shorts" if position == "short" else "total_supply_longs"
    # Calculate the amount of margin that LPs provided on the long position and update the base
    # volume aggregates.
    lp_margin = 0.0
    # Get the total supply of longs in the checkpoint of the longs being closed. If the longs are
    # closed before maturity, we add the amount of longs being closed since the total supply is
    # decreased when burning the long tokens.
    checkpoint_amount = market.market_state[total_supply][checkpoint_time]
    # If the checkpoint has nothing stored, then do not update
    if checkpoint_amount == 0:
        return (0, defaultdict(float, {checkpoint_time: 0}), 0)
    proportional_base_volume = (
        market.market_state.checkpoints[checkpoint_time].long_base_volume * bond_amount / checkpoint_amount
    )
    d_base_volume = -proportional_base_volume
    d_checkpoints = defaultdict(float, {checkpoint_time: d_base_volume})
    lp_margin = bond_amount - proportional_base_volume

    return (d_base_volume, d_checkpoints, lp_margin)


def calc_open_short(
    wallet_address: int,
    bond_amount: float,
    market: hyperdrive_market.Market,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """Calculate the agent & market deltas for opening a short position.
    Shorts need their margin account to cover the worst case scenario (p=1).
    The margin comes from 2 sources:
        - the proceeds from your short sale (p)
        - the max value you cover with base deposted from your wallet (1-p)
    These two components are both priced in base, yet happily add up to 1.0 units of bonds.
    This gives us the following identity:
        total margin (base, from proceeds + deposited) = face value of bonds shorted (# of bonds)
    This guarantees that bonds in the system are always fully backed by an equal amount of base.

    Parameters
    ---------
    wallet_address: int
        The address of the agent's wallet.
    bond_amount: float
        The amount of bonds the agent is shorting.
    market: hyperdrive_market.Market
        The market the agent is opening a short on.

    Returns
    -------
    tuple[MarketDeltas, wallet.Wallet]
        Returns the deltas to update the market and the agent's wallet after opening a short.
    """
    # get the checkpointed time remaining
    mint_time = market.latest_checkpoint_time
    years_remaining = time.get_years_remaining(
        market_time=market.block_time.time,
        mint_time=mint_time,
        position_duration_years=market.position_duration.days / 365,
    )
    time_remaining = time.StretchedTime(
        days=years_remaining * 365,
        time_stretch=market.position_duration.time_stretch,
        normalizing_constant=market.position_duration.normalizing_constant,
    )
    trade_quantity = types.Quantity(amount=bond_amount, unit=types.TokenType.PT)
    market.pricing_model.check_input_assertions(
        quantity=trade_quantity, market_state=market.market_state, time_remaining=time_remaining
    )
    # perform the trade
    trade_result = market.pricing_model.calc_out_given_in(
        in_=trade_quantity, market_state=market.market_state, time_remaining=time_remaining
    )
    # calculate the trader's deposit amount
    normalized_time_elapsed = (market.block_time.time - mint_time) / market.position_duration.years
    share_proceeds = bond_amount * normalized_time_elapsed / market.market_state.share_price
    share_reserves_delta = trade_result.market_result.d_base / market.market_state.share_price
    bond_reserves_delta = trade_result.market_result.d_bonds
    share_proceeds += abs(share_reserves_delta)  # delta is negative from p.o.v of market, positive for shorter
    open_share_price = market.market_state.checkpoints[mint_time].share_price
    share_price = market.market_state.share_price
    trader_deposit = calc_short_proceeds(bond_amount, share_proceeds, open_share_price, share_price, share_price)
    # get gov fees accrued
    market.market_state.gov_fees_accrued += trade_result.breakdown.gov_fee
    # make sure the trade is valid
    market.pricing_model.check_output_assertions(trade_result=trade_result)
    # update accouting for average maturity time, base volume and longs outstanding
    short_average_maturity_time = update_weighted_average(
        average=market.market_state.short_average_maturity_time,
        total_weight=market.market_state.shorts_outstanding,
        delta=market.annualized_position_duration,
        delta_weight=bond_amount,
        is_adding=True,
    )
    d_short_average_maturity_time = short_average_maturity_time - market.market_state.short_average_maturity_time
    d_short_average_maturity_time = (
        market.market_state.short_average_maturity_time
        if market.market_state.short_average_maturity_time + d_short_average_maturity_time < 0
        else d_short_average_maturity_time
    )
    # calculate_base_volume needs a positive base, so we use the value from user_result
    base_volume = calculate_base_volume(trade_result.user_result.d_base, bond_amount, 1)
    # Calculate what the updated bond reserves would be with constant apr
    _, updated_bond_reserves = calc_update_reserves(
        market.market_state.share_reserves + share_reserves_delta,
        market.market_state.bond_reserves + bond_reserves_delta,
        share_reserves_delta,
    )
    bond_reserves_delta += updated_bond_reserves - market.market_state.bond_reserves
    # return the market and wallet deltas
    market_deltas = MarketDeltas(
        d_base_asset=trade_result.market_result.d_base,
        d_bond_asset=bond_reserves_delta,
        # TODO: remove the bond buffer
        d_bond_buffer=bond_amount,
        short_base_volume=base_volume,
        shorts_outstanding=bond_amount,
        short_average_maturity_time=d_short_average_maturity_time,
        short_checkpoints=defaultdict(float, {market.latest_checkpoint_time: base_volume}),
        total_supply_shorts=defaultdict(float, {market.latest_checkpoint_time: bond_amount}),
    )
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=-types.Quantity(amount=trader_deposit, unit=types.TokenType.BASE),
        shorts={
            market.latest_checkpoint_time: wallet.Short(
                balance=bond_amount, open_share_price=market.market_state.share_price
            )
        },
        fees_paid=trade_result.breakdown.fee,
    )
    return market_deltas, agent_deltas


def calc_close_short(
    wallet_address: int,
    bond_amount: float,
    market: hyperdrive_market.Market,
    mint_time: float,
    open_share_price: float,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """
    when closing a short, the number of bonds being closed out, at face value, give us the total margin returned
    the worst case scenario of the short is reduced by that amount, so they no longer need margin for it
    at the same time, margin in their account is drained to pay for the bonds being bought back
    so the amount returned to their wallet is trade_amount minus the cost of buying back the bonds
    that is, d_base = trade_amount (# of bonds) + trade_result.user_result.d_base (a negative amount, in base))
    for more on short accounting, see the open short method

    Parameters
    ---------
    wallet_address: int
        The address of the agent's wallet.
    bond_amount: float
        The amount of bonds the agent is shorting.
    market: hyperdrive_market.Market
        The market the agent is opening a short on.
    mint_time: float
        The time in years when the short was opened.
    open_share_price: float
        The share price when the short was opened.

    Returns
    -------
    tuple[MarketDeltas, wallet.Wallet]
        Returns the deltas to update the market and the agent's wallet after opening a short.
    """
    if bond_amount > market.market_state.bond_reserves - market.market_state.bond_buffer:
        raise AssertionError("not enough reserves to close short")
    # Compute the time remaining given the mint time.
    years_remaining = time.get_years_remaining(
        market_time=market.block_time.time,
        mint_time=mint_time,
        position_duration_years=market.position_duration.days / 365,
    )  # all args in units of years
    time_remaining = time.StretchedTime(
        days=years_remaining * 365,  # converting years to days
        time_stretch=market.position_duration.time_stretch,
        normalizing_constant=market.position_duration.normalizing_constant,
    )
    # Perform the trade.
    trade_quantity = types.Quantity(amount=bond_amount, unit=types.TokenType.PT)
    market.pricing_model.check_input_assertions(
        quantity=trade_quantity,
        market_state=market.market_state,
        time_remaining=time_remaining,
    )
    trade_result = market.pricing_model.calc_in_given_out(
        out=trade_quantity,
        market_state=market.market_state,
        time_remaining=time_remaining,
    )
    share_reserves_delta = trade_result.market_result.d_base / market.market_state.share_price
    bond_reserves_delta = trade_result.market_result.d_bonds
    share_payment = trade_result.user_result.d_base / market.market_state.share_price
    # update governance fees
    market.market_state.gov_fees_accrued += trade_result.breakdown.gov_fee
    # Make sure the trade is valid
    market.pricing_model.check_output_assertions(trade_result=trade_result)
    # Update accouting for average maturity time, base volume and longs outstanding
    short_average_maturity_time = update_weighted_average(
        average=market.market_state.short_average_maturity_time,
        total_weight=market.market_state.shorts_outstanding,
        delta=market.annualized_position_duration,
        delta_weight=bond_amount,
        is_adding=False,
    )
    d_short_average_maturity_time = short_average_maturity_time - market.market_state.short_average_maturity_time
    # Return the market and wallet deltas.
    d_base_volume, d_checkpoints, lp_margin = calc_checkpoint_deltas(market, mint_time, bond_amount, "short")
    # TODO: remove this clamp when short withdrawal shares calculated
    # don't let short base volume go negative
    d_base_volume = np.amax([d_base_volume, -market.market_state.short_base_volume])
    # The flat component of the trade is added to the pool's liquidity since it represents the fixed
    # interest that the short pays to the pool.
    share_adjustment = share_payment - abs(share_reserves_delta)
    # If there is a withdraw processing, we pay out as much of the withdrawal pool as possible with
    # the margin released and interest accrued on the position to the withdrawal pool.
    margin_needs_to_be_freed = (
        market.market_state.total_supply_withdraw_shares > market.market_state.withdraw_shares_ready_to_withdraw
    )
    withdraw_pool_deltas = MarketDeltas()
    withdrawal_proceeds = share_payment
    if margin_needs_to_be_freed:
        proceeds_in_base = trade_result.user_result.d_base
        interest = 0
        if proceeds_in_base >= lp_margin:
            interest = (proceeds_in_base - lp_margin) / market.market_state.share_price
        withdraw_pool_deltas = market.calc_free_margin(
            withdrawal_proceeds - interest, lp_margin / open_share_price, interest
        )
        withdrawal_proceeds = withdraw_pool_deltas.withdraw_capital + withdraw_pool_deltas.withdraw_interest
        share_adjustment -= withdrawal_proceeds
    # Add the flat component of the trade to the pool's liquidity and remove any LP proceeds paid to
    # the withdrawal pool from the pool's liquidity.
    share_reserves = market.market_state.share_reserves + share_reserves_delta
    bond_reserves = market.market_state.bond_reserves + bond_reserves_delta
    adjusted_share_reserves, adjusted_bond_reserves = calc_update_reserves(
        share_reserves, bond_reserves, share_adjustment
    )
    share_reserves_delta = adjusted_share_reserves - market.market_state.share_reserves
    bond_reserves_delta = adjusted_bond_reserves - market.market_state.bond_reserves
    market_deltas = MarketDeltas(
        d_base_asset=share_reserves_delta * market.market_state.share_price,
        d_bond_asset=bond_reserves_delta,
        d_bond_buffer=-bond_amount,
        short_base_volume=d_base_volume,
        shorts_outstanding=-bond_amount,
        short_average_maturity_time=d_short_average_maturity_time,
        short_checkpoints=d_checkpoints,
        total_supply_shorts=defaultdict(float, {mint_time: -bond_amount}),
        withdraw_capital=withdraw_pool_deltas.withdraw_capital,
        withdraw_interest=withdraw_pool_deltas.withdraw_interest,
        withdraw_shares_ready_to_withdraw=withdraw_pool_deltas.withdraw_shares_ready_to_withdraw,
    )
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=types.Quantity(
            amount=(market.market_state.share_price / open_share_price) * bond_amount + trade_result.user_result.d_base,
            unit=types.TokenType.BASE,
        ),  # see CLOSING SHORT LOGIC above
        shorts={
            mint_time: wallet.Short(
                balance=-bond_amount,
                open_share_price=0,
            )
        },
        fees_paid=trade_result.breakdown.fee,
    )
    return market_deltas, agent_deltas


def calc_open_long(
    wallet_address: int,
    base_amount: float,
    market: hyperdrive_market.Market,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """
    When a trader opens a long, they put up base and are given long tokens. As time passes, an amount of the longs
    proportional to the time that has passed are considered to be “mature” and can be redeemed one-to-one.
    The remaining amount of longs are sold on the internal AMM. The trader doesn’t receive any variable interest
    from their long positions, so the only money they make on closing is from the long maturing and the fixed
    rate changing.

    Parameters
    ----------
    wallet_address: int
        integer address for the agent's wallet
    base_amount: float
        amount in base that the agent wishes to trade

    Returns
    -------
    tuple[MarketDeltas, wallet.Wallet]
        The deltas that should be applied to the market and agent
    """
    if base_amount > market.market_state.bond_reserves * market.spot_price:
        raise AssertionError(
            "ERROR: cannot open a long with more than the available bond resereves, "
            f"but {base_amount=} > {market.market_state.bond_reserves=}."
        )
    # Perform the trade.
    trade_quantity = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
    market.pricing_model.check_input_assertions(
        quantity=trade_quantity,
        market_state=market.market_state,
        time_remaining=market.position_duration,
    )
    trade_result = market.pricing_model.calc_out_given_in(
        in_=trade_quantity,
        market_state=market.market_state,
        time_remaining=market.position_duration,
    )
    market.market_state.gov_fees_accrued += trade_result.breakdown.gov_fee
    # TODO: add assert: if share_price * share_reserves < longs_outstanding then revert,
    # this should be in hyperdrive.check_output_assertions which then calls
    # super().check_output_assertions
    # Make sure the trade is valid
    market.pricing_model.check_output_assertions(trade_result=trade_result)
    # Update accouting for average maturity time, base volume and longs outstanding
    long_average_maturity_time = update_weighted_average(
        average=market.market_state.long_average_maturity_time,
        total_weight=market.market_state.longs_outstanding,
        delta=market.annualized_position_duration,
        delta_weight=-trade_result.market_result.d_bonds,
        is_adding=True,
    )
    d_long_average_maturity_time = long_average_maturity_time - market.market_state.long_average_maturity_time
    # TODO: don't use 1 for time_remaining once we have checkpointing
    base_volume = calculate_base_volume(trade_result.market_result.d_base, base_amount, 1)
    # Get the market and wallet deltas to return.
    market_deltas = MarketDeltas(
        d_base_asset=trade_result.market_result.d_base,
        d_bond_asset=trade_result.market_result.d_bonds,
        d_base_buffer=trade_result.user_result.d_bonds,
        long_base_volume=base_volume,
        longs_outstanding=trade_result.user_result.d_bonds,
        long_average_maturity_time=d_long_average_maturity_time,
        long_checkpoints=defaultdict(float, {market.latest_checkpoint_time: base_volume}),
        total_supply_longs=defaultdict(float, {market.latest_checkpoint_time: trade_result.user_result.d_bonds}),
    )
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=types.Quantity(amount=trade_result.user_result.d_base, unit=types.TokenType.BASE),
        longs={market.latest_checkpoint_time: wallet.Long(trade_result.user_result.d_bonds)},
        fees_paid=trade_result.breakdown.fee,
    )
    return market_deltas, agent_deltas


def calc_close_long(
    wallet_address: int,
    bond_amount: float,
    market: hyperdrive_market.Market,
    mint_time: float,
    is_trade: bool = True,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """Calculations for closing a long position.
    This function takes the trade spec & turn it into trade details.

    Parameters
    ---------
    wallet_address: int
        The address of the agent's wallet.
    bond_amount: float
        The amount of bonds the agent is shorting.
    market: hyperdrive_market.Market
        The market the agent is opening a short on.
    mint_time: float
        The time in years when the short was opened.
    is_trade: bool
        If an agent is performing a trade.  If false, this means a checkpoint is applied in which
        case we do not want to update the pool reserves yet since the agent hasn't actually closed
        their position yet.

    Returns
    -------
    tuple[MarketDeltas, wallet.Wallet]
        Returns the deltas to update the market and the agent's wallet after opening a short.
    """
    # Compute the time remaining given the mint time.
    years_remaining = time.get_years_remaining(
        market_time=market.block_time.time,
        mint_time=mint_time,
        position_duration_years=market.position_duration.days / 365,
    )  # all args in units of years
    time_remaining = time.StretchedTime(
        days=years_remaining * 365,  # converting years to days
        time_stretch=market.position_duration.time_stretch,
        normalizing_constant=market.position_duration.normalizing_constant,
    )
    # Perform the trade.
    trade_quantity = types.Quantity(amount=bond_amount, unit=types.TokenType.PT)
    market.pricing_model.check_input_assertions(
        quantity=trade_quantity,
        market_state=market.market_state,
        time_remaining=time_remaining,
    )
    # if we are applying a checkpoint, we don't update the reserves
    bond_reserves_delta = 0
    share_reserves_delta = 0
    base_proceeds = 0
    fee = 0
    gov_fee = 0
    if is_trade:
        trade_result = market.pricing_model.calc_out_given_in(
            in_=trade_quantity,
            market_state=market.market_state,
            time_remaining=time_remaining,
        )
        market.pricing_model.check_output_assertions(trade_result=trade_result)
        bond_reserves_delta = trade_result.market_result.d_bonds
        share_reserves_delta = trade_result.market_result.d_base / market.market_state.share_price
        base_proceeds = trade_result.user_result.d_base
        fee = trade_result.breakdown.fee
        gov_fee = trade_result.breakdown.gov_fee

    market.market_state.gov_fees_accrued += gov_fee
    # Make sure the trade is valid
    # Update accouting for average maturity time, base volume and longs outstanding
    long_average_maturity_time = update_weighted_average(
        average=market.market_state.long_average_maturity_time,
        total_weight=market.market_state.longs_outstanding,
        delta=market.annualized_position_duration,
        delta_weight=bond_amount,
        is_adding=False,
    )
    d_long_average_maturity_time = long_average_maturity_time - market.market_state.long_average_maturity_time
    d_base_volume, d_checkpoints, lp_margin = calc_checkpoint_deltas(market, mint_time, bond_amount, "long")
    # get the share adjustment amount
    normalized_time_elapsed = (market.block_time.time - mint_time) / market.position_duration.years
    share_proceeds = bond_amount * normalized_time_elapsed / market.market_state.share_price
    maturity_time = mint_time + market.position_duration.years
    close_share_price = (
        market.market_state.share_price
        if market.block_time.time < maturity_time
        else market.market_state.checkpoints[mint_time].share_price
    )
    if market.market_state.init_share_price > close_share_price:
        share_proceeds *= close_share_price / market.market_state.init_share_price
    # The amount of liquidity that needs to be removed.
    share_adjustment = -(share_proceeds - share_reserves_delta)
    margin_needs_to_be_freed = (
        market.market_state.total_supply_withdraw_shares > market.market_state.withdraw_shares_ready_to_withdraw
    )
    withdraw_pool_deltas = MarketDeltas()
    if margin_needs_to_be_freed:
        open_share_price = market.market_state.checkpoints[mint_time].long_share_price
        # The withdrawal pool has preferential access to the proceeds generated from closing longs.
        # The LP proceeds when longs are closed are equivalent to the proceeds of short positions.
        withdrawal_proceeds = calc_short_proceeds(
            bond_amount,
            share_proceeds,
            open_share_price,
            market.market_state.share_price,
            market.market_state.share_price,
        )
        lp_interest = calc_short_interest(
            bond_amount,
            open_share_price,
            market.market_state.share_price,
            market.market_state.share_price,
        )
        capital_freed = 0
        if withdrawal_proceeds > lp_interest:
            capital_freed = withdrawal_proceeds - lp_interest

        # Pay out the withdrawal pool with the freed margin. The withdrawal proceeds are split into
        # the margin pool and the interest pool. The proceeds that are distributed to the margin and
        # interest pools are removed from the pool's liquidity.
        withdraw_pool_deltas = market.calc_free_margin(
            capital_freed,
            # TODO: make sure that the withdrawal shares are actually instantiated with the open
            # share price. Think more about this as it seems weird to have to convert back using an
            # old share price considering that this may not have been the share price at the time
            # the withdrawal was initiated.
            lp_margin / open_share_price,
            lp_interest,
        )
        withdrawal_proceeds = withdraw_pool_deltas.withdraw_capital + withdraw_pool_deltas.withdraw_interest
        share_adjustment -= withdrawal_proceeds
    # Remove the flat component of the trade as well as any LP proceeds paid to the withdrawal pool
    # from the pool's liquidity.
    share_reserves = market.market_state.share_reserves + share_reserves_delta
    bond_reserves = market.market_state.bond_reserves + bond_reserves_delta
    adjusted_share_reserves, adjusted_bond_reserves = calc_update_reserves(
        share_reserves, bond_reserves, share_adjustment
    )
    share_reserves_delta = adjusted_share_reserves - market.market_state.share_reserves
    bond_reserves_delta = adjusted_bond_reserves - market.market_state.bond_reserves
    # Return the market and wallet deltas.
    market_deltas = MarketDeltas(
        d_base_asset=share_reserves_delta * market.market_state.share_price,
        d_bond_asset=bond_reserves_delta,
        d_base_buffer=-bond_amount,
        long_base_volume=d_base_volume,
        longs_outstanding=-bond_amount,
        long_average_maturity_time=d_long_average_maturity_time,
        long_checkpoints=d_checkpoints,
        total_supply_longs=defaultdict(float, {mint_time: -bond_amount}),
        withdraw_capital=withdraw_pool_deltas.withdraw_capital,
        withdraw_interest=withdraw_pool_deltas.withdraw_interest,
        withdraw_shares_ready_to_withdraw=withdraw_pool_deltas.withdraw_shares_ready_to_withdraw,
    )
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=types.Quantity(amount=base_proceeds, unit=types.TokenType.BASE),
        longs={mint_time: wallet.Long(-bond_amount)},
        fees_paid=fee,
    )
    return market_deltas, agent_deltas


def calc_update_reserves(share_reserves: float, bond_reserves: float, share_reserves_delta) -> tuple[float, float]:
    """Calculates updates to the pool's liquidity and holds the pool's APR constant.

    Parameters
    ----------
    share_reserves: float
        The current total shares in reserve
    bond_reserves: float
        The current total bonds in reserve
    share_reserves_delta:
        The delta that should be applied to share reserves.

    Returns
    -------
    tuple[float, float]
        updated_share_reserves and updated_bond_reserves
    """
    if share_reserves_delta == 0:
        return 0, 0
    updated_share_reserves = share_reserves + share_reserves_delta
    updated_bond_reserves = bond_reserves * updated_share_reserves / share_reserves
    return updated_share_reserves, updated_bond_reserves


def calc_short_interest(
    bond_amount: float, open_share_price: float, close_share_price: float, share_price: float
) -> float:
    """Calculates the interest in shares earned by a short position.
    The math for the short's interest in shares is given by:

    .. math::
         interest = ((c1 / c0 - 1) * dy) / c
                  = (((c1 - c0) / c0) * dy) / c
                  = ((c1 - c0) / (c0 * c)) * dy

    In the event that the interest is negative, we mark the interest
    to zero.

    Parameters
    ----------
    bond_amount: float
        The amount of bonds underlying the closed short.
    open_share_price: float
        The share price at the short's open.
    close_share_price: float
        The share price at the short's close.
    share_price: float
        the current share price.

    Returns
    -------
    float
        The short interest in shares.
    """
    share_interest = 0
    if close_share_price > open_share_price:
        share_interest = bond_amount * (close_share_price - open_share_price) / (open_share_price * share_price)
    return share_interest


def calc_short_proceeds(
    bond_amount: float, share_amount: float, open_share_price: float, close_share_price: float, share_price: float
) -> float:
    """Calculates the proceeds in shares of closing a short position.

    This takes into account the trading profits, the interest that was earned by the short, and the
    amount of margin that was released by closing the short. The math for the short's proceeds in
    base is given by:

    .. math::
        proceeds = dy - c * dz + (c1 - c0) * (dy / c0) = dy - c * dz + (c1 / c0) * dy - dy = (c1 / c0) *
        dy - c * dz

    We convert the proceeds to shares by dividing by the current share price. In the event that the
    interest is negative and outweighs the trading profits and margin released, the short's proceeds
    are marked to zero.

    Parameters
    ----------
    bond_amount: float
        The amount of bonds underlying the closed short.
    share_amount:
        The amount of shares that it costs to close the short.
    open_share_price: float
        the share price at the short's open.
    close_share_price: float
        the share price at the short's close.
    share_price: float
        The current share price.

    Returns
    -------
    float
        The short proceeds in shares as share_proceeds.
    """
    share_proceeds = 0
    bond_factor = bond_amount * close_share_price / (open_share_price * share_price)
    if bond_factor > share_amount:
        share_proceeds = bond_factor - share_amount
    return share_proceeds


def calc_add_liquidity(
    wallet_address: int,
    base_in: float,
    market: hyperdrive_market.Market,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """Computes new deltas for bond & share reserves after liquidity is added.

    Parameters
    ----------
    wallet_address : int
        The wallet address for the agent.
    base_in: float
        The amount of base the agent is providing.
    market : hyperdrive_market.Market
        The market the agent is providing liquidity for.

    Returns
    -------
    tuple[MarketDeltas, wallet.Wallet]
        Returns the deltas to update the market and the agent's wallet after providing liquidity.
    """
    # get_rate assumes that there is some amount of reserves, and will throw an error if share_reserves is zero
    if (
        market.market_state.share_reserves == 0 and market.market_state.bond_reserves == 0
    ):  # pool has not been initialized
        rate = 0
    else:
        rate = market.fixed_apr
    # sanity check inputs
    market.pricing_model.check_input_assertions(
        quantity=types.Quantity(
            amount=base_in, unit=types.TokenType.PT
        ),  # temporary Quantity object just for this check
        market_state=market.market_state,
        time_remaining=market.position_duration,
    )
    # perform the trade
    lp_out, d_base_reserves, d_bond_reserves = calc_lp_out_given_tokens_in(
        base_in=base_in,
        rate=rate,
        market_state=market.market_state,
        market_time=market.block_time.time,
        position_duration=market.position_duration,
    )
    market_deltas = MarketDeltas(
        d_base_asset=d_base_reserves,
        d_bond_asset=d_bond_reserves,
        d_lp_total_supply=lp_out,
    )
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=-types.Quantity(amount=d_base_reserves, unit=types.TokenType.BASE),
        lp_tokens=lp_out,
    )
    return market_deltas, agent_deltas


def calc_remove_liquidity(
    wallet_address: int,
    lp_shares: float,
    market: hyperdrive_market.Market,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """Computes new deltas for bond & share reserves after liquidity is removed.

    Parameters
    ----------
    wallet_address : int
        The wallet address for the agent.
    lp_shares: float
        The amount of lp_shares the agent is redeeming.
    market : hyperdrive_market.Market
        The market the agent is removing liquidity from.

    Returns
    -------
    tuple[MarketDeltas, wallet.Wallet]
        Returns the deltas to update the market and the agent's wallet after removing liquidity.
    """
    # sanity check inputs
    market.pricing_model.check_input_assertions(
        quantity=types.Quantity(
            amount=lp_shares, unit=types.TokenType.LP_SHARE
        ),  # temporary Quantity object just for this check
        market_state=market.market_state,
        time_remaining=market.position_duration,
    )
    # perform the trade
    delta_shares, delta_bonds = market.pricing_model.calc_tokens_out_given_lp_in(
        lp_in=lp_shares,
        market_state=market.market_state,
    )
    delta_base = market.market_state.share_price * delta_shares
    # calculate withdraw shares for the user
    user_margin = market.market_state.longs_outstanding - market.market_state.long_base_volume
    user_margin += market.market_state.short_base_volume
    user_margin -= (
        market.market_state.total_supply_withdraw_shares - market.market_state.withdraw_shares_ready_to_withdraw
    )
    user_margin = user_margin * lp_shares / market.market_state.lp_total_supply
    withdraw_shares = user_margin / market.market_state.share_price
    # create and return the deltas
    market_deltas = MarketDeltas(
        d_base_asset=-delta_base,
        d_bond_asset=-delta_bonds,
        d_lp_total_supply=-lp_shares,
        total_supply_withdraw_shares=withdraw_shares,
    )
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=types.Quantity(amount=delta_base, unit=types.TokenType.BASE),
        lp_tokens=-lp_shares,
        withdraw_shares=withdraw_shares,
    )
    return market_deltas, agent_deltas


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketDeltasFP(base_market.MarketDeltas):
    r"""Specifies changes to values in the market"""
    # pylint: disable=too-many-instance-attributes
    d_base_asset: FixedPoint = FixedPoint(0)
    d_bond_asset: FixedPoint = FixedPoint(0)
    d_base_buffer: FixedPoint = FixedPoint(0)
    d_bond_buffer: FixedPoint = FixedPoint(0)
    d_lp_total_supply: FixedPoint = FixedPoint(0)
    d_share_price: FixedPoint = FixedPoint(0)
    longs_outstanding: FixedPoint = FixedPoint(0)
    shorts_outstanding: FixedPoint = FixedPoint(0)
    long_average_maturity_time: FixedPoint = FixedPoint(0)
    short_average_maturity_time: FixedPoint = FixedPoint(0)
    long_base_volume: FixedPoint = FixedPoint(0)
    short_base_volume: FixedPoint = FixedPoint(0)
    total_supply_withdraw_shares: FixedPoint = FixedPoint(0)
    withdraw_shares_ready_to_withdraw: FixedPoint = FixedPoint(0)
    withdraw_capital: FixedPoint = FixedPoint(0)
    withdraw_interest: FixedPoint = FixedPoint(0)
    long_checkpoints: defaultdict[FixedPoint, FixedPoint] = field(
        default_factory=lambda: defaultdict(lambda: FixedPoint(0))
    )
    short_checkpoints: defaultdict[FixedPoint, FixedPoint] = field(
        default_factory=lambda: defaultdict(lambda: FixedPoint(0))
    )
    total_supply_longs: defaultdict[FixedPoint, FixedPoint] = field(
        default_factory=lambda: defaultdict(lambda: FixedPoint(0))
    )
    total_supply_shorts: defaultdict[FixedPoint, FixedPoint] = field(
        default_factory=lambda: defaultdict(lambda: FixedPoint(0))
    )


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketActionResultFP(base_market.MarketActionResultFP):
    r"""The result to a market of performing a trade"""
    d_base: FixedPoint
    d_bonds: FixedPoint


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class MarketActionFP(base_market.MarketAction):
    r"""Market action specification"""
    # these two variables are required to be set by the strategy
    action_type: MarketActionType
    # amount to supply for the action
    trade_amount: FixedPoint  # TODO: should this be a Quantity, not a float? Make sure, then delete fixme
    # the agent's wallet
    wallet: wallet.WalletFP
    # min amount to receive for the action
    min_amount_out: FixedPoint = FixedPoint(0)
    # mint time is set only for trades that act on existing positions (close long or close short)
    mint_time: Optional[FixedPoint] = None


def check_action(agent_action: MarketAction) -> None:
    r"""Ensure that the agent action is an allowed action for this market

    Parameters
    ----------
    action_type : MarketActionType
        See MarketActionType for all acceptable actions that can be performed on this market

    Returns
    -------
    None
    """
    if (
        agent_action.action_type
        in [
            MarketActionType.CLOSE_LONG,
            MarketActionType.CLOSE_SHORT,
        ]
        and agent_action.mint_time is None
    ):
        raise ValueError("ERROR: agent_action.mint_time must be provided when closing a short or long")


def calculate_lp_allocation_adjustment(
    positions_outstanding: float,
    base_volume: float,
    average_time_remaining: float,
    share_price: float,
) -> float:
    """Calculates an adjustment amount for lp shares.

    Calculates an amount to adjust an lp allocation based off of either shorts or longs outstanding via:
        base_adjustment = t * base_volume + (1 - t) * _positions_outstanding

    Parameters
    ----------
    positions_outstanding: float
        Either shorts_outstanding or longs_outstanding
    base_volume: float
        Either the aggregrate short_base_volume or long_base_volume
    average_time_remaining: float
        The normalized time remaining for either shorts or longs
    share_price: float
        The current share price

    Returns
    -------
    float
        An amount to adjust the lp shares by.  This ensures that lp's don't get access to interest
        already accrued by previous lps.
    """
    # base_adjustment = t * base_volume + (1 - t) * _positions_outstanding
    base_adjustment = (average_time_remaining * base_volume) + (1 - average_time_remaining) * positions_outstanding
    # adjustment = base_adjustment / c
    return base_adjustment / share_price


def calculate_short_adjustment(
    market_state: hyperdrive_market.MarketState,
    position_duration: time.StretchedTime,
    market_time: float,
) -> float:
    """Calculates an adjustment amount for lp shares based on the amount of shorts outstanding

    Parameters
    ----------
    market_state: hyperdrive_market.MarketState
        The state of the hyperdrive market.
    position_duration: time.StretechedTime
        Used to get the average normalized time remaining for the shorts.
    market_time: float
        The current time in years.

    Returns
    -------
    float
        An amount to adjust the lp shares by.  This ensures that lp's don't get access to interest
        already accrued by previous lps.
    """
    if market_time > market_state.short_average_maturity_time:
        return 0
    # (year_end - year_start) / (normalizing_constant / 365)
    normalized_time_remaining = (market_state.short_average_maturity_time - market_time) / (
        position_duration.normalizing_constant / 365
    )
    return calculate_lp_allocation_adjustment(
        market_state.shorts_outstanding,
        market_state.short_base_volume,
        normalized_time_remaining,
        market_state.share_price,
    )


def calculate_long_adjustment(
    market_state: hyperdrive_market.MarketState,
    position_duration: time.StretchedTime,
    market_time: float,
) -> float:
    """Calculates an adjustment amount for lp shares based on the amount of longs outstanding

    Parameters
    ----------
    market_state: hyperdrive_market.MarketState
        The state of the hyperdrive market.
    position_duration: time.StretechedTime
        Used to get the average normalized time remaining for the longs.
    market_time: float
        The current time in years.

    Returns
    -------
    float
        An amount to adjust the lp shares by.  This ensures that lp's don't get access to interest
        already accrued by previous lps.
    """
    if market_time > market_state.long_average_maturity_time:
        return 0
    # (year_end - year_start) / (normalizing_constant / 365)
    normalized_time_remaining = (market_state.long_average_maturity_time - market_time) / (
        position_duration.normalizing_constant / 365
    )
    return calculate_lp_allocation_adjustment(
        market_state.longs_outstanding,
        market_state.long_base_volume,
        normalized_time_remaining,
        market_state.share_price,
    )


def calc_lp_out_given_tokens_in(
    base_in: float,
    rate: float,
    market_state: hyperdrive_market.MarketState,
    market_time: float,
    position_duration: time.StretchedTime,
) -> tuple[float, float, float]:
    r"""Computes the amount of LP tokens to be minted for a given amount of base asset

    .. math::
        \Delta l = \frac{l \cdot \Delta z}{z + a_s - a_l}

    where a_s and a_l are the short and long adjustments. In order to calculate these we need to
    keep track of the long and short base volumes, amounts outstanding and average maturity
    times.

    Parameters
    ----------
    base_in: float
        The amount of base provided to exchange for lp tokens.
    rate: float
        The fixed rate value of the bonds.
    market_state: hyperdrive_market.MarketState
        Hyperdrive's market state.
    market_time: float
        The current time in years.
    position_duration: time.StretchedTime
        Position duration information of the bonds.

    Returns
    -------
    tuple[float, float, float]
        Returns the lp_out, delta_base and delta_bonds.  The delta_base and delta_bonds values are
        used to update the reserves of the pool.
    """
    delta_shares = base_in / market_state.share_price
    annualized_time = time.norm_days(position_duration.days, 365)
    # bonds computed as y = z/2 * (mu * (1 + rt)**(1/tau) - c)
    delta_bond_reserves = (market_state.share_reserves + delta_shares) / 2 * (
        market_state.init_share_price * (1 + rate * annualized_time) ** (1 / position_duration.stretched_time)
        - market_state.share_price
    ) - market_state.bond_reserves
    if market_state.share_reserves > 0:  # normal case where we have some share reserves
        short_adjustment = calculate_short_adjustment(market_state, position_duration, market_time)
        long_adjustment = calculate_long_adjustment(market_state, position_duration, market_time)
        lp_out = (delta_shares * market_state.lp_total_supply) / (
            market_state.share_reserves + short_adjustment - long_adjustment
        )
    else:  # initial case where we have 0 share reserves or final case where it has been removed
        lp_out = delta_shares
    return lp_out, base_in, delta_bond_reserves


def calculate_base_volume(base_amount: float, bond_amount: float, normalized_time_remaining: float) -> float:
    """Calculates the base volume of an open trade.
    Output is given the base amount, the bond amount, and the time remaining.
    Since the base amount takes into account backdating, we can't use this as our base volume.
    Since we linearly interpolate between the base volume and the bond amount as the time
    remaining goes from 1 to 0, the base volume can be determined as follows:

    .. math::
        base_amount = t * base_volume + (1 - t) * bond_amount
                            =>
        base_volume = (base_amount - (1 - t) * bond_amount) / t

    Parameters
    ----------
    base_amount: float
        The amount of base provided for the trade.
    bond_amount: float
        The amount of bonds used to close the position.
    normalized_time_remaining: str
        The normailzed time remaining of the trade from 1 -> 0.

    Returns
    -------
    float
        The base volume.
    """
    # If the time remaining is 0, the position has already matured and doesn't have an impact on
    # LP's ability to withdraw. This is a pathological case that should never arise.
    if normalized_time_remaining == 0:
        return 0
    return (base_amount - (1 - normalized_time_remaining) * bond_amount) / normalized_time_remaining


def calc_checkpoint_deltas(
    market: hyperdrive_market.Market, checkpoint_time: float, bond_amount: float, position: Literal["short", "long"]
) -> tuple[float, defaultdict[float, float], float]:
    """Compute deltas to close any outstanding positions at the checkpoint_time

    Parameters
    ----------
    market: hyperdrive_market.Market
        Deltas are computed for this market.
    checkpoint_time: float
        The checkpoint (mint) time to be used for updating.
    bond_amount: float
        The amount of bonds used to close the position.
    position: Literal["short", "long"]
        Either "short" or "long", indicating what type of position is being closed.

    Returns
    -------
    d_base_volume: float
        The change in base volume for the given position.
    d_checkpoints: defaultdict[float, float]
        The change in checkpoint volume for the given checkpoint_time (key) and position (value).
    lp_margin: float
        The amount of margin that LPs provided on the long position.
    """
    total_supply = "total_supply_shorts" if position == "short" else "total_supply_longs"
    # Calculate the amount of margin that LPs provided on the long position and update the base
    # volume aggregates.
    lp_margin = 0.0
    # Get the total supply of longs in the checkpoint of the longs being closed. If the longs are
    # closed before maturity, we add the amount of longs being closed since the total supply is
    # decreased when burning the long tokens.
    checkpoint_amount = market.market_state[total_supply][checkpoint_time]
    # If the checkpoint has nothing stored, then do not update
    if checkpoint_amount == 0:
        return (0, defaultdict(float, {checkpoint_time: 0}), 0)
    proportional_base_volume = (
        market.market_state.checkpoints[checkpoint_time].long_base_volume * bond_amount / checkpoint_amount
    )
    d_base_volume = -proportional_base_volume
    d_checkpoints = defaultdict(float, {checkpoint_time: d_base_volume})
    lp_margin = bond_amount - proportional_base_volume

    return (d_base_volume, d_checkpoints, lp_margin)


def calc_open_short(
    wallet_address: int,
    bond_amount: float,
    market: hyperdrive_market.Market,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """Calculate the agent & market deltas for opening a short position.
    Shorts need their margin account to cover the worst case scenario (p=1).
    The margin comes from 2 sources:
        - the proceeds from your short sale (p)
        - the max value you cover with base deposted from your wallet (1-p)
    These two components are both priced in base, yet happily add up to 1.0 units of bonds.
    This gives us the following identity:
        total margin (base, from proceeds + deposited) = face value of bonds shorted (# of bonds)
    This guarantees that bonds in the system are always fully backed by an equal amount of base.

    Parameters
    ---------
    wallet_address: int
        The address of the agent's wallet.
    bond_amount: float
        The amount of bonds the agent is shorting.
    market: hyperdrive_market.Market
        The market the agent is opening a short on.

    Returns
    -------
    tuple[MarketDeltas, wallet.Wallet]
        Returns the deltas to update the market and the agent's wallet after opening a short.
    """
    # get the checkpointed time remaining
    mint_time = market.latest_checkpoint_time
    years_remaining = time.get_years_remaining(
        market_time=market.block_time.time,
        mint_time=mint_time,
        position_duration_years=market.position_duration.days / 365,
    )
    time_remaining = time.StretchedTime(
        days=years_remaining * 365,
        time_stretch=market.position_duration.time_stretch,
        normalizing_constant=market.position_duration.normalizing_constant,
    )
    trade_quantity = types.Quantity(amount=bond_amount, unit=types.TokenType.PT)
    market.pricing_model.check_input_assertions(
        quantity=trade_quantity, market_state=market.market_state, time_remaining=time_remaining
    )
    # perform the trade
    trade_result = market.pricing_model.calc_out_given_in(
        in_=trade_quantity, market_state=market.market_state, time_remaining=time_remaining
    )
    # calculate the trader's deposit amount
    normalized_time_elapsed = (market.block_time.time - mint_time) / market.position_duration.years
    share_proceeds = bond_amount * normalized_time_elapsed / market.market_state.share_price
    share_reserves_delta = trade_result.market_result.d_base / market.market_state.share_price
    bond_reserves_delta = trade_result.market_result.d_bonds
    share_proceeds += abs(share_reserves_delta)  # delta is negative from p.o.v of market, positive for shorter
    open_share_price = market.market_state.checkpoints[mint_time].share_price
    share_price = market.market_state.share_price
    trader_deposit = calc_short_proceeds(bond_amount, share_proceeds, open_share_price, share_price, share_price)
    # get gov fees accrued
    market.market_state.gov_fees_accrued += trade_result.breakdown.gov_fee
    # make sure the trade is valid
    market.pricing_model.check_output_assertions(trade_result=trade_result)
    # update accouting for average maturity time, base volume and longs outstanding
    short_average_maturity_time = update_weighted_average(
        average=market.market_state.short_average_maturity_time,
        total_weight=market.market_state.shorts_outstanding,
        delta=market.annualized_position_duration,
        delta_weight=bond_amount,
        is_adding=True,
    )
    d_short_average_maturity_time = short_average_maturity_time - market.market_state.short_average_maturity_time
    d_short_average_maturity_time = (
        market.market_state.short_average_maturity_time
        if market.market_state.short_average_maturity_time + d_short_average_maturity_time < 0
        else d_short_average_maturity_time
    )
    # calculate_base_volume needs a positive base, so we use the value from user_result
    base_volume = calculate_base_volume(trade_result.user_result.d_base, bond_amount, 1)
    # Calculate what the updated bond reserves would be with constant apr
    _, updated_bond_reserves = calc_update_reserves(
        market.market_state.share_reserves + share_reserves_delta,
        market.market_state.bond_reserves + bond_reserves_delta,
        share_reserves_delta,
    )
    bond_reserves_delta += updated_bond_reserves - market.market_state.bond_reserves
    # return the market and wallet deltas
    market_deltas = MarketDeltas(
        d_base_asset=trade_result.market_result.d_base,
        d_bond_asset=bond_reserves_delta,
        # TODO: remove the bond buffer
        d_bond_buffer=bond_amount,
        short_base_volume=base_volume,
        shorts_outstanding=bond_amount,
        short_average_maturity_time=d_short_average_maturity_time,
        short_checkpoints=defaultdict(float, {market.latest_checkpoint_time: base_volume}),
        total_supply_shorts=defaultdict(float, {market.latest_checkpoint_time: bond_amount}),
    )
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=-types.Quantity(amount=trader_deposit, unit=types.TokenType.BASE),
        shorts={
            market.latest_checkpoint_time: wallet.Short(
                balance=bond_amount, open_share_price=market.market_state.share_price
            )
        },
        fees_paid=trade_result.breakdown.fee,
    )
    return market_deltas, agent_deltas


def calc_close_short(
    wallet_address: int,
    bond_amount: float,
    market: hyperdrive_market.Market,
    mint_time: float,
    open_share_price: float,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """
    when closing a short, the number of bonds being closed out, at face value, give us the total margin returned
    the worst case scenario of the short is reduced by that amount, so they no longer need margin for it
    at the same time, margin in their account is drained to pay for the bonds being bought back
    so the amount returned to their wallet is trade_amount minus the cost of buying back the bonds
    that is, d_base = trade_amount (# of bonds) + trade_result.user_result.d_base (a negative amount, in base))
    for more on short accounting, see the open short method

    Parameters
    ---------
    wallet_address: int
        The address of the agent's wallet.
    bond_amount: float
        The amount of bonds the agent is shorting.
    market: hyperdrive_market.Market
        The market the agent is opening a short on.
    mint_time: float
        The time in years when the short was opened.
    open_share_price: float
        The share price when the short was opened.

    Returns
    -------
    tuple[MarketDeltas, wallet.Wallet]
        Returns the deltas to update the market and the agent's wallet after opening a short.
    """
    if bond_amount > market.market_state.bond_reserves - market.market_state.bond_buffer:
        raise AssertionError("not enough reserves to close short")
    # Compute the time remaining given the mint time.
    years_remaining = time.get_years_remaining(
        market_time=market.block_time.time,
        mint_time=mint_time,
        position_duration_years=market.position_duration.days / 365,
    )  # all args in units of years
    time_remaining = time.StretchedTime(
        days=years_remaining * 365,  # converting years to days
        time_stretch=market.position_duration.time_stretch,
        normalizing_constant=market.position_duration.normalizing_constant,
    )
    # Perform the trade.
    trade_quantity = types.Quantity(amount=bond_amount, unit=types.TokenType.PT)
    market.pricing_model.check_input_assertions(
        quantity=trade_quantity,
        market_state=market.market_state,
        time_remaining=time_remaining,
    )
    trade_result = market.pricing_model.calc_in_given_out(
        out=trade_quantity,
        market_state=market.market_state,
        time_remaining=time_remaining,
    )
    share_reserves_delta = trade_result.market_result.d_base / market.market_state.share_price
    bond_reserves_delta = trade_result.market_result.d_bonds
    share_payment = trade_result.user_result.d_base / market.market_state.share_price
    # update governance fees
    market.market_state.gov_fees_accrued += trade_result.breakdown.gov_fee
    # Make sure the trade is valid
    market.pricing_model.check_output_assertions(trade_result=trade_result)
    # Update accouting for average maturity time, base volume and longs outstanding
    short_average_maturity_time = update_weighted_average(
        average=market.market_state.short_average_maturity_time,
        total_weight=market.market_state.shorts_outstanding,
        delta=market.annualized_position_duration,
        delta_weight=bond_amount,
        is_adding=False,
    )
    d_short_average_maturity_time = short_average_maturity_time - market.market_state.short_average_maturity_time
    # Return the market and wallet deltas.
    d_base_volume, d_checkpoints, lp_margin = calc_checkpoint_deltas(market, mint_time, bond_amount, "short")
    # TODO: remove this clamp when short withdrawal shares calculated
    # don't let short base volume go negative
    d_base_volume = np.amax([d_base_volume, -market.market_state.short_base_volume])
    # The flat component of the trade is added to the pool's liquidity since it represents the fixed
    # interest that the short pays to the pool.
    share_adjustment = share_payment - abs(share_reserves_delta)
    # If there is a withdraw processing, we pay out as much of the withdrawal pool as possible with
    # the margin released and interest accrued on the position to the withdrawal pool.
    margin_needs_to_be_freed = (
        market.market_state.total_supply_withdraw_shares > market.market_state.withdraw_shares_ready_to_withdraw
    )
    withdraw_pool_deltas = MarketDeltas()
    withdrawal_proceeds = share_payment
    if margin_needs_to_be_freed:
        proceeds_in_base = trade_result.user_result.d_base
        interest = 0
        if proceeds_in_base >= lp_margin:
            interest = (proceeds_in_base - lp_margin) / market.market_state.share_price
        withdraw_pool_deltas = market.calc_free_margin(
            withdrawal_proceeds - interest, lp_margin / open_share_price, interest
        )
        withdrawal_proceeds = withdraw_pool_deltas.withdraw_capital + withdraw_pool_deltas.withdraw_interest
        share_adjustment -= withdrawal_proceeds
    # Add the flat component of the trade to the pool's liquidity and remove any LP proceeds paid to
    # the withdrawal pool from the pool's liquidity.
    share_reserves = market.market_state.share_reserves + share_reserves_delta
    bond_reserves = market.market_state.bond_reserves + bond_reserves_delta
    adjusted_share_reserves, adjusted_bond_reserves = calc_update_reserves(
        share_reserves, bond_reserves, share_adjustment
    )
    share_reserves_delta = adjusted_share_reserves - market.market_state.share_reserves
    bond_reserves_delta = adjusted_bond_reserves - market.market_state.bond_reserves
    market_deltas = MarketDeltas(
        d_base_asset=share_reserves_delta * market.market_state.share_price,
        d_bond_asset=bond_reserves_delta,
        d_bond_buffer=-bond_amount,
        short_base_volume=d_base_volume,
        shorts_outstanding=-bond_amount,
        short_average_maturity_time=d_short_average_maturity_time,
        short_checkpoints=d_checkpoints,
        total_supply_shorts=defaultdict(float, {mint_time: -bond_amount}),
        withdraw_capital=withdraw_pool_deltas.withdraw_capital,
        withdraw_interest=withdraw_pool_deltas.withdraw_interest,
        withdraw_shares_ready_to_withdraw=withdraw_pool_deltas.withdraw_shares_ready_to_withdraw,
    )
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=types.Quantity(
            amount=(market.market_state.share_price / open_share_price) * bond_amount + trade_result.user_result.d_base,
            unit=types.TokenType.BASE,
        ),  # see CLOSING SHORT LOGIC above
        shorts={
            mint_time: wallet.Short(
                balance=-bond_amount,
                open_share_price=0,
            )
        },
        fees_paid=trade_result.breakdown.fee,
    )
    return market_deltas, agent_deltas


def calc_open_long(
    wallet_address: int,
    base_amount: float,
    market: hyperdrive_market.Market,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """
    When a trader opens a long, they put up base and are given long tokens. As time passes, an amount of the longs
    proportional to the time that has passed are considered to be “mature” and can be redeemed one-to-one.
    The remaining amount of longs are sold on the internal AMM. The trader doesn’t receive any variable interest
    from their long positions, so the only money they make on closing is from the long maturing and the fixed
    rate changing.

    Parameters
    ----------
    wallet_address: int
        integer address for the agent's wallet
    base_amount: float
        amount in base that the agent wishes to trade

    Returns
    -------
    tuple[MarketDeltas, wallet.Wallet]
        The deltas that should be applied to the market and agent
    """
    if base_amount > market.market_state.bond_reserves * market.spot_price:
        raise AssertionError(
            "ERROR: cannot open a long with more than the available bond resereves, "
            f"but {base_amount=} > {market.market_state.bond_reserves=}."
        )
    # Perform the trade.
    trade_quantity = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
    market.pricing_model.check_input_assertions(
        quantity=trade_quantity,
        market_state=market.market_state,
        time_remaining=market.position_duration,
    )
    trade_result = market.pricing_model.calc_out_given_in(
        in_=trade_quantity,
        market_state=market.market_state,
        time_remaining=market.position_duration,
    )
    market.market_state.gov_fees_accrued += trade_result.breakdown.gov_fee
    # TODO: add assert: if share_price * share_reserves < longs_outstanding then revert,
    # this should be in hyperdrive.check_output_assertions which then calls
    # super().check_output_assertions
    # Make sure the trade is valid
    market.pricing_model.check_output_assertions(trade_result=trade_result)
    # Update accouting for average maturity time, base volume and longs outstanding
    long_average_maturity_time = update_weighted_average(
        average=market.market_state.long_average_maturity_time,
        total_weight=market.market_state.longs_outstanding,
        delta=market.annualized_position_duration,
        delta_weight=-trade_result.market_result.d_bonds,
        is_adding=True,
    )
    d_long_average_maturity_time = long_average_maturity_time - market.market_state.long_average_maturity_time
    # TODO: don't use 1 for time_remaining once we have checkpointing
    base_volume = calculate_base_volume(trade_result.market_result.d_base, base_amount, 1)
    # Get the market and wallet deltas to return.
    market_deltas = MarketDeltas(
        d_base_asset=trade_result.market_result.d_base,
        d_bond_asset=trade_result.market_result.d_bonds,
        d_base_buffer=trade_result.user_result.d_bonds,
        long_base_volume=base_volume,
        longs_outstanding=trade_result.user_result.d_bonds,
        long_average_maturity_time=d_long_average_maturity_time,
        long_checkpoints=defaultdict(float, {market.latest_checkpoint_time: base_volume}),
        total_supply_longs=defaultdict(float, {market.latest_checkpoint_time: trade_result.user_result.d_bonds}),
    )
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=types.Quantity(amount=trade_result.user_result.d_base, unit=types.TokenType.BASE),
        longs={market.latest_checkpoint_time: wallet.Long(trade_result.user_result.d_bonds)},
        fees_paid=trade_result.breakdown.fee,
    )
    return market_deltas, agent_deltas


def calc_close_long(
    wallet_address: int,
    bond_amount: float,
    market: hyperdrive_market.Market,
    mint_time: float,
    is_trade: bool = True,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """Calculations for closing a long position.
    This function takes the trade spec & turn it into trade details.

    Parameters
    ---------
    wallet_address: int
        The address of the agent's wallet.
    bond_amount: float
        The amount of bonds the agent is shorting.
    market: hyperdrive_market.Market
        The market the agent is opening a short on.
    mint_time: float
        The time in years when the short was opened.
    is_trade: bool
        If an agent is performing a trade.  If false, this means a checkpoint is applied in which
        case we do not want to update the pool reserves yet since the agent hasn't actually closed
        their position yet.

    Returns
    -------
    tuple[MarketDeltas, wallet.Wallet]
        Returns the deltas to update the market and the agent's wallet after opening a short.
    """
    # Compute the time remaining given the mint time.
    years_remaining = time.get_years_remaining(
        market_time=market.block_time.time,
        mint_time=mint_time,
        position_duration_years=market.position_duration.days / 365,
    )  # all args in units of years
    time_remaining = time.StretchedTime(
        days=years_remaining * 365,  # converting years to days
        time_stretch=market.position_duration.time_stretch,
        normalizing_constant=market.position_duration.normalizing_constant,
    )
    # Perform the trade.
    trade_quantity = types.Quantity(amount=bond_amount, unit=types.TokenType.PT)
    market.pricing_model.check_input_assertions(
        quantity=trade_quantity,
        market_state=market.market_state,
        time_remaining=time_remaining,
    )
    # if we are applying a checkpoint, we don't update the reserves
    bond_reserves_delta = 0
    share_reserves_delta = 0
    base_proceeds = 0
    fee = 0
    gov_fee = 0
    if is_trade:
        trade_result = market.pricing_model.calc_out_given_in(
            in_=trade_quantity,
            market_state=market.market_state,
            time_remaining=time_remaining,
        )
        market.pricing_model.check_output_assertions(trade_result=trade_result)
        bond_reserves_delta = trade_result.market_result.d_bonds
        share_reserves_delta = trade_result.market_result.d_base / market.market_state.share_price
        base_proceeds = trade_result.user_result.d_base
        fee = trade_result.breakdown.fee
        gov_fee = trade_result.breakdown.gov_fee

    market.market_state.gov_fees_accrued += gov_fee
    # Make sure the trade is valid
    # Update accouting for average maturity time, base volume and longs outstanding
    long_average_maturity_time = update_weighted_average(
        average=market.market_state.long_average_maturity_time,
        total_weight=market.market_state.longs_outstanding,
        delta=market.annualized_position_duration,
        delta_weight=bond_amount,
        is_adding=False,
    )
    d_long_average_maturity_time = long_average_maturity_time - market.market_state.long_average_maturity_time
    d_base_volume, d_checkpoints, lp_margin = calc_checkpoint_deltas(market, mint_time, bond_amount, "long")
    # get the share adjustment amount
    normalized_time_elapsed = (market.block_time.time - mint_time) / market.position_duration.years
    share_proceeds = bond_amount * normalized_time_elapsed / market.market_state.share_price
    maturity_time = mint_time + market.position_duration.years
    close_share_price = (
        market.market_state.share_price
        if market.block_time.time < maturity_time
        else market.market_state.checkpoints[mint_time].share_price
    )
    if market.market_state.init_share_price > close_share_price:
        share_proceeds *= close_share_price / market.market_state.init_share_price
    # The amount of liquidity that needs to be removed.
    share_adjustment = -(share_proceeds - share_reserves_delta)
    margin_needs_to_be_freed = (
        market.market_state.total_supply_withdraw_shares > market.market_state.withdraw_shares_ready_to_withdraw
    )
    withdraw_pool_deltas = MarketDeltas()
    if margin_needs_to_be_freed:
        open_share_price = market.market_state.checkpoints[mint_time].long_share_price
        # The withdrawal pool has preferential access to the proceeds generated from closing longs.
        # The LP proceeds when longs are closed are equivalent to the proceeds of short positions.
        withdrawal_proceeds = calc_short_proceeds(
            bond_amount,
            share_proceeds,
            open_share_price,
            market.market_state.share_price,
            market.market_state.share_price,
        )
        lp_interest = calc_short_interest(
            bond_amount,
            open_share_price,
            market.market_state.share_price,
            market.market_state.share_price,
        )
        capital_freed = 0
        if withdrawal_proceeds > lp_interest:
            capital_freed = withdrawal_proceeds - lp_interest

        # Pay out the withdrawal pool with the freed margin. The withdrawal proceeds are split into
        # the margin pool and the interest pool. The proceeds that are distributed to the margin and
        # interest pools are removed from the pool's liquidity.
        withdraw_pool_deltas = market.calc_free_margin(
            capital_freed,
            # TODO: make sure that the withdrawal shares are actually instantiated with the open
            # share price. Think more about this as it seems weird to have to convert back using an
            # old share price considering that this may not have been the share price at the time
            # the withdrawal was initiated.
            lp_margin / open_share_price,
            lp_interest,
        )
        withdrawal_proceeds = withdraw_pool_deltas.withdraw_capital + withdraw_pool_deltas.withdraw_interest
        share_adjustment -= withdrawal_proceeds
    # Remove the flat component of the trade as well as any LP proceeds paid to the withdrawal pool
    # from the pool's liquidity.
    share_reserves = market.market_state.share_reserves + share_reserves_delta
    bond_reserves = market.market_state.bond_reserves + bond_reserves_delta
    adjusted_share_reserves, adjusted_bond_reserves = calc_update_reserves(
        share_reserves, bond_reserves, share_adjustment
    )
    share_reserves_delta = adjusted_share_reserves - market.market_state.share_reserves
    bond_reserves_delta = adjusted_bond_reserves - market.market_state.bond_reserves
    # Return the market and wallet deltas.
    market_deltas = MarketDeltas(
        d_base_asset=share_reserves_delta * market.market_state.share_price,
        d_bond_asset=bond_reserves_delta,
        d_base_buffer=-bond_amount,
        long_base_volume=d_base_volume,
        longs_outstanding=-bond_amount,
        long_average_maturity_time=d_long_average_maturity_time,
        long_checkpoints=d_checkpoints,
        total_supply_longs=defaultdict(float, {mint_time: -bond_amount}),
        withdraw_capital=withdraw_pool_deltas.withdraw_capital,
        withdraw_interest=withdraw_pool_deltas.withdraw_interest,
        withdraw_shares_ready_to_withdraw=withdraw_pool_deltas.withdraw_shares_ready_to_withdraw,
    )
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=types.Quantity(amount=base_proceeds, unit=types.TokenType.BASE),
        longs={mint_time: wallet.Long(-bond_amount)},
        fees_paid=fee,
    )
    return market_deltas, agent_deltas


def calc_update_reserves(share_reserves: float, bond_reserves: float, share_reserves_delta) -> tuple[float, float]:
    """Calculates updates to the pool's liquidity and holds the pool's APR constant.

    Parameters
    ----------
    share_reserves: float
        The current total shares in reserve
    bond_reserves: float
        The current total bonds in reserve
    share_reserves_delta:
        The delta that should be applied to share reserves.

    Returns
    -------
    tuple[float, float]
        updated_share_reserves and updated_bond_reserves
    """
    if share_reserves_delta == 0:
        return 0, 0
    updated_share_reserves = share_reserves + share_reserves_delta
    updated_bond_reserves = bond_reserves * updated_share_reserves / share_reserves
    return updated_share_reserves, updated_bond_reserves


def calc_short_interest(
    bond_amount: float, open_share_price: float, close_share_price: float, share_price: float
) -> float:
    """Calculates the interest in shares earned by a short position.
    The math for the short's interest in shares is given by:

    .. math::
         interest = ((c1 / c0 - 1) * dy) / c
                  = (((c1 - c0) / c0) * dy) / c
                  = ((c1 - c0) / (c0 * c)) * dy

    In the event that the interest is negative, we mark the interest
    to zero.

    Parameters
    ----------
    bond_amount: float
        The amount of bonds underlying the closed short.
    open_share_price: float
        The share price at the short's open.
    close_share_price: float
        The share price at the short's close.
    share_price: float
        the current share price.

    Returns
    -------
    float
        The short interest in shares.
    """
    share_interest = 0
    if close_share_price > open_share_price:
        share_interest = bond_amount * (close_share_price - open_share_price) / (open_share_price * share_price)
    return share_interest


def calc_short_proceeds(
    bond_amount: float, share_amount: float, open_share_price: float, close_share_price: float, share_price: float
) -> float:
    """Calculates the proceeds in shares of closing a short position.

    This takes into account the trading profits, the interest that was earned by the short, and the
    amount of margin that was released by closing the short. The math for the short's proceeds in
    base is given by:

    .. math::
        proceeds = dy - c * dz + (c1 - c0) * (dy / c0) = dy - c * dz + (c1 / c0) * dy - dy = (c1 / c0) *
        dy - c * dz

    We convert the proceeds to shares by dividing by the current share price. In the event that the
    interest is negative and outweighs the trading profits and margin released, the short's proceeds
    are marked to zero.

    Parameters
    ----------
    bond_amount: float
        The amount of bonds underlying the closed short.
    share_amount:
        The amount of shares that it costs to close the short.
    open_share_price: float
        the share price at the short's open.
    close_share_price: float
        the share price at the short's close.
    share_price: float
        The current share price.

    Returns
    -------
    float
        The short proceeds in shares as share_proceeds.
    """
    share_proceeds = 0
    bond_factor = bond_amount * close_share_price / (open_share_price * share_price)
    if bond_factor > share_amount:
        share_proceeds = bond_factor - share_amount
    return share_proceeds


def calc_add_liquidity(
    wallet_address: int,
    base_in: float,
    market: hyperdrive_market.Market,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """Computes new deltas for bond & share reserves after liquidity is added.

    Parameters
    ----------
    wallet_address : int
        The wallet address for the agent.
    base_in: float
        The amount of base the agent is providing.
    market : hyperdrive_market.Market
        The market the agent is providing liquidity for.

    Returns
    -------
    tuple[MarketDeltas, wallet.Wallet]
        Returns the deltas to update the market and the agent's wallet after providing liquidity.
    """
    # get_rate assumes that there is some amount of reserves, and will throw an error if share_reserves is zero
    if (
        market.market_state.share_reserves == 0 and market.market_state.bond_reserves == 0
    ):  # pool has not been initialized
        rate = 0
    else:
        rate = market.fixed_apr
    # sanity check inputs
    market.pricing_model.check_input_assertions(
        quantity=types.Quantity(
            amount=base_in, unit=types.TokenType.PT
        ),  # temporary Quantity object just for this check
        market_state=market.market_state,
        time_remaining=market.position_duration,
    )
    # perform the trade
    lp_out, d_base_reserves, d_bond_reserves = calc_lp_out_given_tokens_in(
        base_in=base_in,
        rate=rate,
        market_state=market.market_state,
        market_time=market.block_time.time,
        position_duration=market.position_duration,
    )
    market_deltas = MarketDeltas(
        d_base_asset=d_base_reserves,
        d_bond_asset=d_bond_reserves,
        d_lp_total_supply=lp_out,
    )
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=-types.Quantity(amount=d_base_reserves, unit=types.TokenType.BASE),
        lp_tokens=lp_out,
    )
    return market_deltas, agent_deltas


def calc_remove_liquidity(
    wallet_address: int,
    lp_shares: float,
    market: hyperdrive_market.Market,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """Computes new deltas for bond & share reserves after liquidity is removed.

    Parameters
    ----------
    wallet_address : int
        The wallet address for the agent.
    lp_shares: float
        The amount of lp_shares the agent is redeeming.
    market : hyperdrive_market.Market
        The market the agent is removing liquidity from.

    Returns
    -------
    tuple[MarketDeltas, wallet.Wallet]
        Returns the deltas to update the market and the agent's wallet after removing liquidity.
    """
    # sanity check inputs
    market.pricing_model.check_input_assertions(
        quantity=types.Quantity(
            amount=lp_shares, unit=types.TokenType.LP_SHARE
        ),  # temporary Quantity object just for this check
        market_state=market.market_state,
        time_remaining=market.position_duration,
    )
    # perform the trade
    delta_shares, delta_bonds = market.pricing_model.calc_tokens_out_given_lp_in(
        lp_in=lp_shares,
        market_state=market.market_state,
    )
    delta_base = market.market_state.share_price * delta_shares
    # calculate withdraw shares for the user
    user_margin = market.market_state.longs_outstanding - market.market_state.long_base_volume
    user_margin += market.market_state.short_base_volume
    user_margin -= (
        market.market_state.total_supply_withdraw_shares - market.market_state.withdraw_shares_ready_to_withdraw
    )
    user_margin = user_margin * lp_shares / market.market_state.lp_total_supply
    withdraw_shares = user_margin / market.market_state.share_price
    # create and return the deltas
    market_deltas = MarketDeltas(
        d_base_asset=-delta_base,
        d_bond_asset=-delta_bonds,
        d_lp_total_supply=-lp_shares,
        total_supply_withdraw_shares=withdraw_shares,
    )
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=types.Quantity(amount=delta_base, unit=types.TokenType.BASE),
        lp_tokens=-lp_shares,
        withdraw_shares=withdraw_shares,
    )
    return market_deltas, agent_deltas

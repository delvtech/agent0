"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations  # types will be strings by default in 3.11
from decimal import Decimal

from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
from typing import TYPE_CHECKING, Optional, Literal

import elfpy.agents.wallet as wallet
import elfpy.markets.base as base_market
import elfpy.time as time
import elfpy.types as types

if TYPE_CHECKING:
    import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market


# TODO: clean up to avoid these
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals


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
    d_base_asset: Decimal = field(default=Decimal(0))
    d_bond_asset: Decimal = field(default=Decimal(0))
    d_base_buffer: Decimal = field(default=Decimal(0))
    d_bond_buffer: float = 0
    d_lp_total_supply: Decimal = field(default=Decimal(0))
    d_share_price: Decimal = field(default=Decimal(0))
    longs_outstanding: Decimal = field(default=Decimal(0))
    shorts_outstanding: Decimal = field(default=Decimal(0))
    long_average_maturity_time: Decimal = field(default=Decimal(0))
    short_average_maturity_time: Decimal = field(default=Decimal(0))
    long_base_volume: Decimal = field(default=Decimal(0))
    short_base_volume: Decimal = field(default=Decimal(0))
    long_withdrawal_shares_outstanding: float = 0
    short_withdrawal_shares_outstanding: float = 0
    long_withdrawal_share_proceeds: float = 0
    short_withdrawal_share_proceeds: float = 0
    long_checkpoints: defaultdict[Decimal, Decimal] = field(default_factory=lambda: defaultdict(Decimal))
    short_checkpoints: defaultdict[Decimal, Decimal] = field(default_factory=lambda: defaultdict(Decimal))
    total_supply_longs: defaultdict[Decimal, Decimal] = field(default_factory=lambda: defaultdict(Decimal))
    total_supply_shorts: defaultdict[Decimal, Decimal] = field(default_factory=lambda: defaultdict(Decimal))


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketActionResult(base_market.MarketActionResult):
    r"""The result to a market of performing a trade"""
    d_base: Decimal
    d_bonds: Decimal


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class MarketAction(base_market.MarketAction):
    r"""Market action specification"""
    # these two variables are required to be set by the strategy
    action_type: MarketActionType
    # amount to supply for the action
    trade_amount: Decimal  # TODO: should this be a Quantity, not a float? Make sure, then delete fixme
    # the agent's wallet
    wallet: wallet.Wallet
    # min amount to receive for the action
    min_amount_out: Decimal = Decimal(0)
    # mint time is set only for trades that act on existing positions (close long or close short)
    mint_time: Optional[Decimal] = None


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


def calc_open_short(
    wallet_address: int,
    bond_amount: Decimal,
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
    """
    # perform the trade
    trade_quantity = types.Quantity(amount=bond_amount, unit=types.TokenType.PT)
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
    # return the market and wallet deltas
    market_deltas = MarketDeltas(
        d_base_asset=trade_result.market_result.d_base,
        d_bond_asset=trade_result.market_result.d_bonds,
        d_bond_buffer=bond_amount,
        short_base_volume=base_volume,
        shorts_outstanding=bond_amount,
        short_average_maturity_time=d_short_average_maturity_time,
        short_checkpoints=defaultdict(float, {market.latest_checkpoint_time: base_volume}),
        total_supply_shorts=defaultdict(float, {market.latest_checkpoint_time: bond_amount}),
    )
    # amount to cover the worst case scenario where p=1. this amount is 1-p. see logic above.
    max_loss = bond_amount - trade_result.user_result.d_base
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=-types.Quantity(amount=max_loss, unit=types.TokenType.BASE),
        shorts={
            market.block_time.time: wallet.Short(balance=bond_amount, open_share_price=market.market_state.share_price)
        },
        fees_paid=trade_result.breakdown.fee,
    )
    return market_deltas, agent_deltas


def calc_close_short(
    wallet_address: int,
    bond_amount: float,
    market: hyperdrive_market.Market,
    mint_time: Decimal,
    open_share_price: float,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """
    when closing a short, the number of bonds being closed out, at face value, give us the total margin returned
    the worst case scenario of the short is reduced by that amount, so they no longer need margin for it
    at the same time, margin in their account is drained to pay for the bonds being bought back
    so the amount returned to their wallet is trade_amount minus the cost of buying back the bonds
    that is, d_base = trade_amount (# of bonds) + trade_result.user_result.d_base (a negative amount, in base))
    for more on short accounting, see the open short method
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
    # TODO: add accounting for withdrawal shares
    # Return the market and wallet deltas.
    d_base_volume, d_checkpoints = calc_checkpoint_deltas(market, mint_time, bond_amount, "short")
    market_deltas = MarketDeltas(
        d_base_asset=trade_result.market_result.d_base,
        d_bond_asset=trade_result.market_result.d_bonds,
        d_bond_buffer=-bond_amount,
        short_base_volume=d_base_volume,
        shorts_outstanding=-bond_amount,
        short_average_maturity_time=d_short_average_maturity_time,
        short_checkpoints=d_checkpoints,
        total_supply_shorts=defaultdict(float, {mint_time: -bond_amount}),
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

    Arguments
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
    # TODO: add accounting for withdrawal shares
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
    mint_time: Decimal,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """Calculations for closing a long position.
    This function takes the trade spec & turn it into trade details.
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
    trade_result = market.pricing_model.calc_out_given_in(
        in_=trade_quantity,
        market_state=market.market_state,
        time_remaining=time_remaining,
    )
    # Make sure the trade is valid
    market.pricing_model.check_output_assertions(trade_result=trade_result)
    # Update accouting for average maturity time, base volume and longs outstanding
    long_average_maturity_time = update_weighted_average(
        average=market.market_state.long_average_maturity_time,
        total_weight=market.market_state.longs_outstanding,
        delta=market.annualized_position_duration,
        delta_weight=bond_amount,
        is_adding=False,
    )
    d_long_average_maturity_time = long_average_maturity_time - market.market_state.long_average_maturity_time
    d_base_volume, d_checkpoints = calc_checkpoint_deltas(market, mint_time, bond_amount, "long")
    # TODO: add accounting for withdrawal shares
    # Return the market and wallet deltas.
    market_deltas = MarketDeltas(
        d_base_asset=trade_result.market_result.d_base,
        d_bond_asset=trade_result.market_result.d_bonds,
        d_base_buffer=-bond_amount,
        long_base_volume=d_base_volume,
        longs_outstanding=-bond_amount,
        long_average_maturity_time=d_long_average_maturity_time,
        long_checkpoints=d_checkpoints,
        total_supply_longs=defaultdict(float, {mint_time: -bond_amount}),
    )
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=types.Quantity(amount=trade_result.user_result.d_base, unit=types.TokenType.BASE),
        longs={mint_time: wallet.Long(trade_result.user_result.d_bonds)},
        fees_paid=trade_result.breakdown.fee,
    )
    return market_deltas, agent_deltas


def calc_add_liquidity(
    wallet_address: int,
    bond_amount: float,
    market: hyperdrive_market.Market,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """Computes new deltas for bond & share reserves after liquidity is added"""
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
            amount=bond_amount, unit=types.TokenType.PT
        ),  # temporary Quantity object just for this check
        market_state=market.market_state,
        time_remaining=market.position_duration,
    )
    # perform the trade
    lp_out, d_base_reserves, d_bond_reserves = calc_lp_out_given_tokens_in(
        d_base=bond_amount,
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
    bond_amount: float,
    market: hyperdrive_market.Market,
) -> tuple[MarketDeltas, wallet.Wallet]:
    """Computes new deltas for bond & share reserves after liquidity is removed"""
    # sanity check inputs
    market.pricing_model.check_input_assertions(
        quantity=types.Quantity(
            amount=bond_amount, unit=types.TokenType.PT
        ),  # temporary Quantity object just for this check
        market_state=market.market_state,
        time_remaining=market.position_duration,
    )
    # perform the trade
    lp_in, d_base, d_bond = market.pricing_model.calc_tokens_out_given_lp_in(
        lp_in=bond_amount,
        rate=market.fixed_apr,
        market_state=market.market_state,
        time_remaining=market.position_duration,
    )
    market_deltas = MarketDeltas(
        d_base_asset=-d_base,
        d_bond_asset=-d_bond,
        d_lp_total_supply=-lp_in,
    )
    agent_deltas = wallet.Wallet(
        address=wallet_address,
        balance=types.Quantity(amount=d_base, unit=types.TokenType.BASE),
        lp_tokens=-lp_in,
    )
    return market_deltas, agent_deltas


def calculate_short_adjustment(
    market_state: hyperdrive_market.MarketState,
    position_duration: time.StretchedTime,
    market_time: Decimal,
) -> Decimal:
    """Calculates an adjustment amount for lp shares"""
    if market_time > market_state.short_average_maturity_time:
        return Decimal(0)
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
    market_time: Decimal,
) -> Decimal:
    """Calculates an adjustment amount for lp shares"""
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


def calculate_lp_allocation_adjustment(
    positions_outstanding: Decimal,
    base_volume: Decimal,
    average_time_remaining: Decimal,
    share_price: Decimal,
) -> Decimal:
    """Calculates an adjustment amount for lp shares"""
    # base_adjustment = t * base_volume + (1 - t) * _positions_outstanding
    base_adjustment = (average_time_remaining * base_volume) + (1 - average_time_remaining) * positions_outstanding
    # adjustment = base_adjustment / c
    return base_adjustment / share_price


def calculate_base_volume(base_amount: Decimal, bond_amount: Decimal, normalized_time_remaining: Decimal) -> Decimal:
    """Calculates the base volume of an open trade.
    Output is given the base amount, the bond amount, and the time remaining.
    Since the base amount takes into account backdating, we can't use this as our base volume.
    Since we linearly interpolate between the base volume and the bond amount as the time
    remaining goes from 1 to 0, the base volume can be determined as follows:

        base_amount = t * base_volume + (1 - t) * bond_amount
                            =>
        base_volume = (base_amount - (1 - t) * bond_amount) / t
    """
    # If the time remaining is 0, the position has already matured and doesn't have an impact on
    # LP's ability to withdraw. This is a pathological case that should never arise.
    if normalized_time_remaining == 0:
        return Decimal(0)
    return (base_amount - (1 - normalized_time_remaining) * bond_amount) / normalized_time_remaining


def update_weighted_average(  # pylint: disable=too-many-arguments
    average: Decimal,
    total_weight: Decimal,
    delta: Decimal,
    delta_weight: Decimal,
    is_adding: bool,
) -> Decimal:
    """Updates a weighted average by adding or removing a weighted delta."""
    if is_adding:
        return (total_weight * average + delta_weight * delta) / (total_weight + delta_weight)
    if total_weight == delta_weight:
        return Decimal(0)
    return (total_weight * average - delta_weight * delta) / (total_weight - delta_weight)


def calc_lp_out_given_tokens_in(
    d_base: Decimal,
    rate: Decimal,
    market_state: hyperdrive_market.MarketState,
    market_time: Decimal,
    position_duration: time.StretchedTime,
) -> tuple[Decimal, Decimal, Decimal]:
    r"""Computes the amount of LP tokens to be minted for a given amount of base asset

    .. math::
        \Delta l = \frac{(l \cdot \Delta z)(z + a_s - a_l)}

    where a_s and a_l are the short and long adjustments. In order to calculate these we need to
    keep track of the long and short base volumes, amounts outstanding and average maturity
    times.
    """
    d_shares = d_base / market_state.share_price
    annualized_time = time.norm_days(position_duration.days, 365)
    d_bonds = (market_state.share_reserves + d_shares) / 2 * (
        market_state.init_share_price * (1 + rate * annualized_time) ** (1 / position_duration.stretched_time)
        - market_state.share_price
    ) - market_state.bond_reserves
    if market_state.share_reserves > 0:  # normal case where we have some share reserves
        short_adjustment = calculate_short_adjustment(market_state, position_duration, market_time)
        long_adjustment = calculate_long_adjustment(market_state, position_duration, market_time)
        lp_out = (d_shares * market_state.lp_total_supply) / (
            market_state.share_reserves + short_adjustment - long_adjustment
        )
    else:  # initial case where we have 0 share reserves or final case where it has been removed
        lp_out = d_shares
    return lp_out, d_base, d_bonds


def calc_checkpoint_deltas(
    market: hyperdrive_market.Market, checkpoint_time: float, bond_amount: float, position: Literal["short", "long"]
) -> tuple[float, defaultdict[float, float]]:
    """Compute deltas to close any outstanding positions at the checkpoint_time

    Parameters
    ----------
    market: hyperdrive_market.Market
        Deltas are computed for this market.
    checkpoint_time: float
        The checkpoint time to be used for updating.
    bond_amount: float
        The amount of bonds used to close the position.
    position: str
        Either "short" or "long", indicating what type of position is being closed.

    Returns
    -------
    d_base_volume: float
        The change in base volume for the given position.
    d_checkpoints: defaultdict[float, float]
        The change in checkpoint volume for the given checkpoint_time (key) and position (value).
    """
    total_supply = "total_supply_shorts" if position == "short" else "total_supply_longs"
    base_volume = "short_base_volume" if position == "short" else "long_base_volume"
    # Get the total supply of positions in the checkpoint.
    checkpoint_amount = market.market_state[total_supply][checkpoint_time]
    # If the checkpoint has nothing stored, then do not update
    if checkpoint_amount == 0:
        return (0, defaultdict(float, {checkpoint_time: 0}))
    # If all of the positions in the checkpoint are being closed, delete the base volume in the
    # checkpoint and reduce the aggregates by the checkpoint amount. Otherwise, decrease the
    # both the checkpoints and aggregates by a proportional amount.
    if bond_amount == checkpoint_amount:
        d_base_volume = -market.market_state.checkpoints[checkpoint_time][base_volume]
    else:
        d_base_volume = -float(
            market.market_state.checkpoints[checkpoint_time][base_volume] * (bond_amount / checkpoint_amount)
        )
    d_checkpoints = defaultdict(float, {checkpoint_time: d_base_volume})
    return (d_base_volume, d_checkpoints)

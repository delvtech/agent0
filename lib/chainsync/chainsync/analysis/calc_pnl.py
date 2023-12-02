"""Calculates the pnl."""
from __future__ import annotations

import logging
from decimal import Decimal
from ethpy.hyperdrive.interface import HyperdriveInterface
from ethpy.hyperdrive.state.pool_state import PoolState

import pandas as pd
from ethpy.hyperdrive import BASE_TOKEN_SYMBOL
from fixedpointmath import FixedPoint
from web3.contract.contract import Contract


def calculate_close_long_flat_plus_curve(
    amount_bonds: FixedPoint,
    normalized_time_remaining: FixedPoint,
    interface: HyperdriveInterface,
    pool_state: PoolState | None = None,
) -> FixedPoint:
    """Calculate the shares received for a given amount of bonds, after fees.

    Arguments
    ---------
    amount_bonds: FixedPoint
        The amount of bonds to be exchanged.
    normalized_time_remaining: FixedPoint
        Time to maturity, normalized to 1.
    interface: HyperdriveInterface
        The Hyperdrive API interface object.
    pool_state: PoolState, optional
        The hyperdrive pool state.

    Returns
    -------
    FixedPoint
        The shares received for a given amount of bonds, after fees.
    """
    if pool_state is None:
        pool_state = interface.current_pool_state
    curve_part_shares_after_fees = 0
    if normalized_time_remaining > FixedPoint(0):
        curve_part_bonds = amount_bonds * normalized_time_remaining
        curve_part_shares = interface.calc_shares_out_given_bonds_in_down(abs(curve_part_bonds), pool_state)
        price_discount = FixedPoint(1) - interface.calc_spot_price(pool_state)
        curve_part_fees = curve_part_shares * price_discount * pool_state.pool_config.fees.curve
        curve_part_shares_after_fees = curve_part_shares - curve_part_fees
    flat_part_shares = amount_bonds * (FixedPoint(1) - normalized_time_remaining) / pool_state.pool_info.share_price
    flat_part_fees = flat_part_shares * pool_state.pool_config.fees.flat
    flat_part_shares_after_fees = flat_part_shares - flat_part_fees
    return curve_part_shares_after_fees + flat_part_shares_after_fees


def calculate_close_short_flat_plus_curve(
    amount_bonds: FixedPoint,
    normalized_time_remaining: FixedPoint,
    interface: HyperdriveInterface,
    pool_state: PoolState | None = None,
) -> FixedPoint:
    """Calculate the shares received for a given amount of bonds, after fees.

    Arguments
    ---------
    amount_bonds: FixedPoint
        The amount of bonds to be exchanged.
    normalized_time_remaining: FixedPoint
        Time to maturity, normalized to 1.
    interface: HyperdriveInterface
        The Hyperdrive API interface object.
    pool_state: PoolState, optional
        The hyperdrive pool state.

    Returns
    -------
    FixedPoint
        The shares received for a given amount of bonds, after fees.
    """
    if pool_state is None:
        pool_state = interface.current_pool_state
    curve_part_shares_after_fees = 0
    if normalized_time_remaining > FixedPoint(0):
        curve_part_bonds = amount_bonds * normalized_time_remaining
        curve_part_shares = interface.calc_shares_in_given_bonds_out_up(abs(curve_part_bonds), pool_state)
        price_discount = FixedPoint(1) - interface.calc_spot_price(pool_state)
        curve_part_fees = curve_part_shares * price_discount * pool_state.pool_config.fees.curve
        curve_part_shares_after_fees = curve_part_shares - curve_part_fees
    flat_part_shares = amount_bonds * (FixedPoint(1) - normalized_time_remaining) / pool_state.pool_info.share_price
    flat_part_fees = flat_part_shares * pool_state.pool_config.fees.flat
    flat_part_shares_after_fees = flat_part_shares - flat_part_fees
    return curve_part_shares_after_fees + flat_part_shares_after_fees


def calculate_short_proceeds(bond_amount, share_amount, open_share_price, share_price, flat_fee):
    """Calculate the share proceeds of closing a short position, in base.

    proceeds = (c1 / c0 + flat_fee) * dy - c * dz
             = (share_price / open_share_price + flat_fee) * bond_amount - share_price * share_amount

    Arguments
    ---------
    bond_amount: int
        The amount of bonds to be exchanged.
    share_amount: int
        The amount of shares to be exchanged.
    open_share_price: int
        The open share price.
    share_price: int
        The share price.
    flat_fee: int
        The flat fee.

    Returns
    -------
    int
        The share proceeds of closing a short position, in base.
    """
    return (share_price / open_share_price + flat_fee) * bond_amount - share_price * share_amount


def calc_single_closeout(position: pd.Series, interface: HyperdriveInterface, checkpoint_info: pd.DataFrame) -> Decimal:
    # sourcery skip: extract-duplicate-method, extract-method, inline-immediately-returned-variable, move-assign-in-block, remove-redundant-if, split-or-ifs, switch
    """Calculate the closeout pnl for a single position.

    Arguments
    ---------
    position: pd.DataFrame
        The position to calculate the closeout pnl for (one row in current_wallet)
    interface: HyperdriveInterface
        The Hyperdrive API interface object
    checkpoint_info: pd.DataFrame
        A dataframe containing information about each checkpoint.

    Returns
    -------
    Decimal
        The closeout pnl
    """
    # pnl is itself
    if position["base_token_type"] == BASE_TOKEN_SYMBOL:
        return position["value"]
    # If no value, pnl is 0
    if position["value"] == 0:
        return Decimal(0)
    assert len(position.shape) == 1, "Only one position at a time"
    amount = FixedPoint(f"{position['value']:f}")
    # amount = position['value']
    tokentype = position["base_token_type"]
    assert isinstance(tokentype, str)
    out_pnl = Decimal("nan")
    if tokentype in ["LONG", "SHORT"]:
        maturity = position["maturity_time"]
        assert isinstance(maturity, Decimal)
        maturity = int(maturity)
        assert isinstance(maturity, int)
        normalized_time_remaining = (
            maturity - interface.current_pool_state.block_time
        ) / interface.current_pool_state.pool_config.position_duration
        share_price = interface.current_pool_state.pool_info.share_price
        if tokentype == "LONG":
            out_pnl = (
                calculate_close_long_flat_plus_curve(amount, FixedPoint(normalized_time_remaining), interface)
                * share_price
            )
            out_pnl = Decimal(out_pnl.scaled_value) / Decimal(1e18)
        elif tokentype == "SHORT":
            share_reserves_delta = (
                calculate_close_short_flat_plus_curve(amount, FixedPoint(normalized_time_remaining), interface)
                * share_price
            )
            mint_time = maturity - interface.current_pool_state.pool_config.position_duration
            checkpoint_timestamps = checkpoint_info.timestamp.astype("int64") / 1e9
            checkpoints = checkpoint_timestamps - (
                checkpoint_timestamps % interface.current_pool_state.pool_config.checkpoint_duration
            )
            checkpoints = checkpoints.astype("int64")
            open_share_price = checkpoint_info.loc[
                (checkpoints == mint_time) & (checkpoint_info.share_price != 0), "share_price"
            ].values[0]
            print(f"{open_share_price=}")
            assert isinstance(open_share_price, Decimal)
            out_pnl = calculate_short_proceeds(
                amount,
                share_reserves_delta,
                open_share_price,
                share_price,
                interface.current_pool_state.pool_config.fees.flat,
            )
            out_pnl = Decimal(out_pnl.scaled_value) / Decimal(1e18)
    elif tokentype in ["LP", "WITHDRAWAL_SHARE"]:
        out_pnl = amount * interface.current_pool_state.pool_info.lp_share_price
        out_pnl = Decimal(out_pnl.scaled_value) / Decimal(1e18)
    else:
        # Should never get here
        raise ValueError(f"Unexpected token type: {tokentype}")
    return out_pnl


def calc_closeout_pnl(
    current_wallet: pd.DataFrame,
    checkpoint_info: pd.DataFrame,
    hyperdrive_contract: Contract,
    hyperdrive_interface: HyperdriveInterface,
) -> pd.DataFrame:
    """Calculate closeout value of agent positions.

    Arguments
    ---------
    current_wallet: pd.DataFrame
        A dataframe resulting from `get_current_wallet` that describes the current wallet position.
    checkpoint_info: pd.DataFrame
        A dataframe containing information about each checkpoint.
    hyperdrive_contract: Contract
        The hyperdrive contract object.
    hyperdrive_interface: HyperdriveInterface
        The Hyperdrive interface object.

    Returns
    -------
    pd.DataFrame
        The closeout pnl
    """
    # Define a function to handle the calculation for each group
    out_pnl = current_wallet.apply(
        calc_single_closeout,  # type: ignore
        interface=hyperdrive_interface,
        checkpoint_info=checkpoint_info,
        axis=1,
    )

    return out_pnl


def calc_spot_pnl(current_wallet: pd.DataFrame, pool_info: pd.DataFrame, pool_config: pd.DataFrame) -> pd.Series:
    """Calculate spot price value of agent positions.

    Calculate_spot_price_for_position calculates the spot price for a position that has matured by some amount.

    Arguments
    ---------
    current_wallet: pd.DataFrame
        A dataframe resulting from `get_current_wallet` that describes the current wallet position.
    pool_info : pd.DataFrame
        Pool information like reserves. This can contain multiple blocks, but only the most recent is used.
    pool_config : pd.Series
        Time-invariant pool configuration.

    Returns
    -------
    pd.Series
        Calculated pnl for each row in current_wallet.
    """
    # pylint: disable=too-many-locals
    # Most current block timestamp
    latest_pool_info = pool_info.loc[pool_info.index.max()]
    block_timestamp = Decimal(latest_pool_info["timestamp"].timestamp())

    # Sanity check, no tokens except base should dip below 0
    assert (current_wallet["value"][current_wallet["base_token_type"] != "WETH"] >= 0).all()

    # Calculate for base
    # Base is valued at 1:1, since that's our numéraire (https://en.wikipedia.org/wiki/Num%C3%A9raire)
    wallet_base = current_wallet[current_wallet["base_token_type"] == "WETH"]
    base_returns = wallet_base["value"]

    # Calculate for lp
    # LP value = users_LP_tokens * share_price
    # derived from:
    #   total_lp_value = lp_total_supply * share_price
    #   share_of_pool = users_LP_tokens / lp_total_supply
    #   users_LP_value = share_of_pool * total_lp_value
    #   users_LP_value = users_LP_tokens / lp_total_supply * lp_total_supply * share_price
    #   users_LP_value = users_LP_tokens * share_price
    wallet_lps = current_wallet[current_wallet["base_token_type"] == "LP"]
    lp_returns = wallet_lps["value"] * latest_pool_info["share_price"]

    # Calculate for withdrawal shares. Same as for LPs.
    wallet_withdrawal = current_wallet[current_wallet["base_token_type"] == "WITHDRAWAL_SHARE"]
    withdrawal_returns = wallet_withdrawal["value"] * latest_pool_info["share_price"]

    # Calculate for shorts
    # Short value = users_shorts * ( 1 - spot_price )
    # this could also be valued at 1 + ( p1 - p2 ) but we'd have to know their entry price (or entry base 🤔)
    # TODO shorts inflate the pnl calculation. When opening a short, the "amount spent" is
    # how much base is put up for collateral, but the amount of short shares are being calculated at some price
    # This really should be, how much base do I get back if I close this short right now
    wallet_shorts = current_wallet[current_wallet["base_token_type"] == "SHORT"]
    short_spot_prices = calculate_spot_price_for_position(
        share_reserves=latest_pool_info["share_reserves"],
        share_adjustment=latest_pool_info["share_adjustment"],
        bond_reserves=latest_pool_info["bond_reserves"],
        time_stretch=pool_config["time_stretch"],
        initial_share_price=pool_config["initial_share_price"],
        position_duration=pool_config["position_duration"],
        maturity_timestamp=wallet_shorts["maturity_time"],
        block_timestamp=block_timestamp,
    )
    shorts_returns = wallet_shorts["value"] * (1 - short_spot_prices)

    # Calculate for longs
    # Long value = users_longs * spot_price
    wallet_longs = current_wallet[current_wallet["base_token_type"] == "LONG"]
    long_spot_prices = calculate_spot_price_for_position(
        share_reserves=latest_pool_info["share_reserves"],
        share_adjustment=latest_pool_info["share_adjustment"],
        bond_reserves=latest_pool_info["bond_reserves"],
        time_stretch=pool_config["time_stretch"],
        initial_share_price=pool_config["initial_share_price"],
        position_duration=pool_config["position_duration"],
        maturity_timestamp=wallet_longs["maturity_time"],
        block_timestamp=block_timestamp,
    )
    long_returns = wallet_longs["value"] * long_spot_prices

    # Add pnl to current_wallet information
    # Current_wallet and *_pnl dataframes have the same index
    current_wallet.loc[base_returns.index, "pnl"] = base_returns
    current_wallet.loc[lp_returns.index, "pnl"] = lp_returns
    current_wallet.loc[shorts_returns.index, "pnl"] = shorts_returns
    current_wallet.loc[long_returns.index, "pnl"] = long_returns
    current_wallet.loc[withdrawal_returns.index, "pnl"] = withdrawal_returns
    # return current_wallet.reset_index().groupby("wallet_address")["pnl"].sum(), current_wallet
    return current_wallet["pnl"]


def calculate_spot_price_for_position(
    share_reserves: pd.Series,
    share_adjustment: pd.Series,
    bond_reserves: pd.Series,
    time_stretch: pd.Series,
    initial_share_price: pd.Series,
    position_duration: pd.Series,
    maturity_timestamp: pd.Series,
    block_timestamp: Decimal,
):
    """Calculate the spot price given the pool info data.

    This is calculated in a vectorized way, with every input being a scalar except for maturity_timestamp.

    Arguments
    ---------
    share_reserves : pd.Series
        The share reserves
    share_adjustment : pd.Series
        The adjustment for share reserves
    bond_reserves : pd.Series
        The bond reserves
    time_stretch : pd.Series
        The time stretch
    initial_share_price : pd.Series
        The initial share price
    position_duration : pd.Series
        The position duration
    maturity_timestamp : pd.Series
        The maturity timestamp
    block_timestamp : Decimal
        The block timestamp

    Returns
    -------
    pd.Series
        The spot price relevant to each position.
    """
    # pylint: disable=too-many-arguments
    full_term_spot_price = ((initial_share_price * (share_reserves - share_adjustment)) / bond_reserves) ** time_stretch
    time_left_seconds = maturity_timestamp - block_timestamp  # type: ignore
    if isinstance(time_left_seconds, pd.Timedelta):
        time_left_seconds = time_left_seconds.total_seconds()
    time_left_in_years = time_left_seconds / position_duration
    logging.info(
        " spot price is weighted average of %s(%s) and 1 (%s)",
        full_term_spot_price,
        time_left_in_years,
        1 - time_left_in_years,
    )
    return full_term_spot_price * time_left_in_years + 1 * (1 - time_left_in_years)

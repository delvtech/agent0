"""Plots the pnl."""
from __future__ import annotations

import logging

import pandas as pd
from extract_data_logs import calculate_spot_price


# TODO fix calculating spot price with position duration
def calculate_spot_price_from_state(state, maturity_timestamp, block_timestamp, config_data):
    """Calculate spot price from reserves stored in a state variable."""
    return calculate_spot_price_for_position(
        state.shareReserves,
        state.bondReserves,
        config_data["invTimeStretch"],
        config_data["initialSharePrice"],
        config_data["positionDuration"],
        maturity_timestamp,
        block_timestamp,
    )


# Old calculate spot price
def calculate_spot_price_for_position(
    share_reserves,
    bond_reserves,
    time_stretch,
    initial_share_price,
    position_duration,
    maturity_timestamp,
    block_timestamp,
):
    """Calculate the spot price given the pool info data."""
    # pylint: disable=too-many-arguments

    # TODO this calculation is broken
    full_term_spot_price = calculate_spot_price(share_reserves, bond_reserves, initial_share_price, time_stretch)

    time_left_seconds = maturity_timestamp - block_timestamp
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


def calculate_current_pnl(pool_config: pd.Series, pool_info: pd.DataFrame, current_wallet: pd.DataFrame) -> pd.Series:
    """Calculates the most current pnl values."""
    # Most current block timestamp
    latest_pool_info = pool_info.loc[pool_info.index.max()]
    block_timestamp = latest_pool_info["timestamp"].timestamp()

    # Calculate for base
    base_pnl = current_wallet[current_wallet["baseTokenType"] == "BASE"]["tokenValue"]

    # Calculate for lp
    wallet_lps = current_wallet[current_wallet["baseTokenType"] == "LP"]
    lp_pnl = wallet_lps["tokenValue"] * latest_pool_info["sharePrice"]

    # Calculate for shorts
    wallet_shorts = current_wallet[current_wallet["baseTokenType"] == "SHORT"]
    short_spot_prices = calculate_spot_price_for_position(
        latest_pool_info["shareReserves"],
        latest_pool_info["bondReserves"],
        pool_config["invTimeStretch"],
        pool_config["initialSharePrice"],
        pool_config["positionDuration"],
        wallet_shorts["maturityTime"],
        block_timestamp,
    )
    shorts_pnl = wallet_shorts["tokenValue"] * (1 - short_spot_prices)

    # Calculate for longs
    wallet_longs = current_wallet[current_wallet["baseTokenType"] == "LONG"]
    long_spot_prices = calculate_spot_price_for_position(
        latest_pool_info["shareReserves"],
        latest_pool_info["bondReserves"],
        pool_config["invTimeStretch"],
        pool_config["initialSharePrice"],
        pool_config["positionDuration"],
        wallet_longs["maturityTime"],
        block_timestamp,
    )
    long_pnl = wallet_longs["tokenValue"] * long_spot_prices

    # Calculate for longs
    wallet_withdrawl = current_wallet[current_wallet["baseTokenType"] == "WITHDRAWL_SHARE"]

    withdrawl_pnl = wallet_withdrawl["tokenValue"] * latest_pool_info.sharePrice

    # Add pnl to current_wallet information
    # Index should match, so it's magic
    current_wallet.loc[base_pnl.index, "pnl"] = base_pnl
    current_wallet.loc[lp_pnl.index, "pnl"] = lp_pnl
    current_wallet.loc[shorts_pnl.index, "pnl"] = shorts_pnl
    current_wallet.loc[long_pnl.index, "pnl"] = long_pnl
    current_wallet.loc[withdrawl_pnl.index, "pnl"] = withdrawl_pnl
    pnl = current_wallet.reset_index().groupby("walletAddress")["pnl"].sum()
    return pnl


# TODO fix calculating pnl
# def calculate_pnl(
#    pool_config: pd.DataFrame,
#    pool_info: pd.DataFrame,
#    checkpoint_info: pd.DataFrame,
#    agent_positions: dict[str, AgentPosition],
# ) -> dict[str, AgentPosition]:
#    """Calculate pnl for all agents.
#
#    Arguments
#    ---------
#    pool_config : PoolConfig
#        Configuration with which the pool was initialized.
#    pool_info : pd.DataFrame
#        Reserves of the pool at each block.
#    checkpoint_info : pd.DataFrame
#    agent_positions :
#        Dict containing each agent's AgentPosition object.
#    """
#    position_duration = pool_config.positionDuration.iloc[0]
#
#    for ap in agent_positions.values():  # pylint: disable=invalid-name
#        for block in ap.positions.index:
#            # We only calculate pnl up to pool_info
#            if block > pool_info.index.max():
#                continue
#            state = pool_info.loc[block]  # current state of the pool
#
#            # get maturity from current checkpoint
#            if block in checkpoint_info.index:
#                current_checkpoint = checkpoint_info.loc[block]
#                maturity = current_checkpoint["timestamp"] + pd.Timedelta(seconds=position_duration)
#            else:
#                # it's unclear to me if not finding a current checkpoint is expected behavior that we should handle.
#                # if we assume this is the first trade of a new checkpoint,
#                # we know the maturity is equal to the current block timestamp plus the position duration.
#                maturity = None
#
#            # calculate spot price of the bond, specific to the current maturity
#            spot_price = calculate_spot_price_from_state(state, maturity, ap.timestamp[block], position_duration)
#
#            # add up the pnl for the agent based on all of their positions.
#            # TODO: vectorize this. also store the vector of pnl per position. in postgres?
#            ap.pnl.loc[block] = 0
#            for position_name in ap.positions.columns:
#                if position_name.startswith("LP"):
#                    # LP value
#                    total_lp_value = state.shareReserves * state.sharePrice
#                    share_of_pool = ap.positions.loc[block, "LP"] / state.lpTotalSupply
#                    ap.pnl.loc[block] += share_of_pool * total_lp_value
#                elif position_name.startswith("LONG"):
#                    # LONG value
#                    ap.pnl.loc[block] += ap.positions.loc[block, position_name] * spot_price
#                elif position_name.startswith("SHORT"):
#                    # SHORT value is calculated as the:
#                    # total amount paid for the position (position * 1)
#                    # remember this payment is comprised of the spot price (p) and the max loss (1-p) set as margin
#                    # minus the closing cost (position * spot_price)
#                    # this means the current position value equals position * (1 - spot_price)
#                    ap.pnl.loc[block] += ap.positions.loc[block, position_name] * (1 - spot_price)
#                elif position_name.startswith("BASE"):
#                    ap.pnl.loc[block] += ap.positions.loc[block, position_name]
#    return agent_positions


# def plot_pnl(agent_positions: dict[str, AgentPosition], axes) -> None:
#    """Plot the pnl data.
#
#    Arguments
#    ---------
#    agent_positions : dict[str, AgentPosition]
#        Dict containing each agent's AgentPosition object.
#    axes : Axes
#    Axes object to plot on.
#    """
#    plot_data = []
#    agents = []
#    for agent, agent_position in agent_positions.items():
#        agents.append(agent)
#        plot_data.append(agent_position.pnl)
#
#    if len(plot_data) > 0:
#        # TODO see if this concat is slowing things down for plotting
#        # Can also plot multiple times
#        plot_data = pd.concat(plot_data, axis=1)
#        plot_data.columns = agents
#    else:
#        plot_data = pd.DataFrame([])
#        agents = []
#
#    # plot everything in one go
#    axes.plot(plot_data.sort_index(), label=agents)
#
#    # change y-axis unit format to #,###.0f
#    # TODO this is making the y axis text very large, fix
#    # axes.yaxis.set_major_formatter(mpl_ticker.FuncFormatter(lambda x, p: format(float(x), ",")))
#
#    # TODO fix these top use axes
#    axes.set_xlabel("block timestamp")
#    axes.set_ylabel("pnl")
#    axes.yaxis.set_label_position("right")
#    axes.yaxis.tick_right()
#    axes.set_title("pnl over time")

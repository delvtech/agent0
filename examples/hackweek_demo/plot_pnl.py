"""Plots the pnl."""
from __future__ import annotations

import pandas as pd
from extract_data_logs import calculate_spot_price_from_state
from matplotlib import ticker as mpl_ticker

from elfpy.data import postgres as pg


def calculate_pnl(
    pool_config: pd.DataFrame,
    pool_info: pd.DataFrame,
    checkpoint_info: pd.DataFrame,
    agent_positions: dict[str, pg.AgentPosition],
) -> dict[str, pg.AgentPosition]:
    """Calculate pnl for all agents.

    Arguments
    ---------
    pool_config : PoolConfig
        Configuration with which the pool was initialized.
    pool_info : pd.DataFrame
        Reserves of the pool at each block.
    checkpoint_info : pd.DataFrame
    Checkpoint information at each block.
    """
    position_duration = pool_config.positionDuration.iloc[0]

    for ap in agent_positions.values():  # pylint: disable=invalid-name
        for block in ap.positions.index:
            state = pool_info.loc[block]  # current state of the pool

            # get maturity from current checkpoint
            if block in checkpoint_info.index:
                current_checkpoint = checkpoint_info.loc[block]
                maturity = current_checkpoint["timestamp"] + pd.Timedelta(seconds=position_duration)
            else:
                # it's unclear to me if not finding a current checkpoint is expected behavior that we should handle.
                # if we assume this is the first trade of a new checkpoint,
                # we know the maturity is equal to the current block timestamp plus the position duration.
                maturity = None

            # calculate spot price of the bond, specific to the current maturity
            spot_price = calculate_spot_price_from_state(state, maturity, ap.timestamp[block], position_duration)

            # add up the pnl for the agent based on all of their positions.
            # TODO: vectorize this. also store the vector of pnl per position. in postgres?
            ap.pnl.loc[block] = 0
            for position_name in ap.positions.columns:
                if position_name.startswith("LP"):
                    # LP value
                    total_lp_value = state.shareReserves * state.sharePrice + state.bondReserves * spot_price
                    share_of_pool = ap.positions.loc[block, "LP"] / state.lpTotalSupply
                    assert share_of_pool < 1, "share_of_pool must be less than 1"
                    ap.pnl.loc[block] += share_of_pool * total_lp_value
                elif position_name.startswith("LONG"):
                    # LONG value
                    ap.pnl.loc[block] += ap.positions.loc[block, position_name] * spot_price
                elif position_name.startswith("SHORT"):
                    # SHORT value is calculated as the:
                    # total amount paid for the position (position * 1)
                    # remember this payment is comprised of the spot price (p) and the max loss (1-p) set as margin
                    # minus the closing cost (position * spot_price)
                    # this means the current position value equals position * (1 - spot_price)
                    ap.pnl.loc[block] += ap.positions.loc[block, position_name] * (1 - spot_price)
                elif position_name.startswith("BASE"):
                    ap.pnl.loc[block] += ap.positions.loc[block, position_name]
    return agent_positions


def plot_pnl(agent_positions: dict[str, pg.AgentPosition], axes):
    """Plot the pnl data."""
    first_agent = list(agent_positions.keys())[0]
    first_ap = agent_positions[first_agent]

    # pre-allocate plot_data block of maximum size, 1 row for each block, 1 column for each agent
    plot_data = pd.DataFrame(pd.NA, index=first_ap.pnl.index, columns=list(agent_positions.keys()))
    for agent, agent_position in agent_positions.items():
        # insert agent's pnl into the plot_data block
        plot_data.loc[agent_position.pnl.index, agent] = agent_position.pnl

    # plot everything in one go
    axes.plot(plot_data)

    # change y-axis unit format to #,###.0f
    axes.yaxis.set_major_formatter(mpl_ticker.FuncFormatter(lambda x, p: format(int(x), ",")))

    # TODO fix these top use axes
    axes.set_xlabel("block timestamp")
    axes.set_ylabel("pnl")
    axes.yaxis.set_label_position("right")
    axes.yaxis.tick_right()
    axes.set_title("pnl over time")

    axes.legend()

    # %%

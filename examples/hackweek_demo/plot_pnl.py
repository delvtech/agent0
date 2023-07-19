"""Plots the pnl."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from extract_data_logs import calculate_spot_price_from_state
from matplotlib import ticker as mpl_ticker
from sqlalchemy.orm import Session

from elfpy.data import postgres as pg


@dataclass
class AgentPosition:
    """Details what the agent holds, how it's changed over time, and how much it's worth.

    Notes
    -----
    At a high level "position" refers to the entire portfolio of holdings.
    The portfolio is comprised of multiple positions, built up through multiple trades over time.
    - At most, the agent can have positions equal to the number of checkpoints (trades within a checkpoint are fungible)
    - DataFrames are [blocks, positions] in shape, for convenience and vectorization
    - Series are [blocks] in shape

    Examples
    --------
    To create an agent position you only need to pass in the wallet, from `pg.get_wallet_info_history(session)`:

    >>> agent_position = AgentPosition(pg.get_wallet_info_history(session))

    Use the same index across multiple tables:
    >>> block = 69
    >>> position = 3
    >>> position_name = agent_position.positions.columns[position]
    >>> holding = agent_position.positions.loc[block, position]
    >>> open_share_price = agent_position.open_share_price.loc[block, position]
    >>> pnl = agent_position.pnl.loc[block, position]
    >>> print(f"agent holds {holding} bonds in {position_name} at block {block} worth {pnl}"})
    agent holds  55.55555556 bonds in LONG-20240715 at block 69 worth 50

    Attributes
    ----------
    positions : pd.DataFrame
        The agent's holding of a single position, in bonds (# of longs or shorts).
    deltas : pd.DataFrame
        Change in each position, from the previous block.
    open_share_price : pd.DataFrame
        Weighted average open share price of each position
    pnl : pd.Series
        Value of the agent's positions.
    share_price : pd.Series
        Share price at the time of the current block.
    timestamp : pd.Series
        Timestamp of the current block.
    """

    positions: pd.DataFrame
    deltas: pd.DataFrame
    open_share_price: pd.DataFrame
    share_price: pd.Series
    timestamp: pd.Series
    pnl: pd.Series = field(default_factory=pd.Series)
    share_price: pd.Series = field(default_factory=pd.Series)
    timestamp: pd.Series = field(default_factory=pd.Series)

    def __init__(self, wallet_history: pd.DataFrame):
        """Calculate multiple relevant historical breakdowns of an agent's position."""
        # Prepare PNL Series filled with NaNs, in the shape of [blocks]
        self.pnl = pd.Series(data=pd.NA, index=wallet_history.index)

        # Scrap the wallet history for parts. First we extract the share price and timestamp.
        self.share_price = wallet_history["sharePrice"]
        self.timestamp = wallet_history["timestamp"]
        # Then we keep track of every other column, to extract them into other tables.
        other_columns = [col for col in wallet_history.columns if col not in ["sharePrice", "timestamp"]]

        # Create positions dataframe which tracks aggregate holdings.
        self.positions = wallet_history.loc[:, other_columns].copy()
        # keep positions where they are not 0, otherwise replace 0 with NaN
        self.positions = self.positions.where(self.positions != 0, pd.NA)

        # Create deltas dataframe which tracks change in holdings.
        self.deltas = self.positions.diff()
        # After the diff() call above, the first row of the deltas table will be NaN.
        # Replace them with the first row of the positions table, effectively capturing a delta from 0.
        self.deltas.iloc[0] = self.positions.iloc[0]

        # Prepare tables filled with NaNs, in the shape of [blocks, positions]
        share_price_on_increases = pd.DataFrame(data=pd.NA, index=self.deltas.index, columns=self.deltas.columns)
        self.open_share_price = pd.DataFrame(data=pd.NA, index=self.deltas.index, columns=self.deltas.columns)

        # When we have an increase in position, we use the current block's share_price
        share_price_on_increases = share_price_on_increases.where(self.deltas <= 0, self.share_price, axis=0)

        # Fill forward to replace NaNs. Table is now full of share prices, sourced only from increases in position.
        share_price_on_increases.fillna(method="ffill", inplace=True, axis=0)

        # Calculate weighted average share price across all deltas (couldn't figure out how to do this vector-wise).
        # vectorised attempt: ap.open_share_price = (share_price_on_increases * deltas).cumsum(axis=0) / positions
        # First row of weighted average open share price is equal to the share
        # price on increases since there's nothing to weight.
        self.open_share_price.iloc[0] = share_price_on_increases.iloc[0]

        # Now we loop across the remaining rows, updated the weighted averages for positions that change.
        for row in self.deltas.index[1:]:
            # An update is required for columns which increase in size this row, identified by a positive delta.
            update_required = self.deltas.loc[row, :] > 0

            new_price = []
            if len(update_required) > 0:
                # calculate update, per this general formula:
                # new_price = (delta_amount * current_price + old_amount * old_price) / (old_amount + delta_amount)
                new_price = (
                    share_price_on_increases.loc[row, update_required] * self.deltas.loc[row, update_required]
                    + self.open_share_price.loc[row - 1, update_required] * self.positions.loc[row - 1, update_required]
                ) / (self.deltas.loc[row, update_required] + self.positions.loc[row - 1, update_required])

            # Keep previous result where an update isn't required, otherwise replace with new_price
            self.open_share_price.loc[row, :] = self.open_share_price.loc[row - 1, :].where(
                ~update_required, new_price, axis=0
            )


def get_agent_positions(session: Session) -> dict[str, AgentPosition]:
    """Create an AgentPosition for each agent in the wallet history."""
    return {agent: AgentPosition(wallet) for agent, wallet in pg.get_wallet_info_history(session).items()}


def calculate_pnl(
    pool_config: pd.DataFrame, pool_info: pd.DataFrame, checkpoint_info: pd.DataFrame
) -> dict[str, AgentPosition]:
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
    session = pg.initialize_session()
    agent_positions = get_agent_positions(session)
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


def plot_pnl(agent_positions: dict[str, AgentPosition], axes):
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

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


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
        self.pnl = pd.Series(data=np.nan, index=wallet_history.index)

        # Scrap the wallet history for parts. First we extract the share price and timestamp.
        self.share_price = wallet_history["sharePrice"]
        self.timestamp = wallet_history["timestamp"]
        # Then we keep track of every other column, to extract them into other tables.
        other_columns = [col for col in wallet_history.columns if col not in ["sharePrice", "timestamp"]]

        # Create positions dataframe which tracks aggregate holdings.
        self.positions = wallet_history.loc[:, other_columns].copy()

        # Create deltas dataframe which tracks change in holdings.
        self.deltas = self.positions.diff()
        # After the diff() call above, the first row of the deltas table will be NaN.
        # Replace them with the first row of the positions table, effectively capturing a delta from 0.
        self.deltas.iloc[0] = self.positions.iloc[0]

        # Prepare tables filled with NaNs, in the shape of [blocks, positions]
        share_price_on_increases = pd.DataFrame(
            data=np.nan,  # type: ignore
            index=self.deltas.index,  # type: ignore
            columns=self.deltas.columns,  # type: ignore
        )
        self.open_share_price = pd.DataFrame(
            data=np.nan,  # type: ignore
            index=self.deltas.index,  # type: ignore
            columns=self.deltas.columns,  # type: ignore
        )

        # When we have an increase in position, we use the current block's share_price
        share_price_on_increases = share_price_on_increases.mask(self.deltas > 0, self.share_price, axis=0)

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
            update_required = self.deltas.loc[row, :].values > 0  # boolean values where we have positive deltas.
            cols = self.deltas.columns[update_required].to_list()  # associated column names

            new_price = []
            if len(update_required) > 0:
                # calculate update, per this general formula:
                # new_price = (delta_amount * current_price + old_amount * old_price) / (old_amount + delta_amount)
                new_price = (
                    share_price_on_increases.loc[row, cols] * self.deltas.loc[row, cols]  # type: ignore
                    + self.open_share_price.loc[row - 1, cols] * self.positions.loc[row - 1, cols]  # type: ignore
                ) / (
                    self.deltas.loc[row, cols] + self.positions.loc[row - 1, cols]  # type: ignore
                )

            # Keep previous result where an update isn't required, otherwise replace with new_price
            self.open_share_price.loc[row, :] = self.open_share_price.loc[row - 1, :].where(
                ~update_required, new_price, axis=0
            )

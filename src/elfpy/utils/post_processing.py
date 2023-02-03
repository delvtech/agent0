"""
Helper functions for post-processing simulation outputs
"""
from __future__ import annotations  # types will be strings by default in 3.11
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from elfpy.simulators import Simulator


def get_simulation_state_df(simulator: Simulator) -> pd.DataFrame:
    r"""Converts the simulator output dictionary to a pandas dataframe

    Parameters
    ----------
    simulation_state : SimulationState
        simulation_state, which is a member variable of the Simulator class

    Returns
    -------
    trades : DataFrame
        Pandas dataframe containing the simulation_state keys as columns, as well as some computed columns
    """
    # construct dataframe from simulation dict
    return pd.DataFrame.from_dict(simulator.simulation_state.__dict__)


def compute_derived_variables(simulator: Simulator) -> pd.DataFrame:
    r"""Converts the simulator output dictionary to a pandas dataframe and computes derived variables

    Parameters
    ----------
    simulation_state : SimulationState
        simulation_state, which is a member variable of the Simulator class

    Returns
    -------
    trades : DataFrame
        Pandas dataframe containing the simulation_state keys as columns, as well as some computed columns
    """
    trades_df = get_simulation_state_df(simulator)
    # calculate derived variables across runs
    trades_df["pool_apr_percent"] = trades_df.pool_apr * 100
    trades_df["vault_apr_percent"] = trades_df.vault_apr * 100
    share_liquidity_usd = trades_df.share_reserves * trades_df.share_price
    bond_liquidity_usd = trades_df.bond_reserves * trades_df.share_price * trades_df.spot_price
    trades_df["total_liquidity_usd"] = share_liquidity_usd + bond_liquidity_usd
    # calculate percent change in spot price since the first spot price (after first trade)
    trades_df["price_total_return"] = trades_df.loc[:, "spot_price"] / trades_df.loc[0, "spot_price"] - 1
    trades_df["price_total_return_percent"] = trades_df.price_total_return * 100
    # rescale price_total_return to equal init_share_price for the first value, for comparison
    trades_df["price_total_return_scaled_to_share_price"] = (
        trades_df.price_total_return + 1
    ) * trades_df.init_share_price  # this is APR (does not include compounding)
    # compute the total return from share price
    trades_df["share_price_total_return"] = 0
    for run in trades_df.run_number.unique():
        trades_df.loc[trades_df.run_number == run, "share_price_total_return"] = (
            trades_df.loc[trades_df.run_number == run, "share_price"]
            / trades_df.loc[trades_df.run_number == run, "share_price"].iloc[0]
            - 1
        )
    trades_df["share_price_total_return_percent"] = trades_df.share_price_total_return * 100
    # compute rescaled returns to common annualized metric
    scale = 365 / (trades_df["day"] + 1)
    trades_df["price_total_return_percent_annualized"] = scale * trades_df["price_total_return_percent"]
    trades_df["share_price_total_return_percent_annualized"] = scale * trades_df["share_price_total_return_percent"]
    # create explicit column that increments per trade
    add_pnl_columns(trades_df)
    return trades_df


def add_pnl_columns(trades_df: pd.DataFrame) -> None:
    """Adds Profit and Loss Column for every agent to the dataframe that is passed in"""
    num_agents = len([col for col in trades_df if col.startswith("agent") and col.endswith("base")])
    for agent_id in range(num_agents):
        trades_df[f"agent_{agent_id}_pnl"] = trades_df.apply(
            lambda row: row[f"agent_{agent_id}_base"]
            + row[f"agent_{agent_id}_lp_tokens"]
            + row[f"agent_{agent_id}_total_longs"]
            + row[f"agent_{agent_id}_total_shorts"],
            axis=1,
        )


def aggregate_trade_data(trades: pd.DataFrame) -> pd.DataFrame:
    r"""Aggregate trades dataframe by computing means

    Parameters
    ----------
    trades : DataFrame
        Pandas dataframe containing the simulation_state keys as columns, as well as some computed columns

    Returns
    -------
    trades_agg : DataFrame
        aggregated dataframe that keeps the model_name and day columns
        and computes the mean over spot price
    """
    ### STATS AGGREGATED BY SIM AND DAY ###
    # aggregates by two dimensions:
    # 1. model_name (directly output from pricing_model class)
    # 2. day
    keep_columns = [
        "model_name",
        "day",
    ]
    trades_agg = trades.groupby(keep_columns).agg(
        {
            "spot_price": ["mean"],
        }
    )
    trades_agg.columns = ["_".join(col).strip() for col in trades_agg.columns.values]
    trades_agg = trades_agg.reset_index()
    return trades_agg

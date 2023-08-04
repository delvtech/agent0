"""Helper functions for post-processing simulation outputs"""
from __future__ import annotations  # types will be strings by default in 3.11

import pandas as pd

import lib.elfpy.elfpy.simulators as simulators

# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false


def aggregate_agent_and_market_states(combined_trades_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the trade details from the simulation state into a representation of market & wallet states per trade
    TODO:
    The new combined_trades_df stores the deltas (literally market_delta and agent_delta).
    We want this function to loop over every trade and construct the market state by applying each delta.
    We can also compute the PNL values in the loop. This should be able to take advantage of multi-threading,
    since the delta values are fixed & we don't have to worry about trades changing what they would be.
    Example:
        market_state = hyperdrive.MarketState(
            lp_total_supply=combined_trades_df.market_init.iloc[0].lp_total_supply,
            share_reserves=combined_trades_df.market_init.iloc[0].share_reserves,
            bond_reserves=combined_trades_df.market_init.iloc[0].bond_reserves,
            variable_apr=combined_trades_df.market_init.iloc[0].variable_apr,
            share_price=combined_trades_df.market_init.iloc[0].share_price,
            init_share_price=combined_trades_df.market_init.iloc[0].init_share_price,
            curve_fee_multiple=combined_trades_df.market_init.iloc[0].curve_fee_multiple,
            flat_fee_multiple=combined_trades_df.market_init.iloc[0].flat_fee_multiple,
        )
        agent_wallets = list(combined_trades_df.iloc[0, :].agent_init)
        for trade_number in range(combined_trades_df.trade_number.max()):

    def add_pnl_to_trades_df()
        this can be done across prallel processors
        loop through the sim trades
        compute pnl
        add columns
    """
    raise NotImplementedError


def aggregate_trade_data(trades: pd.DataFrame) -> pd.DataFrame:
    r"""Aggregate trades dataframe by computing means

    Arguments
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
            "delta_base_abs": ["sum"],
        }
    )
    trades_agg.columns = ["_".join(col).strip() for col in trades_agg.columns.values]
    trades_agg = trades_agg.reset_index()
    return trades_agg


def get_simulation_state_df(simulator: simulators.Simulator) -> pd.DataFrame:
    r"""Converts the simulator output dictionary to a pandas dataframe

    Arguments
    ----------
    simulator : Simulator
        Simulator object that holds the simulation_state

    Returns
    -------
    trades : DataFrame
        Pandas dataframe containing the simulation_state keys as columns, as well as some computed columns

    .. todo::
        Using the new sim state:
        # def get_simulation_state_df(simulator: Simulator) -> pd.DataFrame:
        #      return simulator.simulation_state.combined_dataframe

        Also, converting from FixedPoint (which gets cast to "object") to real types needs to be fixed
    """
    # construct dataframe from simulation dict
    sim_dict = simulator.simulation_state.__dict__
    if "frozen" in sim_dict:
        del sim_dict["frozen"]
    if "no_new_attribs" in sim_dict:
        del sim_dict["no_new_attribs"]
    trades_df = pd.DataFrame.from_dict(sim_dict)
    string_columns = [
        "model_name",
    ]
    int_columns = [
        "checkpoint_duration_days",
        "run_number",
        "day",
        "block_number",
        "daily_block_number",
        "trade_number",
    ]
    float_columns = [
        "base_buffer",
        "bond_buffer",
        "bond_reserves",
        "checkpoint_duration",
        "current_time",
        "current_variable_apr",
        "curve_fee_multiple",
        "flat_fee_multiple",
        "fixed_apr",
        "gov_fees_accrued",
        "governance_fee_multiple",
        "init_share_price",
        "long_average_maturity_time",
        "long_base_volume",
        "longs_outstanding",
        "lp_total_supply",
        "run_number",
        "share_reserves",
        "share_price",
        "short_average_maturity_time",
        "short_base_volume",
        "shorts_outstanding",
        "spot_price",
        "time_step_size",
        "total_supply_withdraw_shares",
        "variable_apr",
        "withdraw_capital",
        "withdraw_interest",
        "withdraw_shares_ready_to_withdraw",
    ]
    trades_df[float_columns] = trades_df[float_columns].astype(float)
    trades_df[int_columns] = trades_df[int_columns].astype(int)
    trades_df[string_columns] = trades_df[string_columns].astype(str)
    for col in list(trades_df):
        if col.startswith("agent"):  # type: ignore
            trades_df[col] = trades_df[col].astype(float)
    return trades_df


def compute_derived_variables(simulator: simulators.Simulator) -> pd.DataFrame:
    r"""Converts the simulator output dictionary to a pandas dataframe and computes derived variables

    Argument
    ----------
    simulator : Simulator
        Simulator object that holds the simulation_state

    Returns
    -------
    trades : DataFrame
        Pandas dataframe containing the simulation_state keys as columns, as well as some computed columns
    """
    trades_df = get_simulation_state_df(simulator)
    # calculate changes in reserves, corresponding to latest trade
    trades_df["delta_shares"] = trades_df.share_reserves.diff()
    trades_df["delta_base"] = trades_df.share_reserves.diff() * trades_df.share_price
    trades_df["delta_bonds"] = trades_df.bond_reserves.diff()
    # same thing but with absolute values for plotting
    trades_df["delta_shares_abs"] = trades_df.delta_shares.abs()
    trades_df["delta_base_abs"] = trades_df.delta_base.abs()
    trades_df["delta_bonds_abs"] = trades_df.delta_bonds.abs()
    # calculate derived variables across runs
    trades_df["fixed_apr_percent"] = trades_df.fixed_apr * 100
    trades_df["variable_apr_percent"] = trades_df.variable_apr * 100
    share_liquidity_usd = trades_df.share_reserves * trades_df.share_price
    bond_liquidity_usd = trades_df.bond_reserves * trades_df.share_price * trades_df.spot_price
    trades_df["total_liquidity_usd"] = share_liquidity_usd + bond_liquidity_usd
    # calculate percent change in spot price since the first spot price (after first trade)
    trades_df["price_total_return"] = (
        trades_df.loc[:, "spot_price"] / trades_df.loc[0, "spot_price"] - 1  # type: ignore
    )
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
            / trades_df.loc[trades_df.run_number == run, "share_price"].iloc[0]  # type: ignore
            - 1
        )
    trades_df["share_price_total_return_percent"] = trades_df.share_price_total_return * 100
    # compute rescaled returns to common annualized metric
    scale = 365 / (trades_df["day"] + 1)
    trades_df["price_total_return_percent_annualized"] = scale * trades_df["price_total_return_percent"]
    trades_df["share_price_total_return_percent_annualized"] = scale * trades_df["share_price_total_return_percent"]
    # create explicit column that increments per trade
    add_pnl_columns(trades_df)
    trades_df = trades_df.reset_index()
    return trades_df


def add_pnl_columns(trades_df: pd.DataFrame) -> None:
    """Adds Profit and Loss Column for every agent to the dataframe that is passed in"""
    num_agents = len([col for col in trades_df if str(col).startswith("agent") and str(col).endswith("base")])
    for agent_id in range(num_agents):
        wallet_values_in_base = [
            f"agent_{agent_id}_base",
            f"agent_{agent_id}_lp_tokens",
            f"agent_{agent_id}_total_longs",
            f"agent_{agent_id}_total_shorts",
        ]
        wallet_values_in_base_no_mock = [
            f"agent_{agent_id}_base",
            f"agent_{agent_id}_lp_tokens",
            f"agent_{agent_id}_total_longs_no_mock",
            f"agent_{agent_id}_total_shorts_no_mock",
        ]
        trades_df[f"agent_{agent_id}_pnl"] = trades_df[wallet_values_in_base].astype(float).sum(axis=1)
        trades_df[f"agent_{agent_id}_pnl_no_mock"] = trades_df[wallet_values_in_base_no_mock].astype(float).sum(axis=1)

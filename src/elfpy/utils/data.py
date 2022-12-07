"""
Helper functions for post-processing simulation outputs
"""

import pandas as pd


def format_trades(analysis_dict):
    """Converts the simulator output dictionary to a pandas dataframe and computes derived variables"""
    # construct simulation dataframe output
    trades = pd.DataFrame.from_dict(analysis_dict)
    # calculate derived variables across runs
    trades["pool_apy_percent"] = trades.pool_apy * 100
    trades["vault_apy_percent"] = trades.vault_apy * 100
    share_liquidity_usd = trades.share_reserves * trades.share_price
    bond_liquidity_usd = trades.bond_reserves * trades.share_price * trades.spot_price
    trades["total_liquidity_usd"] = share_liquidity_usd + bond_liquidity_usd
    # calculate percent change in spot price since the first spot price (after first trade, kinda weird)
    trades["price_total_return"] = (
        trades.loc[:, "spot_price"] / trades.loc[0, "spot_price"] - 1
    )  # rescales price_total_return to equal init_share_price for the first value, for comparison
    trades["price_total_return_scaled_to_share_price"] = (
        trades.price_total_return + 1
    ) * trades.init_share_price  # this is APR (does not include compounding)
    base_asset_liquidity_usd = trades.share_reserves * trades.share_price
    token_asset_liquidity_usd = trades.bond_reserves * trades.share_price * trades.spot_price
    trades["total_liquidity_usd"] = base_asset_liquidity_usd + token_asset_liquidity_usd
    trades["share_price_total_return"] = 0
    for run in trades.run_number.unique():
        trades.loc[trades.run_number == run, "share_price_total_return"] = (
            trades.loc[trades.run_number == run, "share_price"]
            / trades.loc[trades.run_number == run, "share_price"].iloc[0]
            - 1
        )
    trades["price_total_return_percent"] = trades.price_total_return * 100
    trades["share_price_total_return_percent"] = trades.share_price_total_return * 100
    scale = 365 / (trades["day"] + 1)
    trades["price_total_return_percent_annualized"] = scale * trades["price_total_return_percent"]
    trades["share_price_total_return_percent_annualized"] = scale * trades["share_price_total_return_percent"]

    # create explicit column that increments per trade
    trades = trades.reset_index()

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
    return [trades, trades_agg]

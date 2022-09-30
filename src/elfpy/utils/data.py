"""
Helper functions for post-processing simulation outputs
"""

import pandas as pd


def format_trades(analysis_dict):
    """Converts the simulator output dictionary to a pandas dataframe and computes derived variables"""
    # construct simulation dataframe output
    trades = pd.DataFrame.from_dict(analysis_dict)
    # calculate derived variables across runs
    trades["time_diff"] = trades.time_until_end.diff()
    trades["time_diff_shift"] = trades.time_until_end.shift(-1).diff()
    trades.loc[len(trades) - 1, "time_diff_shift"] = 1
    trades["fee_in_usd"] = trades.fee  # * trades.base_asset_price
    trades["fee_in_bps"] = trades.fee / trades.out_without_fee * 100 * 100
    base_asset_liquidity_usd = trades.base_asset_reserves * trades.base_asset_price
    token_asset_liquidity_usd = (
        trades.token_asset_reserves * trades.base_asset_price * trades.spot_price
    )
    trades["total_liquidity_usd"] = base_asset_liquidity_usd + token_asset_liquidity_usd
    trades["trade_volume_usd"] = trades.out_with_fee  # * trades.base_asset_price
    # pr is the percent change in spot price since day 1
    # it is APR (does'nt include compounding)
    trades["pr"] = trades.loc[:, "spot_price"] - trades.loc[0, "spot_price"]
    # pu takes that percent change and normalizes it to be equal to init_share_price at the beginning,
    # so you can compare its progression vs. share_price
    trades["pu"] = (
        trades.pr + 1
    ) * trades.init_share_price  # this is APR (does not include compounding)
    # create explicit column that increments per trade
    trades = trades.reset_index()
    # aggregate trades
    keep_columns = [
        "day",
        "model_name",
    ]
    trades_agg = trades.groupby(keep_columns).agg(
        {
            "trade_volume_usd": ["sum"],
            "fee_in_usd": ["mean", "std", "min", "max", "sum"],
            "fee_in_bps": ["mean", "sum"],
        }
    )
    trades_agg.columns = ["_".join(col).strip() for col in trades_agg.columns.values]
    trades_agg["fee_in_usd_sum_cum"] = 0
    trades_agg = trades_agg.reset_index()
    for model in trades_agg.model_name.unique():
        trades_agg.loc[
            trades_agg.model_name == model, "fee_in_usd_sum_cum"
        ] = trades_agg.loc[trades_agg.model_name == model, "fee_in_usd_sum"].cumsum()
    return [trades, trades_agg]

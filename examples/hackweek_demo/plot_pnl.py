"""Plots the pnl"""

from __future__ import annotations

import numpy as np
import pandas as pd

from matplotlib import ticker as mpl_ticker
from extract_data_logs import calculate_spot_price

import elfpy
from elfpy.wallet.wallet import Wallet, Long, Short
from elfpy import types
from elfpy.math import FixedPoint
from elfpy.markets.hyperdrive import hyperdrive_assets
from elfpy.markets.hyperdrive import AssetIdPrefix


def get_wallet_from_onchain_trade_info(
    address: str,
    trades: pd.DataFrame,
    index: int = 0,
    add_to_existing_wallet: Wallet | None = None,
) -> Wallet:
    # pylint: disable=too-many-arguments, too-many-branches, too-many-locals
    r"""Construct wallet balances from on-chain trade info.

    Arguments
     ---------
     address : str
         Address of the wallet.
     info : OnChainTradeInfo
         On-chain trade info.
     index : int
         Index of the wallet among ALL agents.

     Returns
     -------
     Wallet
         Wallet with Short, Long, and LP positions.
    """
    # TODO: remove restriction forcing Wallet index to be an int (issue #415)
    if add_to_existing_wallet is None:
        wallet = Wallet(
            address=index,
            balance=types.Quantity(amount=FixedPoint(scaled_value=0), unit=types.TokenType.BASE),
        )
    else:
        wallet = add_to_existing_wallet

    position_id = trades["id"]
    trades_in_position = ((trades["from"] == address) | (trades["to"] == address)) & (trades["id"] == position_id)

    positive_balance = int(trades.loc[(trades_in_position) & (trades["to"] == address), "value"].sum())
    negative_balance = int(trades.loc[(trades_in_position) & (trades["from"] == address), "value"].sum())
    balance = positive_balance - negative_balance

    asset_type = trades["asset_type"].iloc[0]
    maturity = trades["asset_maturity"].iloc[0]
    mint_time = maturity if np.isnan(maturity) else int(maturity) - elfpy.SECONDS_IN_YEAR

    # check if there's an outstanding balance
    if balance != 0:
        if asset_type == "SHORT":
            previous_balance = wallet.shorts[mint_time].balance if mint_time in wallet.shorts else 0
            marginal_position_change = FixedPoint(scaled_value=balance)
            new_balance = previous_balance + marginal_position_change
            if new_balance == 0:
                # remove key of "mint_time" from the "wallet.shorts" dict
                wallet.shorts.pop(mint_time, None)
            else:
                # we either do a marginal update or full weighted average for open share price
                if add_to_existing_wallet:  # marginal update
                    previous_share_price = (
                        wallet.shorts[mint_time].open_share_price if mint_time in wallet.shorts else 0
                    )
                    marginal_open_share_price = FixedPoint(scaled_value=int(trades.sharePrice))
                    new_open_share_price = (
                        previous_balance * previous_share_price + marginal_position_change * marginal_open_share_price
                    )
                    new_open_share_price /= previous_balance + marginal_position_change
                else:  # weighted average across a bunch of trades
                    sum_product_of_open_share_price_and_value, sum_value = 0, 0
                    for specific_trade in trades_in_position.index[trades_in_position]:
                        value = trades.loc[specific_trade, "value"]
                        value *= -1 if trades.loc[specific_trade, "from"] == address else 1
                        sum_value += value
                        sum_product_of_open_share_price_and_value += (
                            value * trades.loc[specific_trade, "sharePrice"] / 1e18
                        )
                    new_open_share_price = FixedPoint(
                        scaled_value=int(sum_product_of_open_share_price_and_value / sum_value)
                    )
                wallet.shorts.update(
                    {
                        mint_time: Short(
                            balance=new_balance,
                            open_share_price=new_open_share_price,
                        )
                    }
                )
        elif asset_type == "LONG":
            previous_balance = wallet.longs[mint_time].balance if mint_time in wallet.longs else 0
            new_balance = previous_balance + FixedPoint(scaled_value=balance)
            if new_balance == 0:
                # remove key of "mint_time" from the "wallet.longs" dict
                wallet.longs.pop(mint_time, None)
            wallet.longs.update({mint_time: Long(balance=new_balance)})
        elif asset_type == "LP":
            wallet.lp_tokens += FixedPoint(scaled_value=balance)
    return wallet


def calculate_pnl(logs_df):
    """Calculates the pnl given trade data"""
    # pylint: disable=too-many-locals
    # Drop all rows with nan maturity timestamps

    idx = ~logs_df["maturityTime"].isna()
    position_duration = max(logs_df.maturityTime[idx] - logs_df.timestamp[idx])
    position_duration_days = round(position_duration / 60 / 60 / 24)
    position_duration = position_duration_days * 60 * 60 * 24

    def decode_id(row):
        if row["id"] != row["id"]:
            return np.nan, np.nan
        return hyperdrive_assets.decode_asset_id(int(row["id"]))

    def decode_prefix(row):
        return np.nan if np.isnan(row) else AssetIdPrefix(row).name

    tuple_series = logs_df.apply(func=decode_id, axis=1)
    logs_df["prefix"], logs_df["asset_maturity"] = zip(*tuple_series)
    logs_df["asset_type"] = logs_df["prefix"].apply(decode_prefix)

    agents = logs_df["trader"].value_counts().index.tolist() + logs_df["operator"].value_counts().index.tolist()
    agents = list(set(agents))
    agent_wallets = {
        a: Wallet(
            address=agents.index(a),
            balance=types.Quantity(amount=FixedPoint(0), unit=types.TokenType.BASE),
        )
        for a in agents
    }

    # pre-define column names to store agent pnl
    pnl_data = pd.DataFrame(index=logs_df.index)
    agent_col_names = []
    for i in range(len(agents)):
        agent_col_name = f"agent_{i}_pnl"
        pnl_data[agent_col_name] = np.nan
        agent_col_names.append(agent_col_name)

    for idx, row in logs_df.iterrows():
        for agent in agents:
            agent_index = agents.index(agent)

            marginal_trades = pd.DataFrame(row).T

            # pass in one trade at a time, and get out the updated wallet
            agent_wallets[agent] = get_wallet_from_onchain_trade_info(
                address=agent,
                trades=marginal_trades,
                index=agents.index(agent),
                add_to_existing_wallet=agent_wallets[agent],
            )

            spot_price = calculate_spot_price(
                row.shareReserves,
                row.bondReserves,
                row.lpTotalSupply,
                row.maturityTime,
                row.timestamp,
                position_duration,
            )

            # LP value (TODO: check why certain agents own more than 100% of the pool)
            total_lp_value = row.shareReserves / 1e18 * row.sharePrice / 1e18 + row.bondReserves / 1e18 * spot_price
            share_of_pool = float(agent_wallets[agent].lp_tokens) / (row.lpTotalSupply / 1e18)
            # print(f"{float(agent_wallets[agent].lp_tokens)=}")
            # print(f"{row.lpTotalSupply/1e18=}")
            pnl = share_of_pool * total_lp_value

            # for each LONG
            for _, long in agent_wallets[agent].longs.items():
                pnl += float(long.balance) * spot_price

            # for each SHORT
            for _, short in agent_wallets[agent].shorts.items():
                pnl += float(short.balance) * (1 - spot_price)

            pnl_data.loc[idx, f"agent_{agent_index}_pnl"] = pnl

    x_data = pd.to_datetime(logs_df.loc[:, "timestamp"], unit="s")

    return x_data, pnl_data


def plot_pnl(x_data, y_data, axes):
    """Plots the pnl data"""
    axes.plot(x_data, y_data)
    # change y-axis unit format to #,###.0f
    axes.yaxis.set_major_formatter(mpl_ticker.FuncFormatter(lambda x, p: format(int(x), ",")))

    # TODO fix these top use axes
    axes.set_xlabel("block timestamp")
    axes.set_ylabel("pnl")
    axes.yaxis.set_label_position("right")
    axes.yaxis.tick_right()
    axes.set_title("pnl over time")

    # make this work: col_names.replace("_pnl","")
    col_names = y_data.columns
    axes.legend([col_names.replace("_pnl", "") for col_names in col_names])

    # %%

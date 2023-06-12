"""Plots the pnl"""

from __future__ import annotations
import pandas as pd
from matplotlib import ticker as mpl_ticker
import elfpy
from elfpy.wallet.wallet import Wallet, Long, Short
from elfpy import types
from elfpy.math import FixedPoint
from extract_data_logs import calculate_spot_price


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
    share_price = trades.share_price

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

    asset_type = trades["trade_enum"].iloc[0]
    maturity = trades["maturity_timestamp"].iloc[0]
    mint_time = int(maturity) - elfpy.SECONDS_IN_YEAR

    # check if there's an outstanding balance
    if balance != 0:
        if asset_type == "SHORT":
            # loop across all the positions owned by this wallet
            sum_product_of_open_share_price_and_value, sum_value = 0, 0

            # WEIGHTED AVERAGE ACROSS A BUNCH OF TRADES
            for specific_trade in trades_in_position.index[trades_in_position]:
                value = trades.loc[specific_trade, "value"]
                value *= -1 if trades.loc[specific_trade, "from"] == address else 1
                sum_value += value
                sum_product_of_open_share_price_and_value += (
                    value * share_price[trades.loc[specific_trade, "block_number"]]
                )

            # WEIGHTED AVERAGR FROM A MARGINAL UPDATE
            previous_balance = wallet.shorts[mint_time].balance if mint_time in wallet.shorts else 0
            previous_share_price = wallet.shorts[mint_time].open_share_price if mint_time in wallet.shorts else 0

            marginal_position_change = FixedPoint(scaled_value=balance)
            marginal_open_share_price = FixedPoint(scaled_value=int(trades.share_price))

            new_balance = previous_balance + marginal_position_change

            if new_balance == 0:
                # remove key of "mint_time" from the "wallet.shorts" dict
                wallet.shorts.pop(mint_time, None)
            else:
                new_open_share_price = (
                    previous_balance * previous_share_price
                    + marginal_position_change
                    * marginal_open_share_price
                    / (previous_balance + marginal_position_change)
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


def calculate_pnl(trade_data):
    # pylint: disable=too-many-locals
    """Calculates the pnl given trade data"""
    # Drop all rows with nan maturity timestamps
    trade_data = trade_data[~trade_data["maturity_timestamp"].isna()]

    # %% estimate position duration and add it in
    position_duration = max(trade_data.maturity_timestamp - trade_data.block_timestamp)
    # print(f"empirically observed position_duration in seconds: {position_duration}")
    # print(f"empirically observed position_duration in minutes: {position_duration/60}")
    # print(f"empirically observed position_duration in hours: {position_duration/60/60}")
    # print(f"empirically observed position_duration in days: {position_duration/60/60/24}")
    position_duration_days = round(position_duration / 60 / 60 / 24)
    # print(f"assuming position_duration is {position_duration_days}")
    position_duration = position_duration_days * 60 * 60 * 24

    agents = trade_data["operator"].value_counts().index.tolist()
    agent_wallets = {
        a: Wallet(
            address=agents.index(a),
            balance=types.Quantity(amount=FixedPoint(0), unit=types.TokenType.BASE),
        )
        for a in agents
    }

    # %% pre-define column names to store agent pnl
    pnl_data = pd.DataFrame(index=trade_data.index)
    agent_col_names = []
    for i in range(len(agents)):
        agent_col_name = f"agent_{i}_pnl"
        pnl_data[agent_col_name] = 0
        agent_col_names.append(agent_col_name)

    # %%
    process_rows = len(trade_data)

    for idx, row in trade_data.loc[0:process_rows, :].iterrows():
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
                row.share_reserves,
                row.bond_reserves,
                row.lp_total_supply,
                row.maturity_timestamp,
                row.block_timestamp,
                position_duration,
            )
            # print(f"{spot_price=}")

            # LP value (TODO: check why certain agents own more than 100% of the pool)
            total_lp_value = row.share_reserves / 1e18 * row.share_price / 1e18 + row.bond_reserves / 1e18 * spot_price
            share_of_pool = float(agent_wallets[agent].lp_tokens) / (row.lp_total_supply / 1e18)
            # print(f"{float(agent_wallets[agent].lp_tokens)=}")
            # print(f"{row.lp_total_supply/1e18=}")
            pnl = share_of_pool * total_lp_value

            # for each LONG
            for _, long in agent_wallets[agent].longs.items():
                pnl += float(long.balance) * spot_price

            # for each SHORT
            for _, short in agent_wallets[agent].shorts.items():
                pnl += float(short.balance) * (1 - spot_price)

            pnl_data.loc[idx, f"agent_{agent_index}_pnl"] = pnl

    # %%
    x_data = pd.to_datetime(trade_data.loc[:, "block_timestamp"], unit="s")

    return (x_data, pnl_data)


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

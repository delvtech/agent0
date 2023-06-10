# TODO fix this file
# pylint: disable=all

# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.6
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
"""simulation for the Hyperdrive market"""
from __future__ import annotations
import json
import pandas as pd
import os
import numpy as np
import elfpy
from elfpy.wallet.wallet import Wallet, Long, Short
from elfpy.markets.hyperdrive import hyperdrive_assets
import elfpy.utils.apeworx_integrations as ape_utils
from collections import namedtuple
from elfpy import types
from elfpy.math import FixedPoint
from elfpy.markets.hyperdrive.hyperdrive_market import (
    HyperdriveMarket,
    HyperdriveMarketState,
)
from elfpy.markets.hyperdrive import HyperdrivePricingModel
from matplotlib import ticker as mpl_ticker
from matplotlib import dates as mdates
from matplotlib import pyplot as plt

from extract_data_logs import read_json_to_pd, explode_transaction_data

## Get transactions from data
trans_data = "../../.logging/transactions.json"
config_data = "../../.logging/hyperdrive_config.json"
pool_info_data = "../../.logging/hyperdrive_pool_info.json"

trans_data = explode_transaction_data(read_json_to_pd(trans_data))
config_data = read_json_to_pd(config_data)
pool_info_data = read_json_to_pd(pool_info_data).T

data = get_combined_data(trans_data, pool_data)

# %%
# data = data[~data["args.id"].isna()]
# data = data.reset_index(drop=True)
# prefix, maturity_timestamp = hyperdrive_assets.decode_asset_id(data["args.id"].values)
# trade_type = pd.DataFrame(prefix).apply(lambda x: hyperdrive_assets.AssetIdPrefix(x.values).name, axis=1)

# %%
# data["prefix"] = prefix
data["timestamp"] = data["timestamp"].astype(int)

rename_dict = {
    "contractAddress": "contract_address",
    "transactionHash": "transaction_hash",
    "blockNumber": "block_number",
    "blockHash": "block_hash",
    "transactionIndex": "transaction_index",
    "args.operator": "operator",  # missing
    "args.from": "from",  # missing
    "args.to": "to",  # missing
    "args.id": "id",  # missing
    "args.value": "value",  # missing
    "prefix": "prefix",  # missing
    "input.params._maturityTime": "maturity_timestamp",
    "input.method": "trade_type",
    "shareReserves": "share_reserves",
    "bondReserves": "bond_reserves",
    "lpTotalSupply": "lp_total_supply",
    "sharePrice": "share_price",
    "longsOutstanding": "longs_outstanding",
    "longAverageMaturityTime": "longs_average_maturity_time",
    "shortsOutstanding": "shorts_outstanding",
    "shortAverageMaturityTime": "short_average_maturity_time",
    "shortBaseVolume": "short_base_volume",
    "timestamp": "block_timestamp",
}

# %%
columns = [k for k in rename_dict.keys()]

# TODO remove this hack, only grab columns that exist from data
columns = [c for c in columns if c in data.columns]

# %%
# Filter data based on columns
trade_data = data[columns]
# Rename columns
trade_data = trade_data.rename(columns=rename_dict)


# %%
def get_wallet_from_onchain_trade_info(
    address: str,
    trades: pd.DataFrame,
    index: int = 0,
    add_to_existing_wallet: Wallet | None = None,
) -> Wallet:
    # pylint: disable=too-many-arguments, too-many-branches

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

    asset_prefix = trades["prefix"].iloc[0]
    asset_type = trades["trade_type"].iloc[0]
    maturity = trades["maturity_timestamp"].iloc[0]
    mint_time = maturity - elfpy.SECONDS_IN_YEAR

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
            open_share_price = int(sum_product_of_open_share_price_and_value / sum_value)

            # WEIGHTED AVERAGR FROM A MARGINAL UPDATE
            previous_balance = wallet.shorts[mint_time].balance if mint_time in wallet.shorts else 0
            previous_share_price = wallet.shorts[mint_time].open_share_price if mint_time in wallet.shorts else 0

            marginal_position_change = FixedPoint(scaled_value=balance)
            marginal_open_share_price = FixedPoint(scaled_value=trades.open_share_price)

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


# %%
agents = trade_data["operator"].value_counts().index.tolist()
agent_wallets = {
    a: Wallet(
        address=agents.index(a),
        balance=types.Quantity(amount=FixedPoint(0), unit=types.TokenType.BASE),
    )
    for a in agents
}


# %% attempt to mock up trade closeout
def get_wallet_state(agent_wallet: Wallet, market: HyperdriveMarket) -> dict[str, FixedPoint]:
    r"""The wallet's current state of public variables

    .. todo:: This will go away once we finish refactoring the state
    """
    lp_token_value = FixedPoint(0)
    # proceed further only if the agent has LP tokens and avoid divide by zero
    if agent_wallet.lp_tokens > FixedPoint(0) and market.market_state.lp_total_supply > FixedPoint(0):
        share_of_pool = agent_wallet.lp_tokens / market.market_state.lp_total_supply
        pool_value = (
            market.market_state.bond_reserves * market.spot_price  # in base
            + market.market_state.share_reserves * market.market_state.share_price  # in base
        )
        lp_token_value = pool_value * share_of_pool  # in base
    share_reserves = market.market_state.share_reserves
    # compute long values in units of base
    longs_value = FixedPoint(0)
    longs_value_no_mock = FixedPoint(0)
    for mint_time, long in agent_wallet.longs.items():
        if long.balance > FixedPoint(0) and share_reserves:
            balance = hyperdrive_actions.calc_close_long(
                bond_amount=long.balance,
                market_state=market.market_state,
                position_duration=market.position_duration,
                pricing_model=market.pricing_model,
                block_time=market.block_time.time,
                mint_time=mint_time,
                is_trade=True,
            )[1].balance.amount
        else:
            balance = FixedPoint(0)
        longs_value += balance
        longs_value_no_mock += long.balance * market.spot_price
    # compute short values in units of base
    shorts_value = FixedPoint(0)
    shorts_value_no_mock = FixedPoint(0)
    for mint_time, short in agent_wallet.shorts.items():
        balance = FixedPoint(0)
        if (
            short.balance > FixedPoint(0)
            and share_reserves > FixedPoint(0)
            and market.market_state.bond_reserves - market.market_state.bond_buffer > short.balance
        ):
            balance = hyperdrive_actions.calc_close_short(
                bond_amount=short.balance,
                market_state=market.market_state,
                position_duration=market.position_duration,
                pricing_model=market.pricing_model,
                block_time=market.block_time.time,
                mint_time=mint_time,
                open_share_price=short.open_share_price,
            )[1].balance.amount
        shorts_value += balance
        base_no_mock = short.balance * (FixedPoint("1.0") - market.spot_price)
        shorts_value_no_mock += base_nomock
    return {
        f"agent{agent_wallet.address}_base": agentwallet.balance.amount,
        f"agent{agent_wallet.address}_lp_tokens": lp_tokenvalue,
        f"agent{agent_wallet.address}_num_longs": FixedPoint(len(agentwallet.longs)),
        f"agent{agent_wallet.address}_num_shorts": FixedPoint(len(agentwallet.shorts)),
        f"agent{agent_wallet.address}_total_longs": longsvalue,
        f"agent{agent_wallet.address}_total_shorts": shortsvalue,
        f"agent{agent_wallet.address}_total_longs_no_mock": longs_value_nomock,
        f"agent{agent_wallet.address}_total_shorts_no_mock": shorts_value_no_mock,
    }


# %%
# WE ARE MISSING INFOMRATION REQUIRED TO CREATE THESE OBJECTS
# THIS IS TRACKED IN ISSUE #530
# https://github.com/delvtech/elf-simulations/issues/530

# pool_info_columns = ['share_price',
#        'longs_outstanding', 'average_maturity_time', 'long_base_volume',
#        'shorts_outstanding', 'short_average_maturity_time',
#        'short_base_volume']
# def get_market_state_from_row(row) -> HyperdriveMarketState:
#     return HyperdriveMarketState(
#         lp_total_supply=FixedPoint(scaled_value=row.lp_total_supply),
#         share_reserves=FixedPoint(scaled_value=row.share_reserves),
#         bond_reserves=FixedPoint(scaled_value=row.bond_reserves),
#         base_buffer=FixedPoint(0),
#         variable_apr=???,

# def create_elfpy_market_without_contracts():
#     elfpy_market = HyperdriveMarket(
#         pricing_model=HyperdrivePricingModel(),
#         market_state=HyperdriveMarketState(

#         )
#         position_duration=time.StretchedTime(
#             days=FixedPoint(hyperdrive_config["term_length"]),
#             time_stretch=FixedPoint(hyperdrive_config["timeStretch"]),
#             normalizing_constant=FixedPoint(hyperdrive_config["term_length"]),
#         ),
#         block_time=time.BlockTime(
#             _time=FixedPoint((block_timestamp - start_timestamp) / 365),
#             _block_number=FixedPoint(block_number),
#             _step_size=FixedPoint("1.0") / FixedPoint("365.0"),
#         ),
#     )


# %% estimate position duration and add it in
position_duration = max(trade_data.maturity_timestamp - trade_data.block_timestamp)
# print(f"empirically observed position_duration in seconds: {position_duration}")
# print(f"empirically observed position_duration in minutes: {position_duration/60}")
# print(f"empirically observed position_duration in hours: {position_duration/60/60}")
# print(f"empirically observed position_duration in days: {position_duration/60/60/24}")
position_duration_days = round(position_duration / 60 / 60 / 24)
# print(f"assuming position_duration is {position_duration_days}")
position_duration = position_duration_days * 60 * 60 * 24


# %%
def calculate_spot_price(
    share_reserves,
    bond_reserves,
    lp_total_supply,
    maturity_timestamp,
    block_timestamp,
    position_duration,
):
    """Calculate spot price."""
    # Hard coding variables to calculate spot price
    initial_share_price = 1
    time_remaining_stretched = 0.045071688063194093
    full_term_spot_price = (
        (initial_share_price * (share_reserves / 1e18)) / ((bond_reserves / 1e18) + (lp_total_supply / 1e18))
    ) ** time_remaining_stretched

    time_left_in_years = (maturity_timestamp - block_timestamp) / position_duration

    return full_term_spot_price * time_left_in_years + 1 * (1 - time_left_in_years)


# %% pre-define column names to store agent pnl
agent_col_names = []
for i in range(len(agents)):
    agent_col_name = f"agent_{i}_pnl"
    trade_data[agent_col_name] = 0
    agent_col_names.append(agent_col_name)
print(f"{agent_col_names=}")

# %%
NUMBER_OF_DATA_ROWS_TO_PROCESS = len(trade_data)

for idx, row in trade_data.loc[0:NUMBER_OF_DATA_ROWS_TO_PROCESS, :].iterrows():
    for agent in agents:
        agent_index = agents.index(agent)
        # get their wallet
        wallet = agent_wallets[agent]

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
        # print(f"agent {row.operator[:8]} has {pnl} from LP only (owns {share_of_pool:,.0%} of the pool)")

        # for each LONG
        for mint_time, long in agent_wallets[agent].longs.items():
            pnl += float(long.balance) * spot_price
        # for each SHORT
        for mint_time, short in agent_wallets[agent].shorts.items():
            pnl += float(short.balance) * (1 - spot_price)

        trade_data.loc[idx, f"agent_{agent_index}_pnl"] = pnl

# %%
x_data = pd.to_datetime(trade_data.loc[:, "block_timestamp"], unit="s")
col_names = agent_col_names[:-1]
print(f"{col_names=}")
y_data = trade_data.loc[:, col_names]
plt.plot(x_data, y_data)
# change y-axis unit format to #,###.0f
plt.gca().yaxis.set_major_formatter(mpl_ticker.FuncFormatter(lambda x, p: format(int(x), ",")))
plt.xlabel("block timestamp")
plt.ylabel("pnl")
plt.title("pnl over time")
# format x-axis as time
# plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
plt.gcf().autofmt_xdate()

# make this work: col_names.replace("_pnl","")
plt.legend([col_names.replace("_pnl", "") for col_names in col_names])

# %%

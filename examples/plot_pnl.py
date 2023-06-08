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

# %%
# Hard coding location for now
trans_data = "hyperTransRecs_updated.json"

with open(trans_data, 'r', encoding='utf8') as f:
    json_data = json.load(f)

data = pd.DataFrame(json_data)

# %%
data.columns

# %%
timestamps = data['timestamp']
decoded_logs = data['decoded_logs'].str[0]

# %%
data = pd.concat([pd.json_normalize(decoded_logs), pd.json_normalize(data['decoded_input'])], axis=1)

# %%
data.columns

# %%
data

# %%
data = data[~data['args.id'].isna()]

# %%
data = data.reset_index(drop=True)

# %%
data

# %%
data.iloc[0]

# %%
data['args.id']

# %%
prefix_mask = (1 << 248) - 1
prefix = data['args.id'].values >> 248

# %%
maturity_timestamp = prefix & prefix_mask

# %%
trade_type = pd.DataFrame(prefix).apply(lambda x: hyperdrive_assets.AssetIdPrefix(x.values).name, axis=1)

# %%
data['prefix'] = prefix
data['maturity_timestamp'] = maturity_timestamp
data['trade_type'] = trade_type

# %%
columns = [
    'event', 
    'address', 
    'transactionHash', 
    'blockNumber', 
    'blockHash', 
    'logIndex', 
    'transactionIndex', 
    'args.operator', 
    'args.from', 
    'args.to', 
    'args.id', 
    'args.value', 
    'prefix',
    'maturity_timestamp',
    'trade_type',
]

# %%
rename_columns = [
    'event_name',
    'contract_address',
    'transaction_hash',
    'block_number',
    'block_hash',
    'log_index',
    'transaction_index',
    'operator',
    'from',
    'to',
    'id',
    'value',
    'prefix',
    'maturity_timestamp',
    'trade_type',
]

# %%
renamed_data = data[columns]

# %%
renamed_data

# %%
renamed_data.columns = rename_columns

# %%
renamed_data

# %%
#block_info_data
data.columns

# %%
block_info_data = data[[c for c in data.columns if 'block_info.' in c]]
block_info_data


# %%
block_info_data.columns = [
    "share_reserves",
    "bond_reserves",
    "lp_total_supply",
    "share_price",
    "longs_outstanding",
    "average_maturity_time",
    "long_base_volume",
    "shorts_outstanding",
    "short_average_maturity_time",
    "short_base_volume",
]

# %%
block_info_data

# %%
trade_data = pd.concat([renamed_data, block_info_data], axis=1)
trade_data


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
    print(f"{trades.columns=}")
    share_price = trades.share_price
    
    # TODO: remove restriction forcing Wallet index to be an int (issue #415)
    if add_to_existing_wallet is None:
        wallet = Wallet(
            address=index,
            balance=types.Quantity(
                amount=FixedPoint(scaled_value=0), unit=types.TokenType.BASE
            ),
        )
    else:
        wallet = add_to_existing_wallet
    
    position_id = trades["id"]
    trades_in_position = ((trades["from"] == address) | (trades["to"] == address)) & (
        trades["id"] == position_id
    )
    
    positive_balance = int(trades.loc[(trades_in_position) & (trades["to"] == address), "value"].sum())
    negative_balance = int(trades.loc[(trades_in_position) & (trades["from"] == address), "value"].sum())
    balance = positive_balance - negative_balance
    
    asset_prefix, maturity = hyperdrive_assets.decode_asset_id(position_id)
    asset_type = hyperdrive_assets.AssetIdPrefix(asset_prefix).name
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
                new_open_share_price = previous_balance * previous_share_price \
                    + marginal_position_change * marginal_open_share_price \
                    / ( previous_balance + marginal_position_change )
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
trade_data.columns

# %%
agents = trade_data['operator'].value_counts().index.tolist()

# %%
# agent_trades = {a: trade_data[trade_data['operator'] == a] for a in agents}
agent_wallets = {
    a: Wallet(
        address=agents.index(a),
        balance=types.Quantity(amount=FixedPoint(0), unit=types.TokenType.BASE),
    )
    for a in agents
    }

for a,v in agent_wallets.items():
    print(v)

# %%
# for index, (address, trades) in enumerate(agent_trades.items()):
for idx,row in trade_data.iterrows():
    agent = row.operator
    # get their wallet
    wallet = agent_wallets[agent]

    marginal_trades = pd.DataFrame(row)
    print(f"{marginal_trades=}")

    # pass in one trade at a time, and get out the updated wallet
    agent_wallets[agent] = get_wallet_from_onchain_trade_info(address=agent, trades = marginal_trades, index=agents.index(agent), add_to_existing_wallet=agent_wallets[agent],)
    print(f"agent {agent}'s wallet is now: {agent_wallets[agent]}")

# %%
onchain_trade_info = get_on_chain_trade_info_from_file(trade_data)

# %%
onchain_trade_info

# %%
for row in 

# %%
onchain_trade_info.apply(lambda x: get_wallet_from_onchain_trade_info(address="0x841958527DFe4499fA234A1Acc247b29C90d1C21", info = x, index=0)

# %%

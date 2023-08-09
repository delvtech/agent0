"""A script to calculate the leaderboard from postgres
This takes into account that withdrawal shares were not
gathered in the database.
"""
from __future__ import annotations

import pandas as pd
from chainsync.analysis import calc_total_returns
from chainsync.base import db_interface
from chainsync.dashboard import address_to_username, build_leaderboard, get_user_lookup
from dotenv import load_dotenv
from sqlalchemy.sql import text

# pylint: disable=invalid-name

# Connect to postgres
load_dotenv()

# Can't use existing postgres code due to mismatch of schema
# so we do direct queries here
engine = db_interface.initialize_engine()

# sql queries
config_query = text("select * from poolconfig;")
pool_info_query = text("select * from poolinfo;")
txn_query = text("select * from transactions;")
wallet_query = text("select * from walletinfo;")
agents_query = text('select distinct "walletAddress" from walletinfo;')
user_map_query = text("select * from usermap;")
# TODO get user lookup

with engine.connect() as conn:
    config_data = pd.read_sql(config_query, con=conn, coerce_float=False).iloc[0]
    pool_info_data = pd.read_sql(pool_info_query, con=conn, coerce_float=False)
    txn_data = pd.read_sql(txn_query, con=conn, coerce_float=False)
    wallet_data = pd.read_sql(wallet_query, con=conn, coerce_float=False)
    agents_data = pd.read_sql(agents_query, con=conn, coerce_float=False)["walletAddress"].tolist()
    user_map_data = pd.read_sql(user_map_query, con=conn, coerce_float=False)

user_lookup = get_user_lookup(agents_data, user_map_data)

# TODO fix input invTimeStretch to be unscaled in ingestion into postgres
config_data["invTimeStretch"] = config_data["invTimeStretch"] / 10**18

# Provide a lookup table for difference in bases given a block number and an address
wallet_data = wallet_data.sort_values("blockNumber")
# Filter wallet data for only base
base_delta_lookup = wallet_data[wallet_data["tokenType"] == "BASE"].copy()
base_groups = base_delta_lookup.groupby(["walletAddress", "tokenType"])
base_diffs = base_groups["tokenValue"].apply("diff").fillna(0)
base_delta_lookup["delta"] = base_diffs
base_delta_lookup = base_delta_lookup.set_index(["blockNumber", "walletAddress"])["delta"]
# Change walletAddress to match column name in txns
base_delta_lookup.index.names = ["blockNumber", "event_operator"]

# Get all necessary information from txn_data
# Need to calculate wallet deltas using txn data
txn_data = txn_data[
    [
        "blockNumber",
        "input_method",
        "event_operator",
        "event_maturity_time",
        "input_params_contribution",
        "input_params_baseAmount",
        "input_params_bondAmount",
        "input_params_shares",
        "event_value",
    ]
]
# The columns to keep when calculating deltas from txn
keep_columns = ["blockNumber", "input_method", "event_operator", "event_maturity_time"]

# Drop all txns without an event operator
txn_data = txn_data.dropna(axis=0, subset=["event_operator"])

# Append other relevant information from poolinfo and poolconfig here
txn_data["share_price"] = pool_info_data.set_index("blockNumber").loc[txn_data["blockNumber"], "sharePrice"].values

wallet_deltas = []

# Calculate how many transactions each agent made per block for assertion check
txn_counts = txn_data.value_counts(["blockNumber", "event_operator"])

# Add liquidity transactions
txn = txn_data[txn_data["input_method"] == "addLiquidity"]
token_delta = txn[keep_columns].copy()
token_delta["baseTokenType"] = "LP"
token_delta["tokenType"] = "LP"
token_delta["delta"] = txn["event_value"]
base_delta = txn[keep_columns].copy()
base_delta["baseTokenType"] = "BASE"
base_delta["tokenType"] = "BASE"
base_delta["delta"] = -txn["input_params_contribution"]
wallet_deltas.extend([token_delta, base_delta])

# Open long transactions
txn = txn_data[txn_data["input_method"] == "openLong"]
token_delta = txn[keep_columns].copy()
token_delta["baseTokenType"] = "LONG"
token_delta["tokenType"] = "LONG-" + txn["event_maturity_time"].astype(int).astype(str)
token_delta["delta"] = txn["event_value"]
base_delta = txn[keep_columns].copy()
base_delta["baseTokenType"] = "BASE"
base_delta["tokenType"] = "BASE"
base_delta["delta"] = -txn["input_params_baseAmount"]
wallet_deltas.extend([token_delta, base_delta])

# Open short transactions
txn = txn_data[txn_data["input_method"] == "openShort"]
token_delta = txn[keep_columns].copy()
token_delta["baseTokenType"] = "SHORT"
token_delta["tokenType"] = "SHORT-" + txn["event_maturity_time"].astype(int).astype(str)
token_delta["delta"] = txn["input_params_bondAmount"]
base_delta = txn[keep_columns].copy()
base_delta["baseTokenType"] = "BASE"
base_delta["tokenType"] = "BASE"
# Calculate base delta through a lookup of the wallet info table
# Note that this only works if no other transactions were made by the event operator
# at this time block, so we make an assertion here

# There's one time where a user opens and closes a long in the same block. In this case,
# we ignore the base delta for this open short, and calculate the total base delta during
# close long
txn = txn.set_index(["blockNumber", "event_operator"])
keep_base_delta_idx = txn_counts.loc[txn.index] <= 1
# Filter both txn and base_delta based on the case above
txn = txn[keep_base_delta_idx]
base_delta = base_delta[keep_base_delta_idx.values]
assert (txn_counts.loc[txn.index] <= 1).all()
# Look up difference in base from walletinfo for this txn
base_delta["delta"] = base_delta_lookup.loc[txn.index].values
wallet_deltas.extend([token_delta, base_delta])

# Remove liquidity
txn = txn_data[txn_data["input_method"] == "removeLiquidity"]
token_delta = txn[keep_columns].copy()
token_delta["baseTokenType"] = "LP"
token_delta["tokenType"] = "LP"
token_delta["delta"] = -txn["input_params_shares"]
base_delta = txn[keep_columns].copy()
base_delta["baseTokenType"] = "BASE"
base_delta["tokenType"] = "BASE"
# We calculate base delta directly from the amount of LP tokens that were removed
# There is a bit of inaccuracy here due to difference in share price here versus
# when withdrawal shares were actually withdrawal, but we hope that the difference
# is negligible
base_delta["delta"] = -token_delta["delta"] * txn["share_price"]
# base_delta["delta"] = -txn["input_params_baseAmount"]
wallet_deltas.extend([token_delta, base_delta])


# Close Long
txn = txn_data[txn_data["input_method"] == "closeLong"]
token_delta = txn[keep_columns].copy()
token_delta["baseTokenType"] = "LONG"
token_delta["tokenType"] = "LONG-" + txn["event_maturity_time"].astype(int).astype(str)
token_delta["delta"] = -txn["input_params_bondAmount"]
base_delta = txn[keep_columns].copy()
base_delta["baseTokenType"] = "BASE"
base_delta["tokenType"] = "BASE"
# Calculate base delta through a lookup of the wallet info table
# Note: There's one time where a user opens and closes a long in the same block. In this case,
# we ignore the base delta for this open short, and calculate the total base delta during
# close long. Hence, we don't assert that the user makes one trade only here
txn = txn.set_index(["blockNumber", "event_operator"])
# Look up difference in base from walletinfo for this txn
base_delta_values = base_delta_lookup.loc[txn.index]
# Drop duplicate indices of this series
base_delta_values = base_delta_values[~base_delta_values.index.duplicated(keep="first")]
base_delta["delta"] = base_delta_values.values
wallet_deltas.extend([token_delta, base_delta])

# Close Short
txn = txn_data[txn_data["input_method"] == "closeShort"]
token_delta = txn[keep_columns].copy()
token_delta["baseTokenType"] = "SHORT"
token_delta["tokenType"] = "SHORT-" + txn["event_maturity_time"].astype(int).astype(str)
token_delta["delta"] = -txn["input_params_bondAmount"]
base_delta = txn[keep_columns].copy()
base_delta["baseTokenType"] = "BASE"
base_delta["tokenType"] = "BASE"
# Calculate base delta through a lookup of the wallet info table
# Note that this only works if no other transactions were made by the event operator
# at this time block, so we make an assertion here
txn = txn.set_index(["blockNumber", "event_operator"])
assert (txn_counts.loc[txn.index] <= 1).all()
# Look up difference in base from walletinfo for this txn
base_delta["delta"] = base_delta_lookup.loc[txn.index].values
wallet_deltas.extend([token_delta, base_delta])

all_wallet_deltas = pd.concat(wallet_deltas, axis=0)
# Set wallet_delta columns to match expected columns
all_wallet_deltas.columns = [
    "blockNumber",
    "input_method",
    "walletAddress",
    "maturityTime",
    "baseTokenType",
    "tokenType",
    "delta",
]

# The following address closes LP without any corresponding open LP
# Also this address isn't registered anywhere
# Ignore it in all_wallet_deltas
all_wallet_deltas = all_wallet_deltas[
    all_wallet_deltas["walletAddress"] != "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
]

current_returns = calc_total_returns(config_data, pool_info_data, all_wallet_deltas)[0]
assert isinstance(current_returns, pd.Series)
comb_rank, ind_rank = build_leaderboard(current_returns, user_lookup)

# TODO External transfers of base is getting captured, so need to undo this
# Run 1: No change needed
# Run 2: Sheng Lundquist (click) + 500,000
# Run 3: Dylan Paiton (click) - 1,000,000, Giovanni Effio (click) - 1,000,000
database_name = str(engine.url.database)
comb_rank.to_csv("../comb_rank_" + database_name + ".csv")
ind_rank.to_csv("../ind_rank_" + database_name + ".csv")

# Map wallet_addresses to users for wallet deltas
usernames = address_to_username(user_lookup, all_wallet_deltas["walletAddress"])
all_wallet_deltas.insert(1, "username", usernames.values.tolist())

all_wallet_deltas = all_wallet_deltas.set_index("blockNumber")
select_pool_info = pool_info_data.set_index("blockNumber").loc[all_wallet_deltas.index]

out_wallet_data = pd.concat([all_wallet_deltas, select_pool_info], axis=1)

# Move timestamp column to front
timestamp = out_wallet_data.pop("timestamp")
out_wallet_data.insert(0, "timestamp", timestamp)
out_wallet_data = out_wallet_data.sort_index()

out_wallet_data.to_csv("../wallet_deltas_" + database_name + ".csv")

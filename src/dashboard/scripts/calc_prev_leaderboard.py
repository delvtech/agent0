"""A script to calculate the leaderboard from postgres
This takes into account that withdrawal shares were not
gathered in the database
"""
from __future__ import annotations

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy.sql import text

from src.dashboard.calc_pnl import calc_total_returns
from src.data import postgres

# pylint: disable=invalid-name


def get_user_lookup(agents, user_map) -> pd.DataFrame:
    """Generate username to agents mapping."""
    # Usernames in postgres are bots
    user_map["username"] = user_map["username"] + " (bots)"

    click_map = get_click_addresses()
    user_map = pd.concat([click_map, user_map], axis=0)

    # Generate a lookup of users -> address, taking into account that some addresses don't have users
    # Reindex looks up agent addresses against user_map, adding nans if it doesn't exist
    options_map = user_map.set_index("address").reindex(agents)

    # Set username as address if agent doesn't exist
    na_idx = options_map["username"].isna()
    # If there are any nan usernames, set address itself as username
    if na_idx.any():
        options_map[na_idx] = options_map.index[na_idx]
    return options_map.reset_index()


def combine_usernames(username: pd.Series) -> pd.DataFrame:
    """Map usernames to a single user (e.g., combine click with bots)."""
    # Hard coded mapping:
    user_mapping = {
        "Charles St. Louis (click)": "Charles St. Louis",
        "Alim Khamisa (click)": "Alim Khamisa",
        "Danny Delott (click)": "Danny Delott",
        "Gregory Lisa (click)": "Gregory Lisa",
        "Jonny Rhea (click)": "Jonny Rhea",
        "Matt Brown (click)": "Matt Brown",
        "Giovanni Effio (click)": "Giovanni Effio",
        "Mihai Cosma (click)": "Mihai Cosma",
        "Ryan Goree (click)": "Ryan Goree",
        "Alex Towle (click)": "Alex Towle",
        "Adelina Ruffolo (click)": "Adelina Ruffolo",
        "Jacob Arruda (click)": "Jacob Arruda",
        "Dylan Paiton (click)": "Dylan Paiton",
        "Sheng Lundquist (click)": "Sheng Lundquist",
        "ControlC Schmidt (click)": "ControlC Schmidt",
        "George Towle (click)": "George Towle",
        "Jack Burrus (click)": "Jack Burrus",
        "Jordan J (click)": "Jordan J",
        # Bot accounts
        "slundquist (bots)": "Sheng Lundquist",
    }
    user_mapping = pd.DataFrame.from_dict(user_mapping, orient="index")
    user_mapping.columns = ["user"]
    # Use merge in case mapping doesn't exist
    username_column = username.name
    user = username.to_frame().merge(user_mapping, how="left", left_on=username_column, right_index=True)
    return user


def get_leaderboard(pnl: pd.Series, lookup: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rank users by PNL, individually and bomined across their accounts."""
    pnl = pnl.reset_index()  # type: ignore
    wallet_usernames = address_to_username(lookup, pnl["walletAddress"])
    pnl.insert(1, "username", wallet_usernames.values.tolist())
    # Hard coded funding provider from migration account
    migration_addr = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    # Don't show this account
    pnl = pnl[pnl["walletAddress"] != migration_addr]
    # Rank based on pnl
    user = combine_usernames(pnl["username"])
    pnl["user"] = user["user"].values

    ind_leaderboard = (
        pnl[["username", "walletAddress", "pnl"]]
        .sort_values("pnl", ascending=False)  # type: ignore
        .reset_index(drop=True)
    )
    comb_leaderboard = (
        pnl[["user", "pnl"]].groupby("user")["pnl"].sum().reset_index().sort_values("pnl", ascending=False)
    ).reset_index(drop=True)

    return (comb_leaderboard, ind_leaderboard)


def get_click_addresses() -> pd.DataFrame:
    """Returns a dataframe of hard coded click addresses."""
    addresses = {
        "0x004dfC2dBA6573fa4dFb1E86e3723e1070C0CfdE": "Charles St. Louis (click)",
        "0x005182C62DA59Ff202D53d6E42Cef6585eBF9617": "Alim Khamisa (click)",
        "0x005BB73FddB8CE049eE366b50d2f48763E9Dc0De": "Danny Delott (click)",
        "0x0065291E64E40FF740aE833BE2F68F536A742b70": "Gregory Lisa (click)",
        "0x0076b154e60BF0E9088FcebAAbd4A778deC5ce2c": "Jonny Rhea (click)",
        "0x00860d89A40a5B4835a3d498fC1052De04996de6": "Matt Brown (click)",
        "0x00905A77Dc202e618d15d1a04Bc340820F99d7C4": "Giovanni Effio (click)",
        "0x009ef846DcbaA903464635B0dF2574CBEE66caDd": "Mihai Cosma (click)",
        "0x00D5E029aFCE62738fa01EdCA21c9A4bAeabd434": "Ryan Goree (click)",
        "0x020A6F562884395A7dA2be0b607Bf824546699e2": "Alex Towle (click)",
        "0x020a898437E9c9DCdF3c2ffdDB94E759C0DAdFB6": "Adelina Ruffolo (click)",
        "0x020b42c1E3665d14275E2823bCef737015c7f787": "Jacob Arruda (click)",
        "0x02147558D39cE51e19de3A2E1e5b7c8ff2778829": "Dylan Paiton (click)",
        "0x021f1Bbd2Ec870FB150bBCAdaaA1F85DFd72407C": "Sheng Lundquist (click)",
        "0x02237E07b7Ac07A17E1bdEc720722cb568f22840": "ControlC Schmidt (click)",
        "0x022ca016Dc7af612e9A8c5c0e344585De53E9667": "George Towle (click)",
        "0x0235037B42b4c0575c2575D50D700dD558098b78": "Jack Burrus (click)",
        "0x0238811B058bA876Ae5F79cFbCAcCfA1c7e67879": "Jordan J (click)",
    }
    addresses = pd.DataFrame.from_dict(addresses, orient="index")
    addresses = addresses.reset_index()
    addresses.columns = ["address", "username"]

    return addresses


def address_to_username(lookup: pd.DataFrame, selected_list: pd.Series) -> pd.Series:
    """Look up selected users/addrs to all addresses.

    Arguments
    ---------
    lookup: pd.DataFrame
        The lookup dataframe from `get_user_lookup` call
    selected_list: list[str]
        A list of addresses to look up usernames to

    Returns
    -------
    list[str]
        A list of usernames based on selected_list
    """
    selected_list_column = selected_list.name
    out = selected_list.to_frame().merge(lookup, how="left", left_on=selected_list_column, right_on="address")
    return out["username"]


# Connect to postgres
load_dotenv()

# Can't use existing postgres code due to mismatch of schema
# so we do direct queries here
engine = postgres.initialize_engine()

# sql queries
config_query = text("select * from poolconfig;")
pool_info_query = text("select * from poolinfo;")
txn_query = text("select * from transactions;")
wallet_query = text("select * from walletinfo;")
agents_query = text('select distinct "walletAddress" from walletinfo;')
user_map_query = text("select * from usermap;")
# TODO get user lookup

with engine.connect() as conn:
    config_data = pd.read_sql(config_query, con=conn).iloc[0]
    pool_info_data = pd.read_sql(pool_info_query, con=conn)
    txn_data = pd.read_sql(txn_query, con=conn)
    wallet_data = pd.read_sql(wallet_query, con=conn)
    agents_data = pd.read_sql(agents_query, con=conn)["walletAddress"].tolist()
    user_map_data = pd.read_sql(user_map_query, con=conn)

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

current_returns = calc_total_returns(config_data, pool_info_data, all_wallet_deltas)
assert isinstance(current_returns, pd.Series)
comb_rank, ind_rank = get_leaderboard(current_returns, user_lookup)

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
all_wallet_deltas.to_csv("../wallet_deltas_" + database_name + ".csv")

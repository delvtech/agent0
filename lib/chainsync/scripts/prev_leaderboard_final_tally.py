"""A script to calculate the leaderboard from postgres
This takes into account that withdrawal shares were not
gathered in the database
"""
from __future__ import annotations

import pandas as pd


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


comb_rank_csvs = [
    "../comb_rank_devnet_test.csv",
    "../comb_rank_devnet_test_2.csv",
    "../comb_rank_devnet_test_3.csv",
]

ind_rank_csvs = [
    "../ind_rank_devnet_test.csv",
    "../ind_rank_devnet_test_2.csv",
    "../ind_rank_devnet_test_3.csv",
]

wallet_delta_csvs = [
    "../wallet_deltas_devnet_test.csv",
    "../wallet_deltas_devnet_test_2.csv",
    "../wallet_deltas_devnet_test_3.csv",
]


comb_rank = [pd.read_csv(csv).set_index("user")["pnl"] for csv in comb_rank_csvs]
ind_rank = [pd.read_csv(csv).set_index(["username", "walletAddress"])["pnl"] for csv in ind_rank_csvs]
wallet_deltas = [pd.read_csv(csv).sort_values("blockNumber") for csv in wallet_delta_csvs]

# Timestamp adjustments, converting to PDT
wallet_deltas[0]["timestamp"] = (
    pd.to_datetime(wallet_deltas[0]["timestamp"]) - pd.to_timedelta("7 hours")
).dt.tz_localize("US/Pacific")

wallet_deltas[1]["timestamp"] = (
    pd.to_datetime(wallet_deltas[1]["timestamp"]) - pd.to_timedelta("7 hours")
).dt.tz_localize("US/Pacific")

wallet_deltas[2]["timestamp"] = (
    pd.to_datetime(wallet_deltas[2]["timestamp"]) - pd.to_timedelta("7 hours")
).dt.tz_localize("US/Pacific")


# External transfers of base is getting captured, so need to undo this
# Adjustments:
# Run 1: No change needed
# Run 2: Sheng Lundquist (click) + 500,000
# Run 3: Dylan Paiton (click) - 1,000,000, Giovanni Effio (click) - 1,000,000

# 500k transfer to bots captured in base delta, adjustment here
comb_rank[1].loc["Sheng Lundquist"] += 500000
ind_rank[1].loc[("Sheng Lundquist (click)", "0x021f1Bbd2Ec870FB150bBCAdaaA1F85DFd72407C")] += 500000  # type: ignore
# Delta OI
wallet_deltas[1].loc[
    (wallet_deltas[1]["username"] == "Sheng Lundquist (click)")
    & (wallet_deltas[1]["blockNumber"] == 13293)
    & (wallet_deltas[1]["tokenType"] == "BASE"),
    "delta",
] += 500000


# 1 million injection of base captured due to these users making a trade before the injection
# then after the injection. Adjustment here
comb_rank[2].loc["Dylan Paiton"] -= 1000000
ind_rank[2].loc[("Dylan Paiton (click)", "0x02147558D39cE51e19de3A2E1e5b7c8ff2778829")] -= 1000000  # type: ignore
wallet_deltas[2].loc[
    (wallet_deltas[2]["username"] == "Dylan Paiton (click)")
    & (wallet_deltas[2]["blockNumber"] == 39048)
    & (wallet_deltas[2]["tokenType"] == "BASE"),
    "delta",
] -= 1000000


comb_rank[2].loc["Giovanni Effio"] -= 1000000
ind_rank[2].loc[("Giovanni Effio (click)", "0x00905A77Dc202e618d15d1a04Bc340820F99d7C4")] -= 1000000  # type: ignore
wallet_deltas[2].loc[
    (wallet_deltas[2]["username"] == "Giovanni Effio (click)")
    & (wallet_deltas[2]["blockNumber"] == 23289)
    & (wallet_deltas[2]["tokenType"] == "BASE"),
    "delta",
] -= 1000000


total_comb_rank = pd.concat(comb_rank, axis=0).groupby("user").sum().sort_values(ascending=False)
total_ind_rank = pd.concat(ind_rank, axis=0).groupby(["username", "walletAddress"]).sum().sort_values(ascending=False)

# Find out who still held positions during bank run on last run
final_delta = wallet_deltas[2].groupby(["walletAddress", "tokenType"]).agg({"username": "first", "delta": "sum"})
burn_positions = final_delta[(final_delta.reset_index()["tokenType"] != "BASE").values]
# Remove zero deltas
burn_positions = burn_positions[(burn_positions["delta"].abs() >= 1e-9)]
burn_positions.to_csv("../burned_positions.csv")

adj_ind_rank_2 = final_delta[(final_delta.reset_index()["tokenType"] == "BASE").values].reset_index()[
    ["username", "walletAddress", "delta"]
]
adj_ind_rank_2.columns = ["username", "walletAddress", "pnl"]
adj_ind_rank_2 = adj_ind_rank_2.sort_values("pnl", ascending=False).set_index(["username", "walletAddress"])["pnl"]

adj_ind_rank_2.to_csv("../adj_ind_rank_2.csv")

# Calculate adjusted final ind and combined rank
adj_total_ind_rank = (
    pd.concat([ind_rank[0], ind_rank[1], adj_ind_rank_2], axis=0).groupby(["username", "walletAddress"]).sum()
).sort_values(ascending=False)

adj_total_ind_rank.to_csv("../adj_final_ind_rank.csv")

users = combine_usernames(adj_total_ind_rank.reset_index()["username"])["user"]
adj_total_comb_rank = adj_total_ind_rank.to_frame()
adj_total_comb_rank["user"] = users.values

adj_total_comb_rank = adj_total_comb_rank.groupby("user")["pnl"].sum().sort_values(ascending=False)

adj_total_comb_rank.to_csv("../adj_final_comb_rank.csv")

total_comb_rank.to_csv("../final_comb_rank.csv")
total_ind_rank.to_csv("../final_ind_rank.csv")

# Save back out the final wallet_deltas to csv
[rank.sort_values(ascending=False).to_csv("../comb_rank_" + str(idx) + ".csv") for idx, rank in enumerate(comb_rank)]
[rank.sort_values(ascending=False).to_csv("../ind_rank_" + str(idx) + ".csv") for idx, rank in enumerate(ind_rank)]
[delta.to_csv("../final_trades_" + str(idx) + ".csv", index=False) for idx, delta in enumerate(wallet_deltas)]

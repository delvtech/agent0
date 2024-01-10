# %%
"""Run experiments of economic activity.

We want to better understand return profiles of participants in Hyperdrive.
To do so, we run various scenarios of plausible economic activity.
We target a certain amount of daily activity, as a percentage of the liquidity provided.
That trading activity is executed by a random agent named Rob.
The liquidity is provided by an agent named Larry.
At the end, we close out all positions, and evaluate results based off the WETH in their wallets.
"""

import datetime
import os
import sys
import time
from copy import deepcopy
from dataclasses import dataclass, field, fields
from typing import NamedTuple

from dotenv import load_dotenv
import numpy as np
import pandas as pd
from fixedpointmath import FixedPoint
from matplotlib import pyplot as plt
import wandb

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain

# pylint: disable=bare-except
# ruff: noqa: A001 (allow shadowing a python builtin)
# using the variable "max"
# pylint: disable=redefined-builtin
# don't make me use upper case variable names
# pylint: disable=invalid-name
# don't need docstrings in scripts
# pylint: disable=missing-function-docstring,missing-return-doc,missing-return-type-doc,bad-docstring-quotes


# %%
# check what environment we're running in
def running_interactive():
    try:
        from IPython.core.getipython import get_ipython  # pylint: disable=import-outside-toplevel

        return bool("ipykernel" in sys.modules and get_ipython())
    except ImportError:
        return False


def running_wandb():
    # Check for a specific wandb environment variable
    # For example, 'WANDB_RUN_ID' is set by wandb during a run
    return "WANDB_RUN_ID" in os.environ


if RUNNING_INTERACTIVE := running_interactive():
    from IPython.display import display  # pylint: disable=import-outside-toplevel

    print("Running in interactive mode.")
else:  # being run from the terminal or something similar
    display = print  # pylint: disable=redefined-builtin,unused-import
    print("Running in non-interactive mode.")

if RUNNING_WANDB := running_wandb():
    print("Running inside a wandb environment.")
else:
    print("Not running inside a wandb environment.")


# %%
# config
cols = ["block_number", "username", "position", "pnl"]


@dataclass
class ExperimentConfig:  # pylint: disable=too-many-instance-attributes,missing-class-docstring
    db_port: int = 5_433
    chain_port: int = 10_000
    daily_volume_percentage_of_liquidity: float = 0.01  # 1%
    term_days: int = 20  # 20 days for quick testing purposes. actual experiment are 365 days.
    float_fmt: str = ",.0f"
    display_cols: list[str] = field(default_factory=lambda: cols + ["base_token_type", "maturity_time"])
    display_cols_with_hpr: list[str] = field(default_factory=lambda: cols + ["hpr", "apr"])
    amount_of_liquidity: int = 10_000_000
    fixed_rate: float = 0.035  # 3.5%
    curve_fee: FixedPoint = FixedPoint("0.01")  # 1%, 10% default
    flat_fee: FixedPoint = FixedPoint("0.0001")  # 1bps, 5bps default
    governance_fee: FixedPoint = FixedPoint("0.1")  # 10%, 15% default
    randseed: int = 0
    term_seconds: int = 0
    starting_fixed_rate: FixedPoint = FixedPoint(0)
    starting_variable_rate: FixedPoint = FixedPoint(0)
    calc_pnl: bool = False

    def calculate_values(self):
        self.term_seconds: int = 60 * 60 * 24 * self.term_days
        # used to scale up to the equivalent of a year
        scaling_ratio = 365 / self.term_days
        # this interest rate gives us the same price as a 3.% fixed rate for 1 year
        rate_required_for_same_price: float = min(1, self.fixed_rate * scaling_ratio)
        self.starting_fixed_rate: FixedPoint = FixedPoint(rate_required_for_same_price)
        self.starting_variable_rate: FixedPoint = FixedPoint(rate_required_for_same_price)


def safe_cast(_type: type, _value: str, _debug: bool = False):
    if _debug:
        print(f"trying to cast {_value} to {_type}")
    return_value = _value
    if _type == int:
        return_value = int(_value)
    if _type == float:
        return_value = float(_value)
    if _type == bool:
        return_value = _value.lower() in {"true", "1", "yes"}
    if _type == FixedPoint:
        return_value = FixedPoint(_value)
    if _debug:
        print(f"  result: {_value} of {type(return_value)}")
    return return_value


exp = ExperimentConfig()
field_names = [f.name for f in fields(exp)]
# update initial values from environment
print("=== START IMPORTING ENVIRONMENT ===")
load_dotenv("parameters.env")
for key, value in os.environ.items():
    lkey = key.lower()
    if lkey in field_names:
        attribute_type = exp.__annotations__[lkey]  # pylint: disable=no-member
        setattr(exp, lkey, safe_cast(attribute_type, value))
        # check that it worked
        print(f"  {lkey} = {getattr(exp, lkey)}")
        assert getattr(exp, lkey) == safe_cast(attribute_type, value)
print("=== DONE IMPORTING ENVIRONMENT ===")

# update calculated values
exp.calculate_values()
rng = np.random.default_rng(seed=int(exp.randseed))

# %%
# set up chain
print(f"Experiment ID {exp.chain_port-10_000}")
chain = LocalChain(LocalChain.Config(db_port=exp.db_port, chain_port=exp.chain_port))

# %%
# Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
config = InteractiveHyperdrive.Config(
    position_duration=exp.term_seconds,
    checkpoint_duration=60 * 60 * 24,  # 1 day
    initial_liquidity=FixedPoint(20),
    initial_fixed_rate=exp.starting_fixed_rate,
    initial_variable_rate=exp.starting_variable_rate,
    curve_fee=exp.curve_fee,
    flat_fee=exp.flat_fee,
    governance_lp_fee=exp.governance_fee,
    calc_pnl=exp.calc_pnl,
)
MINIMUM_TRANSACTION_AMOUNT = config.minimum_transaction_amount
for k, v in config.__dict__.items():
    print(f"{k:26} : {v}")
print(f"{'term length':27}: {exp.term_days}")
interactive_hyperdrive = InteractiveHyperdrive(chain, config)
print(f"spot price = {interactive_hyperdrive.hyperdrive_interface.calc_spot_price()}")

# %%
# set up agents
larry = interactive_hyperdrive.init_agent(base=FixedPoint(exp.amount_of_liquidity), name="larry")
larry.add_liquidity(base=FixedPoint(exp.amount_of_liquidity))  # 10 million
rob = interactive_hyperdrive.init_agent(base=FixedPoint(exp.amount_of_liquidity), name="rob")
# this verifies that spot price does not change after adding liquidity
print(f"spot price after adding liquidity = {interactive_hyperdrive.hyperdrive_interface.calc_spot_price()}")

# %%
# do some trades
Max = NamedTuple("Max", [("base", FixedPoint), ("bonds", FixedPoint)])
GetMax = NamedTuple("GetMax", [("long", Max), ("short", Max)])

start_time = time.time()


def get_max(
    _interactive_hyperdrive: InteractiveHyperdrive, _share_price: FixedPoint, _current_base: FixedPoint
) -> GetMax:
    """Get max trade sizes.

    Returns
    -------
    GetMax
        A NamedTuple containing the max long in base, max long in bonds, max short in bonds, and max short in base.
    """
    max_long_base = _interactive_hyperdrive.hyperdrive_interface.calc_max_long(budget=_current_base)
    max_long_shares = _interactive_hyperdrive.hyperdrive_interface.calc_shares_in_given_bonds_out_down(max_long_base)
    max_long_bonds = max_long_shares * _share_price
    max_short_bonds = FixedPoint(0)
    try:  # sourcery skip: do-not-use-bare-except
        max_short_bonds = _interactive_hyperdrive.hyperdrive_interface.calc_max_short(budget=_current_base)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print("Error calculating max short bonds: %s. ", exc)
    max_short_shares = _interactive_hyperdrive.hyperdrive_interface.calc_shares_out_given_bonds_in_down(max_short_bonds)
    max_short_base = max_short_shares * _share_price
    return GetMax(
        Max(max_long_base, max_long_bonds),
        Max(max_short_base, max_short_bonds),
    )


# sourcery skip: avoid-builtin-shadow, do-not-use-bare-except, invert-any-all,
# remove-unnecessary-else, swap-if-else-branches
for day in range(exp.term_days):
    amount_to_trade_base = FixedPoint(exp.amount_of_liquidity * exp.daily_volume_percentage_of_liquidity)
    while amount_to_trade_base > MINIMUM_TRANSACTION_AMOUNT:
        spot_price = interactive_hyperdrive.hyperdrive_interface.calc_spot_price()
        share_price = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.share_price
        max = None
        wallet = rob.wallet
        event = None
        if rng.random() < 0.5:  # go long 50% of the time
            if len(wallet.shorts) > 0:  # check if we have shorts, and close them if we do
                for maturity_time, short in wallet.shorts.copy().items():
                    max = get_max(interactive_hyperdrive, share_price, rob.wallet.balance.amount)
                    amount_to_trade_bonds = (
                        interactive_hyperdrive.hyperdrive_interface.calc_bonds_out_given_shares_in_down(
                            amount_to_trade_base / share_price
                        )
                    )
                    trade_size_bonds = min(amount_to_trade_bonds, short.balance, max.long.bonds)
                    if trade_size_bonds > MINIMUM_TRANSACTION_AMOUNT:
                        event = rob.close_short(maturity_time, trade_size_bonds)
                        amount_to_trade_base -= event.base_amount
                    if amount_to_trade_base <= 0:
                        break  # stop looping across shorts if we've traded enough
            if amount_to_trade_base > 0:
                max = get_max(interactive_hyperdrive, share_price, rob.wallet.balance.amount)
                trade_size_base = min(amount_to_trade_base, max.long.base)
                if trade_size_base > MINIMUM_TRANSACTION_AMOUNT:
                    event = rob.open_long(trade_size_base)
                    amount_to_trade_base -= event.base_amount
        else:  # go short 50% of the time
            if len(wallet.longs) > 0:  # check if we have longs, and close them if we do
                for maturity_time, long in wallet.longs.copy().items():
                    max = get_max(interactive_hyperdrive, share_price, rob.wallet.balance.amount)
                    amount_to_trade_bonds = (
                        interactive_hyperdrive.hyperdrive_interface.calc_bonds_out_given_shares_in_down(
                            amount_to_trade_base / share_price
                        )
                    )
                    trade_size_bonds = min(amount_to_trade_bonds, long.balance, max.short.bonds)
                    if trade_size_bonds > MINIMUM_TRANSACTION_AMOUNT:
                        event = rob.close_long(maturity_time, trade_size_bonds)
                        amount_to_trade_base -= event.base_amount
                    if amount_to_trade_base <= 0:
                        break  # stop looping across longs if we've traded enough
            if amount_to_trade_base > 0:
                max = get_max(interactive_hyperdrive, share_price, rob.wallet.balance.amount)
                amount_to_trade_bonds = interactive_hyperdrive.hyperdrive_interface.calc_bonds_out_given_shares_in_down(
                    amount_to_trade_base / share_price
                )
                trade_size_bonds = min(amount_to_trade_bonds, max.short.bonds)
                if trade_size_bonds > MINIMUM_TRANSACTION_AMOUNT:
                    event = rob.open_short(trade_size_bonds)
                    amount_to_trade_base -= event.base_amount
        lp_share_price = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.lp_share_price
        lp_value = larry.wallet.lp_tokens * lp_share_price
        print(f"day {day}: pnl={float(lp_value-exp.amount_of_liquidity):,.0f}", end="\r", flush=True)
        if RUNNING_WANDB:
            wandb.log({"day": day})
            wandb.log({"lp_value": float(lp_value - exp.amount_of_liquidity)})
        if amount_to_trade_base <= 0:
            break  # end the day if we've traded enough
    chain.advance_time(datetime.timedelta(days=1), create_checkpoints=False)
print(f"experiment finished in {(time.time() - start_time):,.2f} seconds")

# %%
# close all positions
print("wallets before liquidation:")
current_wallet = interactive_hyperdrive.get_current_wallet()
display(
    current_wallet.loc[current_wallet.token_type != "WETH", exp.display_cols]
    .style.format(
        subset=[col for col in current_wallet.columns if current_wallet.dtypes[col] == "float64"],
        formatter="{:" + exp.float_fmt + "}",
    )
    .hide(axis="index")
)
rob.liquidate()
larry.remove_liquidity(shares=larry.wallet.lp_tokens)
print("wallets after liquidation:")
current_wallet = interactive_hyperdrive.get_current_wallet()
display(
    current_wallet.loc[current_wallet.token_type != "WETH", exp.display_cols]
    .style.format(
        subset=[col for col in current_wallet.columns if current_wallet.dtypes[col] == "float64"],
        formatter="{:" + exp.float_fmt + "}",
    )
    .hide(axis="index")
)

# %%
# show WETH balance after closing all positions
pool_info = interactive_hyperdrive.get_pool_state()
starting_fixed_rate = float(pool_info.fixed_rate.iloc[0])
ending_fixed_rate = float(pool_info.fixed_rate.iloc[-1])
print(f"starting fixed rate is {starting_fixed_rate:7.2%}")
print(f"  ending fixed rate is {ending_fixed_rate:7.2%}")
governance_fees = float(interactive_hyperdrive.hyperdrive_interface.get_gov_fees_accrued(block_number=None))
current_wallet = deepcopy(interactive_hyperdrive.get_current_wallet())

# index
non_weth_index = (current_wallet.token_type != "WETH") & (current_wallet.position > float(MINIMUM_TRANSACTION_AMOUNT))
weth_index = current_wallet.token_type == "WETH"
# simple PNL based on WETH balance
current_wallet.loc[weth_index, ["pnl"]] = current_wallet.loc[weth_index, ["position"]].values - exp.amount_of_liquidity
# add HPR
current_wallet.loc[:, ["hpr"]] = current_wallet["pnl"] / (current_wallet["position"] - current_wallet["pnl"])

wallet_positions = deepcopy(interactive_hyperdrive.get_wallet_positions())
weth_changes = wallet_positions.loc[wallet_positions.token_type == "WETH", :].copy()
weth_changes.loc[:, "absDelta"] = abs(weth_changes["delta"])
weth_changes.loc[:, "day"] = (weth_changes.timestamp - weth_changes.timestamp.min()).dt.days + 1
weth_changes_agg = weth_changes[["day", "absDelta"]].groupby("day").sum().reset_index()
total_volume = weth_changes_agg.absDelta.sum()
print(f"  total volume is {total_volume:,.0f}")
wallet_positions_by_block = (
    wallet_positions.loc[wallet_positions.token_type == "WETH", :]
    .pivot(
        index="block_number",
        columns="username",
        values="position",
    )
    .reset_index()
)
wallet_positions_by_time = (
    wallet_positions.loc[wallet_positions.token_type == "WETH", :]
    .pivot(
        index="timestamp",
        columns="username",
        values="position",
    )
    .reset_index()
)
wallet_positions_by_block.loc[:, ["rob"]] = (
    wallet_positions_by_block["rob"].max() - wallet_positions_by_block["rob"]
).fillna(0)
wallet_positions_by_time.loc[:, ["rob"]] = (
    wallet_positions_by_time["rob"].max() - wallet_positions_by_time["rob"]
).fillna(0)
wallet_positions_by_block["block_number_delta"] = wallet_positions_by_block["block_number"].diff().fillna(0)
wallet_positions_by_time["timestamp_delta"] = wallet_positions_by_time["timestamp"].diff().dt.total_seconds().fillna(0)
average_by_block = np.average(wallet_positions_by_block["rob"], weights=wallet_positions_by_block["block_number_delta"])
average_by_time = np.average(wallet_positions_by_time["rob"], weights=wallet_positions_by_time["timestamp_delta"])
if RUNNING_INTERACTIVE or RUNNING_WANDB:
    fig, ax = plt.subplots(2, 1, figsize=(8, 8))
    ax[0].step(wallet_positions_by_block["block_number"], wallet_positions_by_block["rob"], label="rob's WETH spend")
    ax[0].axhline(y=average_by_block, color="red", label=f"weighted average by block = {average_by_block:,.0f}")
    ax[0].legend()
    ax[1].step(wallet_positions_by_time["timestamp"], wallet_positions_by_time["rob"], label="rob's WETH spend")
    ax[1].axhline(y=average_by_time, color="red", label=f"weighted average by time = {average_by_time:,.0f}")
    ax[1].legend()
    if RUNNING_INTERACTIVE:
        plt.show()
    else:
        wandb.log({"wallet_positions": wandb.Image(fig)})
idx = weth_index & (current_wallet.username == "rob")
current_wallet.loc[idx, ["position"]] = average_by_time  # type: ignore
current_wallet.loc[idx, ["hpr"]] = (
    current_wallet.loc[idx, ["pnl"]].astype("float").iloc[0].values
    / current_wallet.loc[idx, ["position"]].astype("float").iloc[0].values
)  # type: ignore

# add governance row
new_row = current_wallet.iloc[len(current_wallet) - 1].copy()
new_row["username"] = "governance"
new_row["position"], new_row["pnl"] = governance_fees, governance_fees
new_row["hpr"] = np.inf
new_row["token_type"] = "WETH"
current_wallet = pd.concat([current_wallet, new_row.to_frame().T], ignore_index=True)

# add total row
new_row = current_wallet.iloc[len(current_wallet) - 1].copy()
new_row["username"] = "total"
new_row["position"] = float(current_wallet["position"].values.sum())  # type: ignore
new_row["pnl"] = current_wallet.loc[current_wallet.token_type.values == "WETH", ["pnl"]].values.sum()  # type: ignore
new_row["hpr"] = new_row["pnl"] / (new_row["position"] - new_row["pnl"])
new_row["token_type"] = "WETH"
current_wallet = pd.concat([current_wallet, new_row.to_frame().T], ignore_index=True)

# add share price row
new_row = current_wallet.iloc[len(current_wallet) - 1].copy()
new_row["username"] = "share price"
new_row["position"] = pool_info.share_price.iloc[-1] * 1e7
new_row["pnl"] = pool_info.share_price.iloc[-1] * 1e7 - pool_info.share_price.iloc[0] * 1e7
new_row["hpr"] = pool_info.share_price.iloc[-1] / pool_info.share_price.iloc[0] - 1
new_row["token_type"] = "WETH"
current_wallet = pd.concat([current_wallet, new_row.to_frame().T], ignore_index=True)

# re-index
non_weth_index = (current_wallet.token_type != "WETH") & (current_wallet.position > float(MINIMUM_TRANSACTION_AMOUNT))
weth_index = current_wallet.token_type == "WETH"
# convert to float
current_wallet.position = current_wallet.position.astype(float)
current_wallet.pnl = current_wallet.pnl.astype(float)

# time passed
time_passed_days = (pool_info.timestamp.iloc[-1] - pool_info.timestamp.iloc[0]).total_seconds() / 60 / 60 / 24
print(f"time passed = {time_passed_days:.2f} days")
apr_factor = 365 / time_passed_days
print(f"to scale APR from HPR we multiply by {apr_factor:,.0f} (365/{time_passed_days:.2f})")
print(f"share price went from {pool_info.share_price.iloc[0]:.4f} to {pool_info.share_price.iloc[-1]:.4f}")
# add APR
current_wallet.loc[:, ["apr"]] = current_wallet.loc[:, ["hpr"]].values * apr_factor

results1 = current_wallet.loc[non_weth_index, exp.display_cols]
results2 = current_wallet.loc[weth_index, exp.display_cols_with_hpr]
results2.loc[:, "total_volume"] = total_volume
if RUNNING_WANDB:
    wandb.log({"results1": wandb.Table(dataframe=results1)})
    wandb.log({"results2": wandb.Table(dataframe=results2)})
    wandb.log({"wallet_positions": wandb.Table(dataframe=wallet_positions)})
    wandb.log({"current_wallet": wandb.Table(dataframe=current_wallet)})
    wandb.log({"lp_value": results2.loc[results2.username == "larry", "pnl"].values[0]})
else:
    results1.to_parquet("results1.parquet", index=False)
    results2.to_parquet("results2.parquet", index=False)
    wallet_positions.to_parquet("wallet_positions.parquet", index=False)
    current_wallet.to_parquet("current_wallet.parquet", index=False)
# display final results
if non_weth_index.sum() > 0:
    print("material non-WETH positions:")
    if RUNNING_INTERACTIVE:
        display(results1.style.hide(axis="index"))
    else:
        print(results1)
else:
    print("no material non-WETH positions")
print("WETH positions:")
if RUNNING_INTERACTIVE:
    display(
        results2.style.format(
            subset=[
                col
                for col in current_wallet.columns
                if current_wallet.dtypes[col] == "float64" and col not in ["hpr", "apr"]
            ],
            formatter="{:" + exp.float_fmt + "}",
        )
        .hide(axis="index")
        .format(
            subset=["hpr", "apr"],
            formatter="{:.2%}",
        )
    )
else:
    print(results2)

# %%

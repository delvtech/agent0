# %%
"""Run experiments of economic activity."""
# Variables by themselves print out dataframes in a nice format in interactive mode
# pylint: disable=pointless-statement

import datetime
import os
import time
from copy import deepcopy
from dataclasses import dataclass, field, fields
from typing import NamedTuple

import numpy as np
import pandas as pd
from fixedpointmath import FixedPoint
from matplotlib import pyplot as plt

from agent0.hyperdrive.interactive import RUNNING_INTERACTIVE, InteractiveHyperdrive, LocalChain

if RUNNING_INTERACTIVE is False:
    display = print  # pylint: disable=redefined-builtin,unused-import
else:
    from IPython.display import display

# pylint: disable=bare-except
# ruff: noqa: A001 (allow shadowing a python builtin)


# %%
# config
@dataclass
class ExperimentConfig:  # pylint: disable=too-many-instance-attributes
    """Everything needed for my experiment."""

    daily_volume_percentage_of_liquidity: float = 0.01  # 1%
    term_days: int = 365
    float_fmt: str = ",.0f"
    display_cols: list[str] = field(
        default_factory=lambda: ["block_number", "username", "position", "pnl", "base_token_type", "maturity_time"]
    )
    display_cols_with_hpr: list[str] = field(
        default_factory=lambda: [
            "block_number",
            "username",
            "position",
            "pnl",
            "HPR",
            "APR",
            "base_token_type",
            "maturity_time",
        ]
    )
    amount_of_liquidity: int = 10_000_000
    curve_fee: FixedPoint = FixedPoint("0.01")  # 1%, 10% default
    flat_fee: FixedPoint = FixedPoint("0.0001")  # 1bps, 5bps default
    governance_fee: FixedPoint = FixedPoint("0.1")  # 10%, 15% default

    def __post_init__(self):
        """Calculate parameters for the experiment."""
        self.rate_required_for_same_price: float = min(
            1, 0.035 * 365 / self.term_days
        )  # get same price for shorter term
        self.starting_fixed_rate: FixedPoint = FixedPoint(self.rate_required_for_same_price)  # equivalent of 3.5%
        self.starting_variable_rate: FixedPoint = FixedPoint(self.rate_required_for_same_price)  # equivalent of 3.5%
        self.term_seconds: int = 60 * 60 * 24 * self.term_days


exp = ExperimentConfig()
for key in os.environ:
    if key in fields(exp):
        setattr(exp, key, os.environ[key])

# %%
# set up chain
chain = LocalChain(LocalChain.Config())

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
    governance_fee=exp.governance_fee,
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
print(f"spot price = {interactive_hyperdrive.hyperdrive_interface.calc_spot_price()}")

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
    _max_long_base = _interactive_hyperdrive.hyperdrive_interface.calc_max_long(budget=_current_base)
    _max_long_shares = _interactive_hyperdrive.hyperdrive_interface.calc_shares_out_given_bonds_in_down(_max_long_base)
    _max_long_bonds = _max_long_shares * _share_price
    _max_short_bonds = FixedPoint(0)
    try:  # sourcery skip: do-not-use-bare-except
        _max_short_bonds = _interactive_hyperdrive.hyperdrive_interface.calc_max_short(budget=_current_base)
    except:  # pylint: disable=bare-except
        pass
    max_short_shares = _interactive_hyperdrive.hyperdrive_interface.calc_shares_out_given_bonds_in_down(
        _max_short_bonds
    )
    _max_short_base = max_short_shares * _share_price
    return GetMax(
        Max(_max_long_base, _max_long_bonds),
        Max(_max_short_base, _max_short_bonds),
    )


# sourcery skip: avoid-builtin-shadow, do-not-use-bare-except, invert-any-all, remove-unnecessary-else, swap-if-else-branches
for day in range(exp.term_days):
    amount_to_trade_base = FixedPoint(exp.amount_of_liquidity * exp.daily_volume_percentage_of_liquidity)
    while amount_to_trade_base > MINIMUM_TRANSACTION_AMOUNT:
        randnum = np.random.randint(0, 2)
        spot_price = interactive_hyperdrive.hyperdrive_interface.calc_spot_price()
        share_price = interactive_hyperdrive.hyperdrive_interface.current_pool_state.pool_info.share_price
        max = None
        wallet = rob.wallet
        event = None
        if randnum == 0:  # go long
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
        else:  # go short
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
        print(f"day {day}: {event}")  # type: ignore (PossiblyUnboundVariable)
        if amount_to_trade_base <= 0:
            break  # end the day if we've traded enough
    chain.advance_time(datetime.timedelta(days=1), create_checkpoints=False)
print(f"experiment finished in {(time.time() - start_time):,.2f} seconds")

# %%
# close all positions
CLOSE_LONG_FIRST = True
RETRIES = 50
for attempt in range(RETRIES):
    # while len(rob.wallet.longs) > 0 or len(rob.wallet.shorts) > 0:
    position_values = list(rob.wallet.longs.values()) + list(rob.wallet.shorts.values())
    material_positions = [p for p in position_values if p.balance > MINIMUM_TRANSACTION_AMOUNT]
    print(f"closeout attempt {attempt:3} of {RETRIES}: open positions: {len(material_positions)=}")
    if any(position.balance > MINIMUM_TRANSACTION_AMOUNT for position in position_values):
        if CLOSE_LONG_FIRST:
            for maturity_time, long in rob.wallet.longs.copy().items():
                if long.balance > MINIMUM_TRANSACTION_AMOUNT:
                    try:
                        rob.close_long(maturity_time, long.balance)
                    except:
                        break
                    break
            for maturity_time, short in rob.wallet.shorts.copy().items():
                if short.balance > MINIMUM_TRANSACTION_AMOUNT:
                    try:
                        rob.close_short(maturity_time, short.balance)
                    except:
                        break
                    break
        else:  # close short first
            for maturity_time, short in rob.wallet.shorts.copy().items():
                if short.balance > MINIMUM_TRANSACTION_AMOUNT:
                    try:
                        rob.close_short(maturity_time, short.balance)
                    except:
                        break
                    break
            for maturity_time, long in rob.wallet.longs.copy().items():
                if long.balance > MINIMUM_TRANSACTION_AMOUNT:
                    try:
                        rob.close_long(maturity_time, long.balance)
                    except:
                        break
                    break
        CLOSE_LONG_FIRST = not CLOSE_LONG_FIRST
    else:
        break
larry.remove_liquidity(shares=larry.wallet.lp_tokens)

# %%
# prepare data
latest_block = chain._web3.eth.get_block("latest")  # pylint: disable=protected-access
print(f"{latest_block.number=}")  # type: ignore
# run data pipeline now, if it wasn't run as part of interactive hyperdrive
# if config.use_data_pipeline is False:
#     from chainsync.exec import acquire_data, data_analysis

#     interactive_hyperdrive.initialize_database()
#     print(f"{interactive_hyperdrive.db_session.is_active=}")
#     kwargs = {
#         "start_block": interactive_hyperdrive._deploy_block_number,  # pylint: disable=protected-access
#         "db_session": interactive_hyperdrive.db_session,
#         "eth_config": interactive_hyperdrive.eth_config,
#         "postgres_config": interactive_hyperdrive.postgres_config,
#         "contract_addresses": interactive_hyperdrive.hyperdrive_interface.addresses,
#         "exit_on_catch_up": True,
#         "suppress_logs": False,
#     }
#     acquire_data(**kwargs | {"lookback_block_limit": 9999})
#     data_analysis(**kwargs)
# else:  # wait for chainsync to catch up
#     from chainsync.db.hyperdrive import get_latest_block_number_from_pool_info_table

#     latest_db_block = get_latest_block_number_from_pool_info_table(interactive_hyperdrive.db_session)
#     print(f"{get_latest_block_number_from_pool_info_table(interactive_hyperdrive.db_session)=}")
#     attempt = 0  # pylint: disable=invalid-name
#     while latest_db_block < latest_block.number:  # type: ignore
#         time.sleep(1)
#         attempt += 1
#         latest_db_block = get_latest_block_number_from_pool_info_table(
#             interactive_hyperdrive.db_session
#         )  # pylint: disable=invalid-name
#         print(f"{attempt=:4,.0f}, {latest_db_block=} vs. {latest_block.number=}")  # type: ignore

# %%
# show wallets at end
current_wallet = interactive_hyperdrive.get_current_wallet()
current_wallet.loc[current_wallet.token_type != "WETH", exp.display_cols].style.format(
    subset=[col for col in current_wallet.columns if current_wallet.dtypes[col] == "float64"],
    formatter="{:" + exp.float_fmt + "}",
).hide(axis="index")

# %%
# show WETH balance after closing all positions
pool_info = interactive_hyperdrive.get_pool_state()
# fixed_rate=interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate()
print(f"starting fixed rate is {float(pool_info.fixed_rate.iloc[1]):7.2%}")
print(f"  ending fixed rate is {float(pool_info.fixed_rate.iloc[-1]):7.2%}")
governance_fees = float(interactive_hyperdrive.hyperdrive_interface.get_gov_fees_accrued(block_number=None))
current_wallet = deepcopy(interactive_hyperdrive.get_current_wallet())

# index
non_weth_index = (current_wallet.token_type != "WETH") & (current_wallet.position > float(MINIMUM_TRANSACTION_AMOUNT))
weth_index = current_wallet.token_type == "WETH"
# simple PNL based on WETH balance
current_wallet.loc[weth_index, ["pnl"]] = current_wallet.loc[weth_index, ["position"]].values - exp.amount_of_liquidity
# add HPR
current_wallet.loc[:, ["HPR"]] = current_wallet["pnl"] / (current_wallet["position"] - current_wallet["pnl"])

wallet_positions = deepcopy(interactive_hyperdrive.get_wallet_positions())
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
if RUNNING_INTERACTIVE:
    fig, ax = plt.subplots(2, 1, figsize=(8, 8))
    ax[0].step(wallet_positions_by_block["block_number"], wallet_positions_by_block["rob"], label="rob's WETH spend")
    ax[0].axhline(y=average_by_block, color="red", label=f"weighted average by block = {average_by_block:,.0f}")
    ax[0].legend()
    ax[1].step(wallet_positions_by_time["timestamp"], wallet_positions_by_time["rob"], label="rob's WETH spend")
    ax[1].axhline(y=average_by_time, color="red", label=f"weighted average by time = {average_by_time:,.0f}")
    ax[1].legend()
    plt.show()
idx = weth_index & (current_wallet.username == "rob")
current_wallet.loc[idx, ["position"]] = average_by_time  # type: ignore
current_wallet.loc[idx, ["HPR"]] = (
    current_wallet.loc[idx, ["pnl"]].astype("float").iloc[0].values
    / current_wallet.loc[idx, ["position"]].astype("float").iloc[0].values
)  # type: ignore

# add governance row
new_row = current_wallet.iloc[len(current_wallet) - 1].copy()
new_row["username"] = "governance"
new_row["position"], new_row["pnl"] = governance_fees, governance_fees
new_row["HPR"] = np.inf
new_row["token_type"] = "WETH"
current_wallet = pd.concat([current_wallet, new_row.to_frame().T], ignore_index=True)

# add total row
new_row = current_wallet.iloc[len(current_wallet) - 1].copy()
new_row["username"] = "total"
new_row["position"] = float(current_wallet["position"].values.sum())  # type: ignore
new_row["pnl"] = current_wallet.loc[current_wallet.token_type.values == "WETH", ["pnl"]].values.sum()  # type: ignore
new_row["HPR"] = new_row["pnl"] / (new_row["position"] - new_row["pnl"])
new_row["token_type"] = "WETH"
current_wallet = pd.concat([current_wallet, new_row.to_frame().T], ignore_index=True)

# add share price row
new_row = current_wallet.iloc[len(current_wallet) - 1].copy()
new_row["username"] = "share price"
new_row["position"] = pool_info.share_price.iloc[-1] * 1e7
new_row["pnl"] = pool_info.share_price.iloc[-1] * 1e7 - pool_info.share_price.iloc[0] * 1e7
new_row["HPR"] = pool_info.share_price.iloc[-1] / pool_info.share_price.iloc[0] - 1
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
# add APR
current_wallet.loc[:, ["APR"]] = current_wallet.loc[:, ["HPR"]].values * apr_factor

results1 = current_wallet.loc[non_weth_index, exp.display_cols]
results2 = current_wallet.loc[weth_index, exp.display_cols_with_hpr]
results1.to_csv("results1.csv")
results2.to_csv("results2.csv")
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
                if current_wallet.dtypes[col] == "float64" and col not in ["HPR", "APR"]
            ],
            formatter="{:" + exp.float_fmt + "}",
        )
        .hide(axis="index")
        .format(
            subset=["HPR", "APR"],
            formatter="{:.2%}",
        )
        .hide(axis="columns", subset=["base_token_type", "maturity_time"])
    )
else:
    print(results2)

# %%

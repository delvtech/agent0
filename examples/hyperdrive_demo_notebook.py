# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     custom_cell_magics: kql
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.2
#   kernelspec:
#     display_name: .venv
#     language: python
#     name: python3
# ---

# %%
"""simulation for the Hyperdrive market"""
from __future__ import annotations
from matplotlib.axes import Axes

# pylint: disable=line-too-long
# pylint: disable=too-many-lines
# pylint: disable=invalid-name
# pyright: reportOptionalMemberAccess=false, reportGeneralTypeIssues=false

# %% [markdown]
# <a href="https://colab.research.google.com/github/delvtech/elf-simulations/blob/4536bb486b7ce857840996448dbb479adb1c5c14/examples/notebooks/hyperdrive.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

# %% [markdown]
# ## Hyperdrive Simulation
# We use the following setup:
# - 90 day term
# - 200 agents, 100 randomly open and close longs, the other 100 randomly open and close shorts
# - agents are initialized with 1 million of capital, trading 10% of their budget per trade
# - they trade at random intervals calibrated to be roughly twice per term (1 open 1 close)
# - there is one Liquidity Provider which deposits 500 million of liquidity
#
# For details on the simulation framework, please see our <a href="https://elfpy.delv.tech/">simulation documentation</a>

# %% [markdown]
# ### Install repo requirements & import packages

# %%
# test: skip-cell
try:  # install repo only if running on google colab
    # check if running in Google Colaboratory
    eval("import google.colab")  # pylint: disable=eval-used
    import os

    os.system(
        "!pip install git+https://github.com/delvtech/elf-simulations.git@4536bb486b7ce857840996448dbb479adb1c5c14"
    )
except:  # pylint: disable=bare-except
    print("running locally & trusting that you have the dependencies installed")

# %%
import numpy as np
from numpy.random._generator import Generator as NumpyGenerator
import matplotlib.pyplot as plt
import pandas as pd

from elfpy.agents.agent import AgentFP
from elfpy.utils import sim_utils
from elfpy.simulators import ConfigFP
from elfpy.utils.outputs import get_gridspec_subplots
from elfpy.math import FixedPoint

import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.utils.outputs as output_utils
import elfpy.utils.post_processing as post_processing
import elfpy.agents.policies.random_agent as random_agent

# %% [markdown]
# ### Setup experiment parameters

# %%
config = ConfigFP()

config.title = "Hyperdrive demo"
config.pricing_model_name = "Hyperdrive"  # can be yieldspace or hyperdrive

config.num_trading_days = 90  # Number of simulated trading days
config.num_blocks_per_day = 10  # Blocks in a given day (7200 means ~12 sec per block)
config.num_position_days = 45
config.curve_fee_multiple = 0.10  # fee multiple applied to the price slippage (1-p) collected on trades
config.flat_fee_multiple = 0.005  # 5 bps

num_agents = 100  # int specifying how many agents you want to simulate
agent_budget = 1_000_000  # max money an agent can spend
trade_chance = 2 / (
    config.num_trading_days * config.num_blocks_per_day
)  # on a given block, an agent will trade with probability `trade_chance`

config.target_fixed_apr = 0.01  # target fixed APR of the initial market after the LP
config.target_liquidity = 500_000_000  # target total liquidity of the initial market, before any trades

config.log_level = output_utils.text_to_log_level("WARNING")  # Logging level, should be in ["DEBUG", "INFO", "WARNING"]
config.log_filename = "hyperdrive"  # Output filename for logging

# %% [markdown]
# ### Setup agents


# %%
class RandomAgent(random_agent.RandomAgent):
    """Agent that randomly opens or closes longs or shorts

    Customized from the policy in that one can force the agent to only open longs or shorts
    """

    def __init__(self, rng: NumpyGenerator, trade_chance_pct: float, wallet_address: int, budget: int = 10_000) -> None:
        """Add custom stuff then call basic policy init"""
        self.trade_long = True  # default to allow easy overriding
        self.trade_short = True  # default to allow easy overriding
        super().__init__(rng, trade_chance_pct, wallet_address, FixedPoint(budget * 10 * 18))

    def get_available_actions(
        self,
        disallowed_actions: list[hyperdrive_actions.MarketActionType] | None = None,
    ) -> list[hyperdrive_actions.MarketActionType]:
        """Get all available actions, excluding those listed in disallowed_actions"""
        # override disallowed_actions
        disallowed_actions = []
        if not self.trade_long:  # disallow longs
            disallowed_actions += [
                hyperdrive_actions.MarketActionType.OPEN_LONG,
                hyperdrive_actions.MarketActionType.CLOSE_LONG,
            ]
        if not self.trade_short:  # disallow shorts
            disallowed_actions += [
                hyperdrive_actions.MarketActionType.OPEN_SHORT,
                hyperdrive_actions.MarketActionType.CLOSE_SHORT,
            ]
        # compile a list of all actions
        all_available_actions = [
            hyperdrive_actions.MarketActionType.OPEN_LONG,
            hyperdrive_actions.MarketActionType.OPEN_SHORT,
        ]
        if self.wallet.longs:  # if the agent has open longs
            all_available_actions.append(hyperdrive_actions.MarketActionType.CLOSE_LONG)
        if self.wallet.shorts:  # if the agent has open shorts
            all_available_actions.append(hyperdrive_actions.MarketActionType.CLOSE_SHORT)
        # downselect from all actions to only include allowed actions
        return [action for action in all_available_actions if action not in disallowed_actions]


def get_example_agents(
    rng: NumpyGenerator, budget: int, new_agents: int, existing_agents: int = 0, direction: str | None = None
) -> list[AgentFP]:
    """Instantiate a set of custom agents"""
    agents = []
    for address in range(existing_agents, existing_agents + new_agents):
        agent = RandomAgent(
            rng=rng,
            trade_chance_pct=trade_chance,
            wallet_address=address,
            budget=budget,
        )
        if direction is not None:
            if direction == "short":
                agent.trade_long = False
            elif direction == "long":
                agent.trade_short = False
        agent.log_status_report()
        agents += [agent]
    return agents


# %% [markdown]
#
# ### Define variable apr process


# %%
def DSR_historical(num_dates=90):
    """Retuns a list of historical DSR values

    Parameters
    ----------
    num_dates : int, optional
        number of daily values to return, by default 90

    Returns
    -------
    list[float]
        A list of historical DSR values
    """
    try:
        dsr = pd.read_csv(
            "https://s3-sim-repo-0.s3.us-east-2.amazonaws.com/Data/HIST_DSR_D.csv",
            index_col=0,
            infer_datetime_format=True,
        )
        dsr.index = pd.to_datetime(dsr.index)
        dsr = dsr.resample("D").mean()
        min_date = dsr.index.min()
        max_date = dsr.index.max()
        date_range = max_date - min_date
        new_date_range = min_date + date_range * np.linspace(0, 1, num_dates)
        dsr_new = dsr.reindex(new_date_range, method="ffill")
        dsr_new = dsr_new.reset_index(drop=True)
        return dsr_new["DAI_SAV_RATE"].to_list()
    except:  # pylint: disable=bare-except
        return [0.01] * config.num_trading_days


# Define the variable apr
config.variable_apr = DSR_historical(num_dates=config.num_trading_days)
config.freeze()  # type: ignore

# %% [markdown]
# ### Setup simulation objects

# %%
# define root logging parameters
output_utils.setup_logging(log_filename=config.log_filename, log_level=config.log_level)

# get an instantiated simulator object
simulator = sim_utils.get_simulator_fp(config)

# %% [markdown]
# ### Run the simulation

# %%
# add the random agents
short_agents = get_example_agents(
    rng=simulator.rng, budget=agent_budget, new_agents=num_agents // 2, existing_agents=1, direction="short"
)
long_agents = get_example_agents(
    rng=simulator.rng,
    budget=agent_budget,
    new_agents=num_agents // 2,
    existing_agents=1 + len(short_agents),
    direction="long",
)
simulator.add_agents(short_agents + long_agents)
print(f"Simulator has {len(simulator.agents)} agents")

# run the simulation
simulator.run_simulation()

# %%
# convert simulation state to a pandas dataframe
trades: pd.DataFrame = post_processing.compute_derived_variables_fp(simulator)
for col in list(trades):
    if col.startswith("agent"):  # type: ignore
        divisor = 1e6  # 1 million divisor for everyone
        # pandas dataframes lets you do this syntax, but they didn't do the typing for it :/
        trades[col] = trades[col] / divisor  # pylint: disable-all

# %% [markdown]
# ### Plot simulation results

# %% [markdown]
# This shows the evolution of interest rates over time. The "variable" APR represents a theoretical underlying variable rate. Here we've mocked it up to have the same pattern as the MakerDao DAI Saving Rate over its whole history, but condensed to a 90 day period for this simulation. The fixed rate is initialized at 1% and appears to remain unchanged.

# %%
trades_agg = trades.groupby("day").agg(
    {
        "variable_apr": ["mean"],
        "fixed_apr": ["mean"],
        "delta_base_abs": ["sum"],
        "agent_0_pnl": ["mean"],
    }
)
trades_agg.columns = ["_".join(col).strip() for col in trades_agg.columns.values]
trades_agg = trades_agg.reset_index()
ax = get_gridspec_subplots()[1][0]
plt.gcf().set_size_inches(6, 5)
ax = trades_agg.iloc[0:].plot(x="day", y="variable_apr_mean", ax=ax, label="variable", c="blue")
ax = trades_agg.iloc[0:].plot(x="day", y="fixed_apr_mean", ax=ax, label="fixed", c="black")
ax.set_title("Interest rates over time")
ax.set_xlabel("Day")
ax.set_ylabel("APR")
ax.legend()

xtick_step = 10
ax.set_xticks([0] + list(range(9, simulator.config.num_trading_days + 1, xtick_step)))
ax.set_xticklabels(["1"] + [str(x + 1) for x in range(9, simulator.config.num_trading_days + 1, xtick_step)])

ylim = ax.get_ylim()
ax.set_ylim(0, ylim[1])
ax.set_yticks(list(np.arange(ylim[0], ylim[1], 0.01)))
ax.set_yticklabels([f"{(i):.0%}" for i in ax.get_yticks()])

# %% [markdown]
# It may look like the black line isn't moving at all, until the end. But let's zoom in!
#
# This is a function of two things: random agents being too dumb to concertedly move the rate, as well as the model parameters not being optimized for this scenario.

# %%
fig = output_utils.plot_fixed_apr(trades, exclude_first_day=True, exclude_last_day=True)
fig.set_size_inches(6, 5)
ax = plt.gca()
ax.properties()["children"][0].set_color("black")
ax.set_yticklabels([f"{(i/100):.3%}" for i in ax.get_yticks()])
ax.set_ylabel("APR")

xtick_step = 10
ax.set_xticks([0] + list(range(9, simulator.config.num_trading_days + 1, xtick_step)))
ax.set_xticklabels(["1"] + [str(x + 1) for x in range(9, simulator.config.num_trading_days + 1, xtick_step)])

# %% [markdown]
# These random agents are unable to pick smart entry points. Due to trading on coinflips only, they slowdly bleed fees out of their starting position, which in this case reduces from 1.0 million down to 0.999, a loss of $1k.


# %%
def get_pnl_excluding_agent_0_no_mock_with_day(trades_df: pd.DataFrame) -> pd.DataFrame:
    """Returns Profit and Loss Column for every agent except for agent 0 from post-processing"""
    cols_to_return = ["day"] + [col for col in trades_df if col.startswith("agent") and col.endswith("pnl_no_mock")]  # type: ignore
    cols_to_return.remove("agent_0_pnl_no_mock")
    return trades_df[cols_to_return]


def plot_pnl(pnl: pd.DataFrame, axes: Axes, label: str):
    """Plots Profit and Loss"""
    # ax.plot(pnl.iloc[1:,:], linestyle='-', linewidth=0.5, alpha=0.5)
    # separate first half of agents, which are set to trade short
    # from second half of agents, which are set to trade long
    columns = pnl.columns.to_list()
    n = len(columns) // 2  # int
    short_pnl = pnl.loc[1:, columns[:n]].mean(axis=1)
    long_pnl = pnl.loc[1:, columns[n:]].mean(axis=1)
    axes.plot(short_pnl, c="red", label=f"Short {label}, final value={short_pnl[len(short_pnl)-1]:.5f}", linewidth=2)
    axes.plot(long_pnl, c="black", label=f"Long {label}, final_value={long_pnl[len(long_pnl)-1]:.5f}", linewidth=2)
    # grey area where day is last day
    axes.set_ylabel("PNL in millions")
    # ax.axvspan(last_day, len(short_pnl), color='grey', alpha=0.2, label="Last day")
    axes.legend()


fig, ax = plt.subplots(1, 1, figsize=(6, 5), sharex=True, gridspec_kw={"wspace": 0.0, "hspace": 0.0})
first_trade_that_is_on_last_day = min(trades.index[trades.day == max(trades.day)])
# data_mock = post_processing.get_pnl_excluding_agent_0(trades)
# plot_pnl(pnl=data_mock.iloc[:-1, :], ax=ax, label='Mock')
data_no_mock = get_pnl_excluding_agent_0_no_mock_with_day(trades).groupby("day").mean()
plot_pnl(pnl=data_no_mock.iloc[:-1, :], axes=ax, label="Realized Market Value")

xtick_step = 10
ax.set_xticks([0] + list(range(9, simulator.config.num_trading_days + 1, xtick_step)))
ax.set_xticklabels(["1"] + [str(x + 1) for x in range(9, simulator.config.num_trading_days + 1, xtick_step)])

plt.gca().set_xlabel("Day")
plt.gca().set_title("Trader PNL over time")
# display(data_no_mock)

# %% [markdown]
# This plot shows being a Liquidity Provider (LP) is a profitable position, in this scenario where agents are trading randomly.

# %%
fig, ax = plt.subplots(2, 1, figsize=(6, 10))
exclude_last_day = True
num_agents = 1
start_idx = 0
first_trade_that_is_on_last_day = min(trades_agg.index[trades_agg.day == max(trades_agg.day)])
end_idx = first_trade_that_is_on_last_day - 1 if exclude_last_day is True else len(trades_agg)
ax[0].plot(
    trades_agg.loc[start_idx:end_idx, "day"],
    trades_agg.loc[start_idx:end_idx, "agent_0_pnl_mean"],
    label=f"mean = {trades_agg.loc[end_idx,'agent_0_pnl_mean']:.3f}",
)
ax[0].set_title("LP PNL Over Time")
ax[0].set_ylabel("PNL")
ax[0].set_xlabel("Day")
data = trades.loc[0 : first_trade_that_is_on_last_day - 1, "agent_0_pnl"]
xtick_step = 10
ax[0].set_xticks([0] + list(range(9, simulator.config.num_trading_days + 1, xtick_step)))
ax[0].set_xticklabels(["1"] + [str(x + 1) for x in range(9, simulator.config.num_trading_days + 1, xtick_step)])
ax[0].legend({f"final value = {data.values[len(data)-1]:,.3f}"})
ax[0].set_ylabel("PnL in millions")

exclude_first_trade = True
exclude_last_trade = True
start_idx = 1 if exclude_first_trade else 0
end_idx = first_trade_that_is_on_last_day - 1 if exclude_last_trade is True else None
ax[1].bar(trades_agg.loc[start_idx:end_idx, "day"], trades_agg.loc[start_idx:end_idx, "delta_base_abs_sum"], label=f"mean = {trades_agg.loc[end_idx,'delta_base_abs_sum']:.3f}")  # type: ignore
ax[1].set_title("Market Volume")
ax[1].set_ylabel("Base")
ax[1].set_xlabel("Day")
xtick_step = 10
ax[1].set_xticks([0] + list(range(9, simulator.config.num_trading_days + 1, xtick_step)))
ax[1].set_xticklabels(["1"] + [str(x + 1) for x in range(9, simulator.config.num_trading_days + 1, xtick_step)])
ylim = ax[1].get_ylim()
ax[1].set_ylim(0, ylim[1])

# %% [markdown]
# ## We are constantly updating our research. Stay tuned for more!

# %% [markdown]
# TODO:
# - parameter optimization
# - smart agents
# - multiple simulation trial runs to evaluate LP profitability
# - simulate Aave, Compound, MakerDao, etc.

# %%
"""Simulation for the smart bots making rational trades"""
from __future__ import annotations


# pylint: disable=line-too-long
# pylint: disable=too-many-lines
# pylint: disable=too-many-arguments
# pylint: disable=invalid-name
# pylint: disable=too-few-public-methods
# pyright: reportOptionalMemberAccess=false, reportGeneralTypeIssues=false

# %% [markdown]
# ### Install repo requirements & import packages

# %%
import numpy as np
from numpy.random._generator import Generator as NumpyGenerator
import matplotlib.ticker as ticker

import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.utils.outputs as output_utils
import elfpy.utils.post_processing as post_processing
import elfpy.utils.sim_utils as sim_utils
import elfpy.types as types

from elfpy.agents.agent import Agent
from elfpy.agents.policies import BasePolicy
from elfpy.agents.wallet import Wallet
from elfpy.math import FixedPoint
from elfpy.simulators.config import Config
from elfpy.agents.policies import LongLouie, ShortSally

# %% [markdown]
# ### Setup experiment parameters

# %%
config = Config()

# General config parameters
config.title = "Hyperdrive smart agent demo"
config.pricing_model_name = "Hyperdrive"  # can be yieldspace or hyperdrive

config.num_trading_days = 20  # 1095 # Number of simulated trading days
config.num_blocks_per_day = 5  # 7200 # Blocks in a given day (7200 means ~12 sec per block)
config.num_position_days = 10  # 90 # How long a token reaches maturity

config.curve_fee_multiple = 0.05  # fee multiple applied to the price slippage (1-p) collected on trades
config.flat_fee_multiple = 0.05  # fee collected on the spread of the flat portion

config.target_fixed_apr = 0.01  # target fixed APR of the initial market after the LP
config.target_liquidity = 500_000_000  # target total liquidity of the initial market, before any trades

config.log_level = output_utils.text_to_log_level("DEBUG")  # Logging level, should be in ["DEBUG", "INFO", "WARNING"]
config.log_filename = "sally_n_louie"  # Output filename for logging

config.shuffle_users = True

# Notebook specific parameters
config.scratch["num_sallys"] = 15
config.scratch["num_louies"] = 20 * config.scratch["num_sallys"]
config.scratch["num_agents"] = (
    config.scratch["num_sallys"] + config.scratch["num_louies"]
)  # int specifying how many agents you want to simulate
config.scratch[
    "trade_chance"
] = 0.1  # 1 / (config.num_trading_days * num_agents) # on a given block, an agent will trade with probability `trade_chance`

config.scratch["louie_budget_mean"] = 375_000
config.scratch["louie_budget_std"] = 25_000

config.scratch["louie_budget_max"] = 1_00_000
config.scratch["louie_budget_min"] = 1_000

config.scratch["sally_budget_mean"] = 1_000
config.scratch["sally_budget_std"] = 500

config.scratch["sally_budget_max"] = 1_00_000
config.scratch["sally_budget_min"] = 1_000

config.scratch["sally_risk_min"] = 0.0
config.scratch["sally_risk_max"] = 0.06
config.scratch["sally_risk_mean"] = 0.02
config.scratch["sally_risk_std"] = 0.01

# Define the vault apr
vault_apr = np.array([0.01] * config.num_trading_days)
vault_apr[config.num_trading_days // 2 :] = 0.05
config.variable_apr = vault_apr.tolist()
config.freeze()

fig_size = (5, 5)

# %% [markdown]
# ### Setup agents


# %%


# %%
class LPAgent(BasePolicy):
    """Adds a large LP"""

    def action(self, market: hyperdrive_market.Market, wallet: Wallet):
        """implement user strategy"""
        if wallet.lp_tokens > 0:  # has already opened the lp
            action_list = []
        else:
            action_list = [
                types.Trade(
                    market=types.MarketType.HYPERDRIVE,
                    trade=hyperdrive_actions.HyperdriveMarketAction(
                        action_type=hyperdrive_actions.MarketActionType.ADD_LIQUIDITY,
                        trade_amount=self.budget,
                        wallet=wallet,
                    ),
                )
            ]
        return action_list


# %%
def get_example_agents(rng: NumpyGenerator, experiment_config: Config, existing_agents: int = 0) -> list[Agent]:
    """Instantiate a set of custom agents"""
    agents = []
    for address in range(existing_agents, existing_agents + experiment_config.scratch["num_sallys"]):
        risk_threshold = FixedPoint(
            np.maximum(
                experiment_config.scratch["sally_risk_min"],
                np.minimum(
                    experiment_config.scratch["sally_risk_max"],
                    rng.normal(
                        loc=experiment_config.scratch["sally_risk_mean"],
                        scale=experiment_config.scratch["sally_risk_std"],
                    ),
                ),
            ).item()  # convert to Python type
        )
        budget = FixedPoint(
            np.maximum(
                experiment_config.scratch["sally_budget_min"],
                np.minimum(
                    250_000,
                    rng.normal(
                        loc=experiment_config.scratch["sally_budget_mean"],
                        scale=experiment_config.scratch["sally_budget_std"],
                    ),
                ),
            ).item()  # convert to Python type
        )
        agent = Agent(
            wallet_address=address,
            policy=ShortSally(
                budget=budget,
                rng=rng,
                trade_chance=experiment_config.scratch["trade_chance"],
                risk_threshold=risk_threshold,
            ),
        )
        agent.log_status_report()
        agents += [agent]
    existing_agents += len(agents)
    for address in range(existing_agents, existing_agents + experiment_config.scratch["num_louies"]):
        risk_threshold = FixedPoint("0.0")
        budget = FixedPoint(
            np.maximum(
                experiment_config.scratch["louie_budget_min"],
                np.minimum(
                    250_000,
                    rng.normal(
                        loc=experiment_config.scratch["louie_budget_mean"],
                        scale=experiment_config.scratch["louie_budget_std"],
                    ),
                ),
            ).item()  # convert to Python type
        )
        agent = Agent(
            wallet_address=address,
            policy=LongLouie(
                budget=budget,
                rng=rng,
                trade_chance=experiment_config.scratch["trade_chance"],
                risk_threshold=risk_threshold,
            ),
        )
        agent.log_status_report()
        agents += [agent]
    return agents


# %% [markdown]
# ### Setup simulation objects

# %%
# define root logging parameters
output_utils.setup_logging(log_filename=config.log_filename, log_level=config.log_level)

# get an instantiated simulator object
simulator = sim_utils.get_simulator(config)

# %% [markdown]
# ### Run the simulation

# %%
# add the random agents
trading_agents = get_example_agents(
    rng=simulator.rng,
    experiment_config=config,
    existing_agents=len(simulator.agents),
)
simulator.add_agents(trading_agents)
print(f"Simulator has {len(simulator.agents)} agents")


# %%
# run the simulation
simulator.run_simulation()

# %%
# convert simulation state to a pandas dataframe
trades = post_processing.compute_derived_variables(simulator)

# %% [markdown]
# ### Plot simulation results

# %% [markdown]
#
# ### variable & fixed apr

# %%
fig, axes, _ = output_utils.get_gridspec_subplots()
ax = axes[0]
start_index = 0
end_index = -1
spot_size = 2.0
ax.scatter(
    trades.iloc[start_index:end_index]["trade_number"],
    trades.iloc[start_index:end_index]["variable_apr"],
    label="variable",
    c="blue",
    s=spot_size,
)
ax.scatter(
    trades.iloc[start_index:end_index]["trade_number"],
    trades.iloc[start_index:end_index]["fixed_apr"],
    label="fixed",
    c="orange",
    s=spot_size,
)

ax.set_title("Interest rates over time")
ax.set_xlabel("trade number")
ax.set_ylabel("APR")
ax.legend()

ax.grid(axis="x", which="both", color="black", alpha=0)
day_data = np.nonzero(np.array(trades.iloc[start_index:end_index]["day"].diff()) == 1)[0]
for x in day_data:
    ax.axvline(x, c="black", alpha=0.2)

ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
fig.set_size_inches(fig_size)

# %%

fig, axes, _ = output_utils.get_gridspec_subplots()
ax = axes[0]
start_index = 0
end_index = -1
spot_size = 2.0
ax.scatter(
    trades.iloc[start_index:end_index]["trade_number"],
    trades.iloc[start_index:end_index]["variable_apr"],
    label="variable",
    c="blue",
    s=spot_size,
)
ax.scatter(
    trades.iloc[start_index:end_index]["trade_number"],
    trades.iloc[start_index:end_index]["fixed_apr"],
    label="fixed",
    c="orange",
    s=spot_size,
)
ax.set_title("Interest rates over time")
ax.set_xlabel("trade number")
ax.set_ylabel("APR")
ax.legend()

ax.grid(axis="x", which="both", color="black", alpha=0)
day_data = np.nonzero(np.array(trades.iloc[start_index:end_index]["day"].diff()) == 1)[0]
for x in day_data:
    ax.axvline(x, c="black", alpha=0.2)

ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
ylim = ax.get_ylim()
fig.set_size_inches(fig_size)

# %%
num_longs_and_shorts = {f"agent_{agent_id}_num_longs": ["sum"] for agent_id in range(len(simulator.agents))}
num_longs_and_shorts.update({f"agent_{agent_id}_num_shorts": ["sum"] for agent_id in range(len(simulator.agents))})
trades_agg = trades.groupby("day").agg(num_longs_and_shorts)
trades_agg.columns = ["_".join(col).strip() for col in trades_agg.columns.values]
trades_agg = trades_agg.reset_index()
longs = trades_agg.filter(regex="num_longs").sum(axis=1)
shorts = trades_agg.filter(regex="num_shorts").sum(axis=1)

fix, axes, _ = output_utils.get_gridspec_subplots(nrows=1, ncols=1)
ax = axes[0]
spot_size = 2
ax.scatter(trades_agg["day"][:-1], longs[:-1], label="num longs", c="blue", s=spot_size)
ax.scatter(trades_agg["day"][:-1], shorts[:-1], label="num shorts", c="orange", s=spot_size)
ax.legend()
ax.set_xlabel("day")
ax.set_ylabel("number of positions")
text_handle = ax.set_title("Open positions")
fig.set_size_inches(fig_size)


# %%
fig, axes, _ = output_utils.get_gridspec_subplots(nrows=1, ncols=1)
ax = trades.iloc[:-1].plot(x="trade_number", y="share_reserves", ax=axes[0], c="blue")
ax = trades.iloc[:-1].plot(x="trade_number", y="bond_reserves", ax=axes[0], c="orange")
ax.set_xlabel("trade number")
ax.set_ylabel("reserve amount")
ax.set_title("Market reserves")
fig.set_size_inches(fig_size)

# %%
lp_trades = trades.groupby("day").agg({f"agent_{0}_pnl": ["sum"]})
lp_trades.columns = ["_".join(col).strip() for col in lp_trades.columns.values]
lp_trades = lp_trades.reset_index()

sallys = [
    agent_id
    for agent_id in range(len(simulator.agents))
    if simulator.agents[agent_id].__class__.__name__ == "ShortSally"
]
sally_trades = trades.groupby("day").agg({f"agent_{agent_id}_pnl": ["sum"] for agent_id in sallys})
sally_trades.columns = ["_".join(col).strip() for col in sally_trades.columns.values]
sally_trades = sally_trades.reset_index()

louies = [
    agent_id
    for agent_id in range(len(simulator.agents))
    if simulator.agents[agent_id].__class__.__name__ == "LongLouie"
]
louies_trades = trades.groupby("day").agg({f"agent_{agent_id}_pnl": ["sum"] for agent_id in louies})
louies_trades.columns = ["_".join(col).strip() for col in louies_trades.columns.values]
louies_trades = louies_trades.reset_index()

fig, axes, _ = output_utils.get_gridspec_subplots(nrows=1, ncols=2, wspace=0.3)

ax = axes[0]
ax.plot(trades_agg["day"][:-1], lp_trades.sum(axis=1)[:-1], label="LP pnl", c="blue")
ax.set_ylabel("base")

ax = axes[1]
ax.plot(trades_agg["day"][:-1], sally_trades.sum(axis=1)[:-1], label="sally pnl", c="orange")
ax.plot(trades_agg["day"][:-1], louies_trades.sum(axis=1)[:-1], label="Louie pnl", c="black")

for ax in axes:
    ax.set_xlabel("day")
    ax.legend()
text_handle = fig.suptitle("Agent profitability")
fig.set_size_inches((fig_size[0] * 2, fig_size[1]))

# %%
trades_agg = trades.groupby("day").agg({"share_reserves": ["sum"], "bond_reserves": ["sum"]})
trades_agg.columns = ["_".join(col).strip() for col in trades_agg.columns.values]
trades_agg = trades_agg.reset_index()

fix, axes, _ = output_utils.get_gridspec_subplots(nrows=1, ncols=1)
ax = trades_agg.iloc[:-1].plot(x="day", y="share_reserves_sum", ax=axes[0], label="share reserves", c="blue")
ax = trades_agg.iloc[:-1].plot(x="day", y="bond_reserves_sum", ax=axes[0], label="bond reserves", c="orange")
ax.set_xlabel("day")
ax.set_ylabel("number of tokenx")
text_handle = ax.set_title("Reserve levels")
fig.set_size_inches(fig_size)

# %%
total_longs_and_shorts = {
    f"agent_{agent_id}_total_longs": ["mean"]  # total_longs is an aggregate value recomputed each trade
    for agent_id in range(len(simulator.agents))
}
total_longs_and_shorts.update(
    {
        f"agent_{agent_id}_total_shorts": ["mean"]  # total_shorts is an aggregate value recomputed each trade
        for agent_id in range(len(simulator.agents))
    }
)
trades_agg = trades.groupby("day").agg(total_longs_and_shorts)
trades_agg.columns = ["_".join(col).strip() for col in trades_agg.columns.values]
trades_agg = trades_agg.reset_index()
longs = trades_agg.filter(regex="total_longs").sum(axis=1)
shorts = trades_agg.filter(regex="total_shorts").sum(axis=1)

fix, axes, _ = output_utils.get_gridspec_subplots(nrows=1, ncols=1)
ax = axes[0]
ax.plot(trades_agg["day"][:-1], longs[:-1], label="total longs", c="blue")
ax.plot(trades_agg["day"][:-1], shorts[:-1], label="total shorts", c="orange")
ax.legend()
ax.set_xlabel("day")
ax.set_ylabel("base")
text_handle = ax.set_title("Value of open positions")
fig.set_size_inches(fig_size)

# %%
trades_agg = trades.groupby("day").agg(
    {
        "base_buffer": ["mean"],
        "bond_buffer": ["mean"],
        "spot_price": ["mean"],
    }
)
trades_agg.columns = ["_".join(col).strip() for col in trades_agg.columns.values]
trades_agg = trades_agg.reset_index()
trades_agg["bond_buffer_mean_in_base"] = trades_agg["bond_buffer_mean"] / trades_agg["spot_price_mean"]

fig, axes, _ = output_utils.get_gridspec_subplots()
ax = trades_agg.iloc[:-1].plot(x="day", y="base_buffer_mean", ax=axes[0], c="blue")
ax = trades_agg.iloc[:-1].plot(x="day", y="bond_buffer_mean_in_base", ax=axes[0], c="orange")
text_handle = ax.set_title("amount locked")
ax.set_xlabel("day")
ax.set_ylabel("buffer quantities (in base units)")
fig.set_size_inches(fig_size)

# %%
trades_agg = trades.groupby("day").agg({"spot_price": ["mean"]})
trades_agg.columns = ["_".join(col).strip() for col in trades_agg.columns.values]
trades_agg = trades_agg.reset_index()
trades_agg["leverage"] = 1 / (1 - trades_agg["spot_price_mean"])

fig, axes, _ = output_utils.get_gridspec_subplots()
ax = axes[0]
ax.plot(trades_agg["day"][:-1], trades_agg["leverage"][:-1])
text_handle = ax.set_title("Short leverage")
ax.set_xlabel("day")
ax.set_ylabel("1/(1-p)")
fig.set_size_inches(fig_size)

# %%

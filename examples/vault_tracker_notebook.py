"""Agent that tracks the vault apr"""
# %%
from __future__ import annotations

import os

import numpy as np
from numpy.random._generator import Generator as NumpyGenerator
import matplotlib.pyplot as plt
import pandas as pd
from scipy import special

import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.types as types
import elfpy.utils.outputs as output_utils
import elfpy.utils.post_processing as post_processing

from elfpy import WEI, PRECISION_THRESHOLD
from elfpy.simulators import Config
from elfpy.agents.agent import Agent
from elfpy.utils import sim_utils
from elfpy.math import FixedPoint

# pylint: disable=too-many-arguments
# pylint: disable=too-many-branches
# pylint: disable=too-many-locals
# pylint: disable=invalid-name
# pylint: disable=not-an-iterable
# pylint: disable=unsubscriptable-object
# pyright: reportOptionalMemberAccess=false, reportGeneralTypeIssues=false
# pyright: reportOptionalSubscript=false, reportUnboundVariable=false


# %% [markdown]
# ### Setup experiment parameters


# %%
def homogeneous_poisson(rng: NumpyGenerator, rate: float, tmax: int, bin_size: int = 1) -> np.ndarray:
    """Generate samples from a homogeneous Poisson distribution

    Attributes
    ----------
    rng: np.random.Generator
        random number generator with preset seed
    rate: float
        number of events per time interval (units of 1/days)
    tmax: float
        total number of days (units of days; sets distribution support)
    bin_size: float
        resolution of the simulation
    """
    nbins = np.floor(tmax / bin_size).astype(int)
    prob_of_spike = rate * bin_size
    events = (rng.random(nbins) < prob_of_spike).astype(int)
    return events


def event_generator(rng, n_trials, rate, tmax, bin_size):
    """Generate samples from the poisson distribution"""
    for _ in range(n_trials):
        yield homogeneous_poisson(rng, rate, tmax, bin_size)


def poisson_prob(k, lam):
    """https://en.wikipedia.org/wiki/Poisson_distribution"""
    return lam**k / special.factorial(k) * np.exp(-lam)


def vault_flip_probs(apr: float, min_apr: float = 0.0, max_apr: float = 1.0, num_flip_bins: int = 100):
    """
    probability of going up is 1 when apr is min
    probability of going down is 1 when apr is max
    probability is 0.5 either way when apr is half way between max and min
    """
    aprs = np.linspace(min_apr, max_apr, num_flip_bins)

    def get_index(value, array):
        return (np.abs(array - value)).argmin()

    apr_index = get_index(apr, aprs)  # return whatever value in aprs array that apr is closest to
    up_probs = np.linspace(1, 0, num_flip_bins)
    up_prob = up_probs[apr_index]
    down_prob = 1 - up_prob
    return down_prob, up_prob


def poisson_vault_apr(
    rng: NumpyGenerator,
    num_trading_days: int,
    initial_apr: float,
    jump_size: float,
    vault_jumps_per_year: int,
    direction: str,
    lower_bound: float = 0.0,
    upper_bound: float = 1.0,
    num_flip_bins: int = 100,
) -> list:
    """Computes a variable APR from a poisson distribution"""
    # vault rate changes happen once every vault_jumps_per_year, on average
    num_bins = 365
    bin_size = 1
    rate = vault_jumps_per_year / num_bins
    tmax = num_bins
    do_jump = homogeneous_poisson(rng, rate, tmax, bin_size)
    vault_apr = np.array([initial_apr] * num_trading_days)
    for day in range(1, num_trading_days):
        if not do_jump[day]:
            continue
        if direction == "up":
            sign = 1
        elif direction == "down":
            sign = -1
        elif direction == "random":
            sign = rng.choice([-1, 1], size=1).item()  # flip a fair coin
        elif direction == "random_weighted":
            probs = vault_flip_probs(vault_apr[day], lower_bound, upper_bound, num_flip_bins)
            sign = rng.choice([-1, 1], p=probs, size=1).item()  # flip a weighted coin
        else:
            raise ValueError(f"Direction must be 'up', 'down', 'weighted_random', or 'random'; not {direction}")
        step = sign * jump_size
        apr = np.minimum(upper_bound, np.maximum(lower_bound, vault_apr[day] + step))
        vault_apr[day:] = apr
    return vault_apr.tolist()


# %%
def DSR_historical(num_dates=90):
    """Extracts the DSR from historical data"""
    dsr = pd.read_csv(
        "https://s3-sim-repo-0.s3.us-east-2.amazonaws.com/Data/HIST_DSR_D.csv", index_col=0, infer_datetime_format=True
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


config = Config()
# config.init_lp = False
config.random_seed = 123

config.log_filename = "vault_tracker"  # Output filename for logging

config.log_level = "DEBUG"  # Logging level, should be in ["DEBUG", "INFO", "WARNING"]. ERROR to suppress all logging.
config.pricing_model_name = "Hyperdrive"  # can be yieldspace or hyperdrive

config.num_trading_days = 365  # Number of simulated trading days, default is 180
config.num_position_days = config.num_trading_days  # term length
config.num_blocks_per_day = 1  # 7200 # Blocks in a given day (7200 means ~12 sec per block)
config.curve_fee_multiple = 0  # 0.10 # fee multiple applied to the price slippage (1-p) collected on trades
config.flat_fee_multiple = 0.000  # 5 bps

config.scratch["trade_chance"] = 4 / (
    config.num_trading_days * config.num_blocks_per_day
)  # on a given block, an agent will trade with probability `trade_chance`

config.target_fixed_apr = 0.05  # 5 # target fixed APR of the initial market after the LP
config.target_liquidity = 5_000_000  # target total liquidity of the initial market, before any trades

config.scratch["vault_apr_init"] = 0.05  # Initial vault APR
config.scratch["vault_apr_jump_size"] = 0.002  # Scale of the vault APR change (vault_apr (+/-)= jump_size)
config.scratch["vault_jumps_per_year"] = 100  # 4 # The average number of jumps per year
# The direction of a rate change. Can be 'up', 'down', or 'random'.
config.scratch["vault_apr_jump_direction"] = "random_weighted"
config.scratch["vault_apr_lower_bound"] = 0.01  # minimum allowable vault apr
config.scratch["vault_apr_upper_bound"] = 0.09  # maximum allowable vault apr

config.variable_apr = poisson_vault_apr(
    rng=config.rng,
    num_trading_days=config.num_trading_days,
    initial_apr=config.scratch["vault_apr_init"],
    jump_size=config.scratch["vault_apr_jump_size"],
    vault_jumps_per_year=config.scratch["vault_jumps_per_year"],
    direction=config.scratch["vault_apr_jump_direction"],
    lower_bound=config.scratch["vault_apr_lower_bound"],
    upper_bound=config.scratch["vault_apr_upper_bound"],
)

# %% [markdown]
# ### Setup agents


# %%
def get_biggest_position(position_dict) -> FixedPoint | None:
    """Return the biggest trade in the position_dict"""
    biggest_position = None
    for mint_time, position in position_dict.items():
        if biggest_position is None or position.balance > biggest_position["balance"]:
            biggest_position = position.__dict__
            biggest_position.update({"mint_time": mint_time})
    return biggest_position


class RegularGuy(Agent):
    """
    Agent that tracks the vault APR, trading both long and short by default
    """

    def __init__(
        self,
        rng: NumpyGenerator,
        trade_chance: float,
        wallet_address: int,
        budget: FixedPoint = FixedPoint("10_000.0"),
    ) -> None:
        """Add custom stuff then call basic policy init"""
        self.trade_long = True  # default to allow easy overriding
        self.trade_short = True  # default to allow easy overriding
        self.trade_chance = trade_chance
        self.rng = rng
        self.last_think_time = None
        self.threshold = FixedPoint(self.rng.normal(loc=0, scale=0.005))
        super().__init__(wallet_address, budget)

    def action(self, market: hyperdrive_market.Market) -> list[hyperdrive_actions.MarketAction]:
        """Implement a random user strategy

        The agent performs one of four possible trades:
            [OPEN_LONG, OPEN_SHORT, CLOSE_LONG, CLOSE_SHORT]
            with the condition that close actions can only be performed after open actions

        The amount opened and closed is random, within constraints given by agent budget & market reserve levels

        Parameters
        ----------
        market : Market
            the trading market

        Returns
        -------
        action_list : list[MarketAction]
        """
        action_list = []
        gonna_trade = self.rng.choice([True, False], p=[self.trade_chance, 1 - self.trade_chance])
        if gonna_trade:
            # User can always open a trade, and can close a trade if one is open
            available_actions = []
            has_opened_short = bool(any((short.balance > 0 for short in self.wallet.shorts.values())))
            has_opened_long = bool(any((long.balance > 0 for long in self.wallet.longs.values())))
            if market.fixed_apr > market.market_state.variable_apr + self.threshold:
                # we want to make rate to go DOWN, so BUY PTs
                if has_opened_short is True:
                    available_actions = [hyperdrive_actions.MarketActionType.CLOSE_SHORT]  # buy to close
                elif self.trade_long is True:
                    available_actions += [hyperdrive_actions.MarketActionType.OPEN_LONG]  # buy to open
            else:
                # we want to make rate go UP, so SELL PTs
                if has_opened_long is True:
                    available_actions = [hyperdrive_actions.MarketActionType.CLOSE_LONG]
                elif self.trade_short is True:
                    available_actions += [hyperdrive_actions.MarketActionType.OPEN_SHORT]  # sell to open
            if available_actions:  # continue only if there are available actions
                action_type = self.rng.choice(
                    np.array(available_actions), size=1
                ).item()  # choose one random trade type
                pt_needed = abs(
                    market.pricing_model.calc_bond_reserves(
                        target_apr=market.market_state.variable_apr,
                        time_remaining=market.position_duration,
                        market_state=market.market_state,
                    )
                    - market.market_state.bond_reserves
                ) / FixedPoint("2.0")
                amount_to_trade_base = (
                    min(FixedPoint("100_000.0"), pt_needed * market.spot_price) if pt_needed > 0 else FixedPoint(0)
                )
                if market.spot_price == 0:
                    amount_to_trade_pt = FixedPoint("inf")
                else:
                    amount_to_trade_pt = amount_to_trade_base / market.spot_price
                if action_type == hyperdrive_actions.MarketActionType.OPEN_SHORT:
                    max_short = self.get_max_short(market)
                    # TODO: This is a hack until we fix get_max
                    max_short = max_short / FixedPoint("100.0")
                    if max_short > WEI + PRECISION_THRESHOLD:  # if max_short is greater than the minimum eth amount
                        trade_amount = np.maximum(
                            WEI + PRECISION_THRESHOLD, min(max_short, amount_to_trade_pt)
                        )  # WEI + PRECISION_THRESHOLD <= trade_amount <= max_short
                        action_list = [
                            types.Trade(
                                market=types.MarketType.HYPERDRIVE,
                                trade=hyperdrive_actions.MarketAction(
                                    action_type=action_type,
                                    trade_amount=trade_amount,
                                    wallet=self.wallet,
                                    mint_time=market.block_time.time,
                                ),
                            )
                        ]
                elif action_type == hyperdrive_actions.MarketActionType.OPEN_LONG:
                    max_long = self.get_max_long(market)
                    # TODO: This is a hack until we fix get_max
                    max_long = max_long / FixedPoint("100.0")
                    if max_long > WEI + PRECISION_THRESHOLD:  # if max_long is greater than the minimum eth amount
                        trade_amount = max(WEI + PRECISION_THRESHOLD, min(max_long, amount_to_trade_base))
                        action_list = [
                            types.Trade(
                                market=types.MarketType.HYPERDRIVE,
                                trade=hyperdrive_actions.MarketAction(
                                    action_type=action_type,
                                    trade_amount=trade_amount,
                                    wallet=self.wallet,
                                    mint_time=market.block_time.time,
                                ),
                            )
                        ]
                elif action_type == hyperdrive_actions.MarketActionType.CLOSE_SHORT:
                    biggest_short = get_biggest_position(self.wallet.shorts)
                    trade_amount = max(WEI + PRECISION_THRESHOLD, min(amount_to_trade_pt, biggest_short["balance"]))
                    action_list = [
                        types.Trade(
                            market=types.MarketType.HYPERDRIVE,
                            trade=hyperdrive_actions.MarketAction(
                                action_type=action_type,
                                trade_amount=trade_amount,
                                wallet=self.wallet,
                                mint_time=biggest_short["mint_time"],
                            ),
                        )
                    ]
                elif action_type == hyperdrive_actions.MarketActionType.CLOSE_LONG:
                    biggest_long = get_biggest_position(self.wallet.longs)
                    trade_amount = np.maximum(
                        WEI + PRECISION_THRESHOLD, np.minimum(amount_to_trade_pt, biggest_long["balance"])
                    )
                    action_list = [
                        types.Trade(
                            market=types.MarketType.HYPERDRIVE,
                            trade=hyperdrive_actions.MarketAction(
                                action_type=action_type,
                                trade_amount=trade_amount,
                                wallet=self.wallet,
                                mint_time=biggest_long["mint_time"],
                            ),
                        )
                    ]
                if action_list and (market.block_time.time * 365) % 36 <= 1:
                    print(
                        f"t={market.block_time.time*365:.0f}: "
                        f"F:{market.fixed_apr:.3%} V:{market.market_state.variable_apr:.3%} "
                        f"agent #{self.wallet.address:03.0f} is going to {action_type} of size {trade_amount}",
                    )
        return action_list


def get_example_agents(
    rng: NumpyGenerator,
    budget: FixedPoint,
    new_agents: float,
    existing_agents: float = 0,
    direction: str = None,
    agent_trade_chance: float = 1,
) -> list[Agent]:
    """Instantiate a set of custom agents"""
    agents = []
    new_agents = int(new_agents)
    existing_agents = int(existing_agents)
    print(f"Creating {new_agents} new agents from {existing_agents} existing agents to {existing_agents + new_agents}")
    for address in range(existing_agents, existing_agents + new_agents):
        example_agent = RegularGuy(
            rng=rng,
            trade_chance=agent_trade_chance,
            wallet_address=address,
            budget=budget,
        )
        if direction is not None:
            if direction == "short":
                example_agent.trade_long = False
            if direction == "long":
                example_agent.trade_short = False
        example_agent.log_status_report()
        agents += [example_agent]
    return agents


# %% [markdown]
# ### Setup simulation objects

# %%
# delete old log file
if os.path.exists(config.log_filename):
    os.remove(config.log_filename)

# define root logging parameters
output_utils.setup_logging(
    log_filename=config.log_filename,
    log_level=output_utils.text_to_log_level(config.log_level),
)

simulator = sim_utils.get_simulator(config)
simulator.collect_and_execute_trades()


# %% [markdown]
# ### Run the simulation

# %%
num_agents = 100  # int specifying how many agents you want to simulate
agent_budget = FixedPoint(9.65 * 1e6 / num_agents)
# add a bunch of regular guys
short_agents = get_example_agents(
    rng=simulator.rng,
    budget=agent_budget,
    new_agents=num_agents / 2,
    existing_agents=1,
    direction="short",
    agent_trade_chance=config.scratch["trade_chance"],
)
long_agents = get_example_agents(
    rng=simulator.rng,
    budget=agent_budget,
    new_agents=num_agents / 2,
    existing_agents=1 + num_agents / 2,
    direction="long",
    agent_trade_chance=config.scratch["trade_chance"],
)
simulator.add_agents(short_agents + long_agents)
# add a singular regular guy
# regular_guy = get_example_agents(rng=simulator.rng, budget=9.65*1e6, new_agents=1, existing_agents=1, trade_chance=1)
# simulator.add_agents(regular_guy)
print(f"Simulator has {len(simulator.agents)} agents")
for idx, agent in enumerate(short_agents):
    if idx in [0, num_agents / 2 - 1]:
        print(f"Agent #{agent.wallet.address} is a short: {agent.trade_short=} {agent.trade_long=}")
for idx, agent in enumerate(long_agents):
    if idx in [0, num_agents / 2 - 1]:
        print(f"Agent #{agent.wallet.address} is a long: {agent.trade_short=} {agent.trade_long=}")

# %%
# run the simulation
simulator.run_simulation()

# %%
# convert simulation state to a pandas dataframe
trades = post_processing.compute_derived_variables(simulator)
for col in trades:
    if col.startswith("agent") and not col.endswith("lp_tokens"):
        divisor = 1e6  # 1 million divisor for everyone
        trades[col] = trades[col] / divisor  # pylint: disable=unsupported-assignment-operation
print(f"number of trades = {len(trades)}")
cols = trades.columns.to_list()
cols_to_display = ["day"] + [cols[10]] + cols[15:18] + ["share_reserves", "bond_reserves", "total_liquidity_usd"]
print(trades[cols_to_display].head(5))

# %%
# aggregate data
keep_columns = [
    "day",
]
trades_agg = trades.groupby(keep_columns).agg(
    {
        "spot_price": ["mean"],
        "delta_base_abs": ["sum", "count"],
        "share_reserves": ["mean"],
        "bond_reserves": ["mean"],
        "lp_total_supply": ["mean"],
        "agent_0_pnl_no_mock": ["mean"],
    }
)
trades_agg.columns = ["_".join(col).strip() for col in trades_agg.columns.values]
trades_agg = trades_agg.reset_index()
print(trades_agg.head(5).style.hide_index())


# %%
def get_pnl_excluding_agent_0_no_mock_with_day(trades_df: pd.DataFrame) -> pd.DataFrame:
    """Returns Profit and Loss Column for every agent except for agent 0 from post-processing"""
    cols_to_return = ["day"] + [col for col in trades_df if col.startswith("agent") and col.endswith("pnl_no_mock")]
    cols_to_return.remove("agent_0_pnl_no_mock")
    return trades_df[cols_to_return].groupby("day").mean()


def get_pnl_excluding_agent_0_with_day(trades_df: pd.DataFrame) -> pd.DataFrame:
    """Returns Profit and Loss Column for every agent except for agent 0 from post-processing"""
    cols_to_return = ["day"] + [col for col in trades_df if col.startswith("agent") and col.endswith("pnl")]
    cols_to_return.remove("agent_0_pnl")
    return trades_df[cols_to_return].groupby("day").mean()


def nice_ticks(tick_ax):
    """Make ticks nice"""
    xtick_step = max(1, config.num_trading_days // 10)  # divide by 10, but at least 1
    xticks = list(range(0 + xtick_step - 1, config.num_trading_days + 1, xtick_step))
    if xtick_step > 1:
        xticks = [0] + xticks
        xticklabels = ["1"] + [str(x + 1) for x in xticks[1:]]
    else:
        xticklabels = [str(x + 1) for x in xticks]
    tick_ax.set_xticks(xticks)
    tick_ax.set_xticklabels(xticklabels)


def set_labels(label_ax, title, xlabel, ylabel):
    """Set labels"""
    label_ax.set_title(title)
    label_ax.set_xlabel(xlabel)
    label_ax.set_ylabel(ylabel)


data_mock = get_pnl_excluding_agent_0_with_day(trades)
data_no_mock = get_pnl_excluding_agent_0_no_mock_with_day(trades)

# print specific agent info
# agent_num=12
# print(trades.loc[:,['day','run_trade_number']+[col for col in trades if col.startswith(f"agent_{agent_num}_")]])
# print(trades.loc[:,[f"agent_{agent_num}_total_longs",f"agent_{agent_num}_total_shorts"]].max())


# %%
exclude_first_day = True
exclude_last_day = True
fig, ax = plt.subplots(5, 1, sharex=True, gridspec_kw={"wspace": 0.3, "hspace": 0.0}, figsize=(10, 12))
first_trade_that_is_on_second_day = min(trades.index[trades.day > 0])
start_idx = first_trade_that_is_on_second_day if exclude_first_day is True else 0
first_trade_that_is_on_last_day = min(trades.index[trades.day == max(trades.day)])
end_idx = first_trade_that_is_on_last_day - 1 if exclude_last_day is True else len(trades)

# first subplot
y_data = trades.loc[start_idx:end_idx, ["share_reserves", "bond_reserves"]]
x_data = trades.loc[start_idx:end_idx, ["day"]]
ax[0].step(x_data, y_data)
ax[0].set_ylabel("# of tokens")
ax[0].legend(loc="best", labels=["Share Reserves", "Bond Reserves"])

# second subplot
y_data = trades.loc[start_idx:end_idx, ["lp_total_supply", "agent_0_lp_tokens"]]
ax[1].step(x_data, y_data)
ax[1].set_ylabel("# of tokens")
ax[1].legend(loc="best", labels=["LP Reserves", "Agent 0 LP Tokens"])

# third subplot
y_data = trades.loc[start_idx:end_idx, ["spot_price"]]
ax[2].step(x_data, y_data)
ax[2].legend(loc="best", labels=["Spot Price"])

# fourth subplot
y_data = trades.loc[start_idx:end_idx, ["fixed_apr", "variable_apr"]]
ax[3].step(x_data, y_data)
ax[3].set_yticklabels([f"{(i):.1%}" for i in ax[3].get_yticks()])
ax[3].legend(loc="best", labels=["Fixed APR", "Variable APR"])

# fifth subplot
lp_pnl = trades.loc[start_idx:end_idx, ["agent_0_pnl"]]
ax[4].step(x_data, lp_pnl)
# trader_pnl = data_no_mock.loc[data_no_mock.index>0,:].sum(axis=1)
trader_pnl = trades.loc[
    start_idx:end_idx,
    [
        col
        for col in trades
        if str(col).startswith("agent") and str(col).endswith("pnl") and not str(col).startswith("agent_0")
    ],
]
all_traders = trader_pnl.sum(axis=1)
half_cols = trader_pnl.shape[1] // 2
short_traders = trader_pnl.loc[:, trader_pnl.columns[:half_cols]].sum(axis=1) * 2
long_traders = trader_pnl.loc[:, trader_pnl.columns[half_cols:]].sum(axis=1) * 2
ax[4].step(x_data, all_traders)
ax[4].step(x_data, short_traders, c="red")
ax[4].step(x_data, long_traders, c="black")
ax[4].set_ylabel("PnL in millions")
ax[4].legend(loc="best", labels=["LP PnL", "All traders", "Shorts only", "Longs only"])
ax[4].set_xlabel("Day")


# %%
def plot_pnl(pnl, pnl_ax, label, last_day):
    """plot the PNL"""
    # separate first half of agents, which are set to trade short
    # from second half of agents, which are set to trade long
    columns = pnl.columns.to_list()
    if len(columns) == 1:
        pnl_ax.plot(pnl.iloc[1:, :], linestyle="-", linewidth=0.5, alpha=0.5)
        pnl_ax.plot(pnl.iloc[1:, :], c="black", label=f"{label}, final_value={pnl.iloc[-1,0]:.5f}", linewidth=2)
    else:
        half = int(len(columns) / 2)
        short_pnl = pnl.loc[1:, columns[:half]].mean(axis=1)
        long_pnl = pnl.loc[1:, columns[half:]].mean(axis=1)
        pnl_ax.plot(pnl.loc[1:, columns[:half]], linestyle="-", linewidth=0.5, alpha=0.5, c="red")
        pnl_ax.plot(pnl.loc[1:, columns[half:]], linestyle="-", linewidth=0.5, alpha=0.5, c="black")
        pnl_ax.plot(short_pnl, c="red", label=f"Short {label}, final value={short_pnl.iloc[-1]:.5f}", linewidth=2)
        pnl_ax.plot(long_pnl, c="black", label=f"Long {label}, final_value={long_pnl.iloc[-1]:.5f}", linewidth=2)
    # grey area where day is last day
    pnl_ax.set_ylabel("PNL in millions")
    pnl_ax.axvspan(last_day, len(short_pnl), color="grey", alpha=0.2, label="Last day")
    pnl_ax.legend()


fig, ax = plt.subplots(1, 1, figsize=(6, 5), sharex=True, gridspec_kw={"wspace": 0.0, "hspace": 0.0})
first_trade_that_is_on_last_day = min(trades.index[trades.day == max(trades.day)])
plot_pnl(data_mock, pnl_ax=ax, label="Unrealized Market Value", last_day=first_trade_that_is_on_last_day)
# plot_pnl(data_no_mock, pnl_ax=ax[1], label="Realized Market Value", last_day=first_trade_that_is_on_last_day)

ax.set_title("Trader PNL over time")

# xtick_step = trades.day.max()//10
# ax.set_xticks([0]+[x for x in range(xtick_step-1, config.num_trading_days + 1, xtick_step)])
# ax.set_xticklabels(['1']+[str(x+1) for x in range(xtick_step-1, config.num_trading_days + 1, xtick_step)])
nice_ticks(ax)

plt.gca().set_xlabel("Day")

# %%
if len(trades_agg) > 1:  # if there were multiple trades
    exclude_last_day = True
    exclude_first_day = True
    num_agents = 1
    start_idx = 0 if exclude_first_day is False else 1
    first_trade_that_is_on_last_day = min(trades_agg.index[trades_agg.day == max(trades_agg.day)])
    end_idx = len(trades_agg) - 2 if exclude_last_day is True else len(trades_agg) - 1
    data = trades_agg.loc[start_idx:end_idx, "agent_0_pnl_no_mock_mean"]

    fig, ax = plt.subplots(3, 1, sharex=False, gridspec_kw={"wspace": 0.3, "hspace": 0.2}, figsize=(6, 15))

    # first subplot
    ax[0].plot(
        trades_agg.loc[start_idx:end_idx, "day"],
        data,
        label=f"mean = {trades_agg.loc[end_idx,'agent_0_pnl_no_mock_mean']:.3f}",
    )
    nice_ticks(ax[0])
    set_labels(ax[0], title="LP PNL Over Time", xlabel="Day", ylabel="PnL in millions")

    # second subplot
    ax[1].bar(
        trades_agg.loc[start_idx:end_idx, "day"],
        trades_agg.loc[start_idx:end_idx, "delta_base_abs_sum"] / 1000,
        label=f"mean = {trades_agg.loc[start_idx:end_idx,'delta_base_abs_sum'].mean():,.0f}",
    )
    ax[1].legend(loc="best")
    nice_ticks(ax[1])
    set_labels(ax[1], title="Market Volume", xlabel="Day", ylabel="Base in thousands")

    # third subplot
    ax[2].bar(
        trades_agg.loc[start_idx:end_idx, "day"],
        trades_agg.loc[start_idx:end_idx, "delta_base_abs_count"],
        label=f"mean = {trades_agg.loc[start_idx:end_idx,'delta_base_abs_count'].mean():,.1f}",
    )
    ax[2].legend(loc="best")
    nice_ticks(ax[2])
    set_labels(ax[2], title="# of trades", xlabel="Day", ylabel="# of trades")

# %%

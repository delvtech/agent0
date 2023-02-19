# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.4
#   kernelspec:
#     display_name: elf-env
#     language: python
#     name: python3
# ---

# + id="efreB4W-4u1q"
from __future__ import annotations
from typing import TYPE_CHECKING
import time

import numpy as np
from numpy.random._generator import Generator
from scipy import special
import matplotlib.pyplot as plt
import pandas as pd

from elfpy import WEI
from elfpy.types import MarketActionType, MarketAction, Config
from elfpy.agent import Agent
from elfpy.markets import Market
from elfpy.utils import sim_utils
import elfpy.utils.outputs as output_utils
import elfpy.utils.post_processing as post_processing

if TYPE_CHECKING:
    from typing import Optional

# + [markdown] id="MMgaUflvLPnq"
# ### Setup experiment parameters


# + id="_PY2dAov5nxy"
def homogeneous_poisson(rng: Generator, rate: float, tmax: int, bin_size: int = 1) -> np.ndarray:
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

    def get_index(array, value):
        return (np.abs(array - value)).argmin()

    aprs = np.linspace(min_apr, max_apr, num_flip_bins)
    apr_index = get_index(apr, aprs)  # return whatever value in aprs array that apr is closest to
    up_probs = np.linspace(1, 0, num_flip_bins)
    up_prob = up_probs[apr_index]
    down_prob = 1 - up_prob
    return (down_prob, up_prob)


def poisson_vault_apr(
    rng: Generator,
    num_trading_days: int,
    initial_apr: float,
    jump_size: float,
    vault_jumps_per_year: int,
    direction: str,
    lower_bound: float = 0.0,
    upper_bound: float = 1.0,
    num_flip_bins: int = 100,
) -> list:
    """calculate stochastic APR using a poisson process"""
    num_bins = 365  # vault rate changes happen once every vault_jumps_per_year, on average
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


# +
def get_biggest_position(position_dict):
    """Return the biggest trade in the position_dict"""
    biggest_position = None
    for mint_time, position in position_dict.items():
        if biggest_position is None or position.balance > biggest_position["balance"]:
            biggest_position = position.__dict__
            biggest_position.update({"mint_time": mint_time})
    return biggest_position

    # + [markdown] id="gMKQLsMiLd-_"
    # ### Setup agents


class RegularGuy(Agent):
    """
    Agent that tracks the vault APR, trading both long and short by default
    """

    def __init__(self, rng: Generator, trade_chance: float, wallet_address: int, budget: int = 10_000) -> None:
        """Add custom stuff then call basic policy init"""
        self.trade_long = True  # default to allow easy overriding
        self.trade_short = True  # default to allow easy overriding
        self.trade_chance = trade_chance
        self.rng = rng
        self.last_think_time = None
        self.threshold = self.rng.normal(loc=0, scale=0.005)
        super().__init__(wallet_address, budget)

    def action(self, market: Market) -> list[MarketAction]:
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
            if market.apr > market.market_state.vault_apr + self.threshold:
                # we want to make rate to go DOWN, so BUY PTs
                if has_opened_short is True:
                    available_actions = [MarketActionType.CLOSE_SHORT]  # buy to close
                elif self.trade_long is True:
                    available_actions += [MarketActionType.OPEN_LONG]  # buy to open
            else:
                # we want to make rate go UP, so SELL PTs
                if has_opened_long is True:
                    available_actions = [MarketActionType.CLOSE_LONG]
                elif self.trade_short is True:
                    available_actions += [MarketActionType.OPEN_SHORT]  # sell to open
            if available_actions != []:  # continue only if there are available actions
                action_type = self.rng.choice(available_actions, size=1)  # choose one random trade type
                PT_needed = (
                    abs(
                        market.pricing_model.calc_bond_reserves(
                            target_apr=market.market_state.vault_apr,
                            time_remaining=market.position_duration,
                            market_state=market.market_state,
                        )
                        - market.market_state.bond_reserves
                    )
                    / 2
                )
                amount_to_trade_base = min(100_000, PT_needed * market.spot_price) if PT_needed > 0 else 0
                if market.spot_price == 0:
                    amount_to_trade_pt = np.Inf
                else:
                    amount_to_trade_pt = amount_to_trade_base / market.spot_price
                if action_type == MarketActionType.OPEN_SHORT:
                    max_short = self.get_max_short(market)
                    if max_short > WEI:  # if max_short is greater than the minimum eth amount
                        trade_amount = np.maximum(
                            WEI, np.minimum(max_short, amount_to_trade_pt)
                        )  # WEI <= trade_amount <= max_short
                        action_list = [
                            self.create_agent_action(
                                action_type=action_type, trade_amount=trade_amount, mint_time=market.time
                            ),
                        ]
                elif action_type == MarketActionType.OPEN_LONG:
                    max_long = self.get_max_long(market)
                    if max_long > WEI:  # if max_long is greater than the minimum eth amount
                        trade_amount = np.maximum(WEI, np.minimum(max_long, amount_to_trade_base))
                        action_list = [
                            self.create_agent_action(
                                action_type=action_type, trade_amount=trade_amount, mint_time=market.time
                            ),
                        ]
                elif action_type == MarketActionType.CLOSE_SHORT:
                    biggest_short = get_biggest_position(self.wallet.shorts)
                    trade_amount = np.maximum(WEI, np.minimum(amount_to_trade_pt, biggest_short["balance"]))
                    action_list = [
                        self.create_agent_action(
                            action_type=action_type, trade_amount=trade_amount, mint_time=biggest_short["mint_time"]
                        ),
                    ]
                elif action_type == MarketActionType.CLOSE_LONG:
                    biggest_long = get_biggest_position(self.wallet.longs)
                    trade_amount = np.maximum(WEI, np.minimum(amount_to_trade_pt, biggest_long["balance"]))
                    action_list = [
                        self.create_agent_action(
                            action_type=action_type, trade_amount=trade_amount, mint_time=biggest_long["mint_time"]
                        ),
                    ]
                if action_list != [] and (market.time * 365) % 36 <= 1:
                    print(
                        f"t={market.time*365:.0f}: F:{market.apr:.3%}V:{market.market_state.vault_apr:.3%}"
                        + f"agent #{self.wallet.address:03.0f} is going to {action_type} of size {trade_amount}",
                    )
        return action_list


def get_example_agents(
    rng: Generator,
    budget: int,
    new_agents: float,
    existing_agents: float = 0,
    direction: Optional[str] = None,
    trade_chance: float = 1,
) -> list[Agent]:
    """Instantiate a set of custom agents"""
    agents = []
    new_agents = int(new_agents)
    existing_agents = int(existing_agents)
    print(f"Creating {new_agents} new agents from {existing_agents} existing agents to {existing_agents + new_agents}")
    for address in range(existing_agents, existing_agents + new_agents):
        agent = RegularGuy(rng=rng, trade_chance=trade_chance, wallet_address=address, budget=budget)
        if direction is not None:
            if direction == "short":
                agent.trade_long = False
            if direction == "long":
                agent.trade_short = False
        agent.log_status_report()
        agents += [agent]
    return agents


# + id="hfwElUKJPQyC"
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


def nice_ticks(axe, config):
    """space out x-ticks appropriately for days, starting at 1, in 10 bins"""
    xtick_step = max(1, config.num_trading_days // 10)  # divide by 10, but at least 1
    xticks = [x for x in range(0 + xtick_step - 1, config.num_trading_days + 1, xtick_step)]
    if xtick_step > 1:
        xticks = [0] + xticks
        xticklabels = ["1"] + [str(x + 1) for x in xticks[1:]]
    else:
        xticklabels = [str(x + 1) for x in xticks]
    axe.set_xticks(xticks)
    axe.set_xticklabels(xticklabels)


def set_labels(axe, title, xlabel, ylabel):
    """assign labels to axis"""
    axe.set_title(title)
    axe.set_xlabel(xlabel)
    axe.set_ylabel(ylabel)


def plot_pnl(pnl, axe, label, last_day=None):
    """
    plot trader pnl, either in aggregate or separate
        last_day: if true, plots grey shaded area to identify the last day (only useful when x-axis is not day)
    """
    # separate first half of agents, which are set to trade short
    # from second half of agents, which are set to trade long
    columns = pnl.columns.to_list()
    if len(columns) == 1:
        axe.plot(pnl.iloc[1:, :], linestyle="-", linewidth=0.5, alpha=0.5)
        axe.plot(pnl.iloc[1:, :], c="black", label=f"{label}, final_value={pnl.iloc[-1,0]:.5f}", linewidth=2)
    else:
        num_agents = int(len(columns) / 2)
        short_pnl = pnl.loc[1:, columns[:num_agents]].mean(axis=1)
        long_pnl = pnl.loc[1:, columns[num_agents:]].mean(axis=1)
        axe.plot(pnl.loc[1:, columns[:num_agents]], linestyle="-", linewidth=0.5, alpha=0.5, c="red")
        axe.plot(pnl.loc[1:, columns[num_agents:]], linestyle="-", linewidth=0.5, alpha=0.5, c="black")
        axe.plot(short_pnl, c="red", label=f"Short {label}, final value={short_pnl.iloc[-1]:.5f}", linewidth=2)
        axe.plot(long_pnl, c="black", label=f"Long {label}, final_value={long_pnl.iloc[-1]:.5f}", linewidth=2)
    axe.set_ylabel("PNL in millions")
    if last_day:  # grey area where day is last day
        axe.axvspan(last_day, len(pnl), color="grey", alpha=0.2, label="Last day")
    axe.legend()


def post_process(simulator):
    """
    process simulator results into pandas dataframes
        trades = detailed pool and agent data on a trade-by-trade basis
        trades_agg = aggregation across days of price, volume, reserves, and LP pnl
        pnl = pnl of all agents excluding agent 0 (regular guys), also aggregated by day
    """
    trades = post_processing.compute_derived_variables(simulator)
    for col in trades:  # pylint: disable=not-an-iterable
        if col.startswith("agent") and not col.endswith("lp_tokens"):
            divisor = 1e6  # 1 million divisor for everyone
            trades.loc[:, col] = trades.loc[:, col] / divisor
    print(f"number of trades = {len(trades)}")

    # aggregate the data
    keep_columns = ["day"]
    trades_agg = trades.groupby(keep_columns).agg(
        {
            "spot_price": ["mean"],
            "delta_base_abs": ["sum", "count"],
            "share_reserves": ["mean"],
            "bond_reserves": ["mean"],
            "lp_reserves": ["mean"],
            "agent_0_pnl_no_mock": ["mean"],
        }
    )
    trades_agg.columns = ["_".join(col).strip() for col in trades_agg.columns.values]
    trades_agg = trades_agg.reset_index()
    pnl = get_pnl_excluding_agent_0_with_day(trades)
    return trades, trades_agg, pnl


def plot_and_save_results(config, trades, pnl, trades_agg, start_chart_num=1):
    """plot some charts then save them"""
    # prepare data
    exclude_first_day = True if config.num_trading_days >= 3 else False
    exclude_lat_day = True if config.num_trading_days >= 3 else False
    first_index_that_is_on_second_day = min(trades.index[trades.day > 0])
    start_idx = first_index_that_is_on_second_day if exclude_first_day is True else 0
    first_index_that_is_on_last_day = min(trades.index[trades.day == max(trades.day)])
    end_idx = first_index_that_is_on_last_day - 1 if exclude_lat_day is True else len(trades)
    trader_pnl = trades.loc[
        start_idx:end_idx,
        [col for col in trades if col.startswith("agent") and col.endswith("pnl") and not col.startswith("agent_0")],
    ]
    all_traders = trader_pnl.sum(axis=1)
    num_traders = trader_pnl.shape[1] // 2
    short_traders = trader_pnl.loc[:, trader_pnl.columns[:num_traders]].sum(axis=1) * 2
    long_traders = trader_pnl.loc[:, trader_pnl.columns[num_traders:]].sum(axis=1) * 2
    first_index_on_last_day_agg = min(trades_agg.index[trades_agg.day == max(trades_agg.day)])
    end_idx_agg = len(trades_agg) - 2 if exclude_lat_day is True else len(trades_agg) - 1
    trader_data = trades_agg.loc[start_idx:end_idx_agg, "agent_0_pnl_no_mock_mean"]

    def print_fig(chart_num, bbox_inches="tight", pad_inches=0):
        fig.savefig(fname=f"chart{chart_num:.0f}.svg", bbox_inches=bbox_inches, pad_inches=pad_inches)

    # CHART: 5-plot experiment summary
    chart_num = start_chart_num
    fig, axe = plt.subplots(5, 1, sharex=True, gridspec_kw={"wspace": 0.3, "hspace": 0.0}, figsize=(10, 12))
    # first subplot
    y_data = trades.loc[start_idx:end_idx, ["share_reserves", "bond_reserves"]]
    x_data = trades.loc[start_idx:end_idx, ["day"]]
    axe[0].step(x_data, y_data)
    axe[0].set_ylabel("# of tokens")
    axe[0].legend(loc="best", labels=["Share Reserves", "Bond Reserves"])
    # second subplot
    y_data = trades.loc[start_idx:end_idx, ["lp_reserves", "agent_0_lp_tokens"]]
    axe[1].step(x_data, y_data)
    axe[1].set_ylabel("# of tokens")
    axe[1].legend(loc="best", labels=["LP Reserves", "Agent 0 LP Tokens"])
    # third subplot
    y_data = trades.loc[start_idx:end_idx, ["spot_price"]]
    axe[2].step(x_data, y_data)
    axe[2].legend(loc="best", labels=["Spot Price"])
    # fourth subplot
    y_data = trades.loc[start_idx:end_idx, ["pool_apr", "vault_apr"]]
    axe[3].step(x_data, y_data)
    axe[3].set_yticklabels([f"{(i):.1%}" for i in axe[3].get_yticks()])
    axe[3].legend(loc="best", labels=["Pool APR", "Vault APR"])
    # fifth subplot
    lp_pnl = trades.loc[start_idx:end_idx, ["agent_0_pnl"]]
    axe[4].step(x_data, lp_pnl)
    axe[4].step(x_data, all_traders)
    axe[4].step(x_data, short_traders, c="red")
    axe[4].step(x_data, long_traders, c="black")
    axe[4].set_ylabel("PnL in millions")
    axe[4].legend(loc="best", labels=["LP PnL", "All traders", "Shorts only", "Longs only"])
    axe[4].set_xlabel("Day")
    print_fig(chart_num)

    # CHART: trader PNL
    chart_num += 1
    fig, axe = plt.subplots(1, 1, figsize=(6, 5), sharex=True, gridspec_kw={"wspace": 0.0, "hspace": 0.0})
    plot_pnl(pnl=pnl, label="Unrealized Market Value", axe=axe, last_day=first_index_on_last_day_agg)
    axe.set_title("Trader PNL over time")
    nice_ticks(axe, config)
    plt.gca().set_xlabel("Day")
    print_fig(chart_num)

    # CHART: LP PNL
    chart_num += 1
    fig, axe = plt.subplots(3, 1, sharex=False, gridspec_kw={"wspace": 0.3, "hspace": 0.2}, figsize=(6, 15))
    # subplot one
    axe[0].plot(
        trades_agg.loc[start_idx:end_idx_agg, "day"],
        trader_data,
        label=f"mean = {trades_agg.loc[end_idx_agg,'agent_0_pnl_no_mock_mean']:.3f}",
    )
    nice_ticks(axe[0], config)
    set_labels(axe=axe[0], title="LP PNL Over Time", xlabel="Day", ylabel="PnL in millions")
    # subplot two
    axe[1].bar(
        trades_agg.loc[start_idx:end_idx_agg, "day"],
        trades_agg.loc[start_idx:end_idx_agg, "delta_base_abs_sum"] / 1000,
        label=f"mean = {trades_agg.loc[start_idx:end_idx_agg,'delta_base_abs_sum'].mean():,.0f}",
    )
    axe[1].legend(loc="best")
    nice_ticks(axe[1], config)
    set_labels(axe=axe[1], title="Market Volume", xlabel="Day", ylabel="Base in thousands")
    # subplot three
    axe[2].bar(
        trades_agg.loc[start_idx:end_idx_agg, "day"],
        trades_agg.loc[start_idx:end_idx_agg, "delta_base_abs_count"],
        label=f"mean = {trades_agg.loc[start_idx:end_idx,'delta_base_abs_count'].mean():,.1f}",
    )
    axe[2].legend(loc="best")
    nice_ticks(axe[2], config)
    set_labels(axe=axe[2], title="# of trades", xlabel="Day", ylabel="# of trades")
    print_fig(chart_num)
    return chart_num


def experiment(start_chart_num=1, trade_fee_percent=0.1, redemption_fee_percent=0.005, trades_per_period=2) -> int:
    """
    run the defined simulation as an experiment with specified input parameters
    """
    start_time = time.time()
    config = Config()
    # config.init_lp = False
    config.random_seed = 123
    config.base_asset_price = 1

    config.log_filename = "../../.logging/vault_tracker.log"  # Output filename for logging

    config.log_level = (
        "DEBUG"  # Logging level, should be in ["DEBUG", "INFO", "WARNING"]. ERROR to suppress all logging.
    )
    config.pricing_model_name = "Hyperdrive"  # can be yieldspace or hyperdrive

    config.num_trading_days = 365  # Number of simulated trading days, default is 180
    config.num_position_days = config.num_trading_days  # term length
    config.num_blocks_per_day = 1  # 7200 # Blocks in a given day (7200 means ~12 sec per block)
    config.trade_fee_percent = trade_fee_percent  # 0.10 # fee percent collected on trades
    config.redemption_fee_percent = redemption_fee_percent  # 5 bps

    trade_chance = trades_per_period / (
        config.num_trading_days * config.num_blocks_per_day
    )  # on a given block, an agent will trade with probability `trade_chance`

    config.target_pool_apr = 0.05  # 5 # target pool APR of the initial market after the LP
    config.target_liquidity = 5_000_000  # target total liquidity of the initial market, before any trades

    vault_apr_init = 0.05  # Initial vault APR
    vault_apr_jump_size = 0.002  # Scale of the vault APR change (vault_apr (+/-)= jump_size)
    vault_jumps_per_year = 100  # 4 # The average number of jumps per year
    vault_apr_jump_direction = "random_weighted"  # The direction of a rate change. Can be 'up', 'down', or 'random'.
    vault_apr_lower_bound = 0.01  # minimum allowable vault apr
    vault_apr_upper_bound = 0.09  # maximum allowable vault apr

    # config.vault_apr = DSR_historical(num_dates=config.num_trading_days)
    config.vault_apr = poisson_vault_apr(
        rng=config.rng,
        num_trading_days=config.num_trading_days,
        initial_apr=vault_apr_init,
        jump_size=vault_apr_jump_size,
        vault_jumps_per_year=vault_jumps_per_year,
        direction=vault_apr_jump_direction,
        lower_bound=vault_apr_lower_bound,
        upper_bound=vault_apr_upper_bound,
    )

    output_utils.setup_logging(
        log_filename=config.log_filename,
        log_level=output_utils.text_to_log_level(config.log_level),
    )

    simulator = sim_utils.get_simulator(config)
    simulator.collect_and_execute_trades()

    num_agents = 100  # int specifying how many agents you want to simulate
    agent_budget = int(9.65 * 1e6 / num_agents)

    # add a bunch of regular guys
    short_agents = get_example_agents(
        rng=simulator.rng,
        budget=agent_budget,
        new_agents=num_agents / 2,
        existing_agents=1,
        direction="short",
        trade_chance=trade_chance,
    )
    long_agents = get_example_agents(
        rng=simulator.rng,
        budget=agent_budget,
        new_agents=num_agents / 2,
        existing_agents=1 + num_agents / 2,
        direction="long",
        trade_chance=trade_chance,
    )
    simulator.add_agents(short_agents + long_agents)
    # add a singular regular guy
    # regular_guy = get_example_agents(rng=simulator.rng, budget=9.65*1e6, new_agents=1, existing_agents=1, trade_chance=1)
    # simulator.add_agents(regular_guy)
    print(f"Simulator has {len(simulator.agents)} agents")
    for idx, agent in enumerate(short_agents):
        if idx in [0, num_agents / 2 - 1]:
            print(f"Agent #{agent.wallet.address} is a short: {agent.trade_short=} {agent.trade_long=}")  # type: ignore
    for idx, agent in enumerate(long_agents):
        if idx in [0, num_agents / 2 - 1]:
            print(f"Agent #{agent.wallet.address} is a long: {agent.trade_short=} {agent.trade_long=}")  # type: ignore

    simulator.run_simulation()
    print(f"simulation finished in {time.time()-start_time:0.2f}s")
    start_time = time.time()
    trades, trades_agg, pnl = post_process(simulator)
    print(f"post-processing finished in {time.time()-start_time:0.2f}s")
    start_time = time.time()
    last_chart = plot_and_save_results(
        config=config, trades=trades, trades_agg=trades_agg, pnl=pnl, start_chart_num=start_chart_num
    )
    print(f"plot_and_save_results() ran in {time.time()-start_time:0.2f}s")
    return last_chart


# create narrative
NARRATIVE = "with 10% trade and 0.05% redemption fees, LPs are <b>TOO DAMN PROFITABLE!!@#</b>"
last_chart_num = experiment(trade_fee_percent=0.1, redemption_fee_percent=0.005)
WEBPAGE = NARRATIVE + "<br><br>" + "<br>".join([f'<img src="chart{num}.svg">' for num in range(1, last_chart_num + 2)])

# create webpage
with open("index.html", mode="w", encoding="utf-8") as file:
    file.write("<html><body><center>" + WEBPAGE)

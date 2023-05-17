# %% [markdown]
# <a href="https://colab.research.google.com/github/element-fi/elf-simulations/blob/dp_mart_agents/examples/notebooks/fred_louie_simulation.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

# %% [markdown]
# ## Hyperdrive [NAME] simulation
# We use the following setup:
# - TBD
# * variable rate:
#     * step function
#     * rate changes every 3 months
#     * 
# 
# For details on the simulation framework, please see our <a href="https://elfpy.element.fi/">simulation documentation</a>

# %% [markdown]
# ### Install repo requirements & import packages

# %%
# test: skip-cell
try: # install dependencies only if running on google colab
    import google.colab # check if running in colab
    !pip install -r https://raw.githubusercontent.com/element-fi/elf-simulations/main/requirements-3.8.txt 
    !pip install git+https://github.com/element-fi/elf-simulations.git
except:
    print("running locally & trusting that you have the dependencies installed")

# %%
from __future__ import annotations
from dataclasses import dataclass, field

import pandas as pd
import numpy as np
from numpy.random._generator import Generator

from elfpy.agents.agent import Agent
from elfpy.simulators import Config

import elfpy.utils.outputs as output_utils
from elfpy.time import BlockTime
import elfpy.types as types

import elfpy.markets.borrow as borrow
import elfpy.agents.wallet as wallet

# %%
class BorrowingBeatrice(Agent):
    """
    Agent that paints & opens fixed rate borrow positions
    """

    def __init__(self, rng: Generator, trade_chance: float, risk_threshold: float, wallet_address: int, budget: int = 10_000) -> None:
        """Add custom stuff then call basic policy init"""
        self.trade_chance = trade_chance
        self.risk_threshold = risk_threshold
        self.rng = rng
        super().__init__(wallet_address, budget)

    def action(self, market: borrow.Market) -> list[types.Trade]:
        """Implement a Borrowing Beatrice user strategy

        I take out loans when the interest rate is below a threshold

        I close them after 2 months

        Parameters
        ----------
        market : Market
            the trading market

        Returns
        -------
        action_list : list[MarketAction]
        """
        # Any trading at all is based on a weighted coin flip -- they have a trade_chance% chance of executing a trade
        action_list = []
        gonna_trade = self.rng.choice([True, False], p=[self.trade_chance, 1-self.trade_chance])
        if not gonna_trade:
            return action_list
        
        has_borrow = self.wallet.borrows
        want_to_borrow = market.borrow_rate <= self.risk_threshold
        #print(f"{self.wallet.borrows=}")
        #print(f"{has_borrow=}")
        #print(f"{market.borrow_rate=}\t{self.risk_threshold}")
        #print(f"{want_to_borrow=}")
        if want_to_borrow and not has_borrow:
            action_list = [
                types.Trade(
                    market=types.MarketType.BORROW,
                    trade=borrow.MarketAction(
                        action_type=borrow.MarketActionType.OPEN_BORROW,
                        wallet=self.wallet,
                        collateral=types.Quantity(amount=self.budget, unit=types.TokenType.BASE),
                        spot_price=1, # usdc # FIXME: Doesn't look like this is uesd?
                    ),
                )
            ]
        
        if has_borrow:
            action_list = [
                types.Trade(
                    market=types.MarketType.BORROW,
                    trade=borrow.MarketAction(
                        action_type=borrow.MarketActionType.CLOSE_BORROW,
                        wallet=self.wallet,
                        collateral=types.Quantity(amount=self.budget, unit=types.TokenType.BASE),
                        spot_price=1, # usdc
                    ),
                )
            ]

        return action_list

# %% [markdown]
# ### Setup experiment parameters

# %%
config = Config()

# General config parameters
config.title = "Spark smart agent demo"
config.pricing_model_name = "Spark"

config.num_trading_days = 20#1095 # Number of simulated trading days
config.num_blocks_per_day = 5#7200 # Blocks in a given day (7200 means ~12 sec per block)
config.num_position_days = 10#90 # How long a token reaches maturity

config.curve_fee_multiple = 0.05 # fee multiple applied to price discount (1-p) collected on trades
config.flat_fee_multiple = 0.05 # fee collected on the spread of the flat portion

config.target_fixed_apr = 0.01 # target fixed APR of the initial market after the LP
config.target_liquidity = 500_000_000 # target total liquidity of the initial market, before any trades

config.log_level = output_utils.text_to_log_level("INFO") # Logging level, should be in ["DEBUG", "INFO", "WARNING"]
config.log_filename = "borrowing_beatrice" # Output filename for logging

config.shuffle_users = True

# Notebook specific parameters
num_bea = 15
trade_chance = 0.1 # on a given block, an agent will trade with probability `trade_chance`

bea_budget_mean = 500_000
bea_budget_std = 1_000
bea_budget_max = 1_00_000
bea_budget_min = 1_000

# Define the vault apr
vault_apr = np.array([0.01]*config.num_trading_days)
#vault_apr[config.num_trading_days//2:] = 0.05
config.variable_apr = vault_apr.tolist()
config.freeze()

fig_size = (5, 5)

# %% [markdown]
# ### Setup agents

# %% [markdown]
# ### Setup simulation objects

# %%
# define root logging parameters
output_utils.setup_logging(log_filename=config.log_filename, log_level=config.log_level)

# %%
market_state = borrow.MarketState(
    loan_to_value_ratio = {types.TokenType.BASE: 0.97},
    borrow_shares=0,
    collateral={types.TokenType.BASE: 0},
    borrow_outstanding=0,
    borrow_share_price=1,
    borrow_closed_interest=0,
    collateral_spot_price={types.TokenType.BASE: 1},
    lending_rate=0.01,
    spread_ratio=1.25
)
market = borrow.Market(pricing_model=borrow.PricingModel(), market_state=market_state, block_time=BlockTime())

agents = {
    0: BorrowingBeatrice(
        rng=config.rng,
        trade_chance=0.1,
        risk_threshold=0.02,
        wallet_address=1,
        budget=10_000,
    )
}

@dataclass
class BorrowSimState:
    day: list[int] = field(default_factory=list)
    block: list[int] = field(default_factory=list)
    borrows: list[dict[float, wallet.Borrow]] = field(default_factory=list)

    def add_dict_entries(self, dictionary: dict) -> None:
        for key, val in dictionary.items():
            if key in ["frozen", "no_new_attribs"]:
                continue
            if hasattr(self, key):
                attribute_state = getattr(self, key)
                attribute_state.append(val)
                setattr(self, key, attribute_state)
            else:
                setattr(self, key, [val])

simulation_state = BorrowSimState()

# %%
block_number = 0
for day in range(config.num_trading_days):
    #print(day)
    for _ in range(config.num_blocks_per_day):
        #print(block_number)
        agent_ids = [key for key in agents]
        agents_and_trades: "list[tuple[int, types.Trade]]" = []
        for agent_id in agent_ids:
            agent = agents[agent_id]
            trades = agent.get_trades(market)
            agents_and_trades.extend((agent_id, trade) for trade in trades)
        for trade in agents_and_trades:
            action_details = (trade[0], trade[1].trade)
            agent_id, agent_deltas, market_deltas = market.perform_action(action_details)
            #print(f"{agent_deltas=}")
            #market.update_market(market_deltas)
            #agents[agent_id].wallet.update(agent_deltas)
            simulation_state.day.append(day)
            simulation_state.block.append(block_number)
            agent_summary = agent_deltas.__dict__
            agent_summary["agent_id"] = agent_id
            simulation_state.add_dict_entries(agent_summary)
            simulation_state.add_dict_entries(market_deltas.__dict__)
            simulation_state.add_dict_entries({"config."+key: val for key, val in config.__dict__.items()})
            simulation_state.add_dict_entries(market.market_state.__dict__)
        block_number += 1

# %%
df = pd.DataFrame.from_dict(simulation_state.__dict__)
display(df)

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
"""Simulation for the Hyperdrive Borrow market"""
from __future__ import annotations

# pylint: disable=line-too-long
# pylint: disable=too-many-lines
# pylint: disable=too-many-arguments
# pylint: disable=invalid-name
# pylint: disable=redefined-outer-name
# pyright: reportOptionalMemberAccess=false, reportGeneralTypeIssues=false

# %% [markdown]
# ## Hyperdrive Borrow market simulation
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
try:  # install dependencies only if running on google colab
    # check if running in Google Colaboratory
    eval("import google.colab")  # pylint: disable=eval-used
    import os

    os.system(
        "!pip install git+https://github.com/delvtech/elf-simulations.git@4536bb486b7ce857840996448dbb479adb1c5c14"
    )
except:  # pylint: disable=bare-except
    print("running locally & trusting that you have the dependencies installed")

# %%
from dataclasses import dataclass, field

import numpy as np
from numpy.random._generator import Generator as NumpyGenerator
import pandas as pd

import elfpy.agents.wallet as wallet
import elfpy.time as elf_time
import elfpy.types as types
import elfpy.utils.outputs as output_utils

from elfpy.agents.agent import Agent
from elfpy.agents.policies.base import BasePolicy
from elfpy.agents.wallet import Wallet
from elfpy.markets.borrow.borrow_market import (
    Market,
    BorrowMarketAction,
    MarketActionType,
)
from elfpy.markets.borrow.borrow_pricing_model import BorrowPricingModel
from elfpy.markets.borrow.borrow_market_state import BorrowMarketState
from elfpy.math.fixed_point import FixedPoint
from elfpy.simulators.config import Config

# pylint: disable=too-few-public-methods


# %%
class BorrowingBeatrice(BasePolicy):
    """
    Agent that paints & opens fixed rate borrow positions
    """

    def __init__(
        self,
        budget: FixedPoint = FixedPoint("10_000.0"),
        rng: NumpyGenerator | None = None,
        trade_chance: FixedPoint = FixedPoint("1.0"),
        risk_threshold: FixedPoint = FixedPoint("0.0"),
    ) -> None:
        """Add custom stuff then call basic policy init"""
        self.trade_chance = trade_chance
        self.risk_threshold = risk_threshold
        super().__init__(budget, rng)

    def action(self, market: Market, wallet: Wallet) -> list[types.Trade]:
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
        gonna_trade = self.rng.choice([True, False], p=[float(self.trade_chance), 1 - float(self.trade_chance)])
        if not gonna_trade:
            return action_list
        has_borrow = wallet.borrows
        want_to_borrow = market.borrow_rate <= self.risk_threshold
        if want_to_borrow and not has_borrow:
            action_list = [
                types.Trade(
                    market=types.MarketType.BORROW,
                    trade=BorrowMarketAction(
                        action_type=MarketActionType.OPEN_BORROW,
                        wallet=wallet,
                        collateral=types.Quantity(amount=self.budget, unit=types.TokenType.BASE),
                        spot_price=1,
                    ),
                )
            ]
        if has_borrow:
            action_list = [
                types.Trade(
                    market=types.MarketType.BORROW,
                    trade=BorrowMarketAction(
                        action_type=MarketActionType.CLOSE_BORROW,
                        wallet=wallet,
                        collateral=types.Quantity(amount=self.budget, unit=types.TokenType.BASE),
                        spot_price=1,  # usdc
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

config.num_trading_days = 20  # 1095 # Number of simulated trading days
config.num_blocks_per_day = 5  # 7200 # Blocks in a given day (7200 means ~12 sec per block)
config.num_position_days = 10  # 90 # How long a token reaches maturity

config.curve_fee_multiple = 0.05  # fee multiple applied to price discount (1-p) collected on trades
config.flat_fee_multiple = 0.05  # fee collected on the spread of the flat portion

config.target_fixed_apr = 0.01  # target fixed APR of the initial market after the LP
config.target_liquidity = 500_000_000  # target total liquidity of the initial market, before any trades

config.log_level = output_utils.text_to_log_level("INFO")  # Logging level, should be in ["DEBUG", "INFO", "WARNING"]
config.log_filename = "borrowing_beatrice"  # Output filename for logging

config.shuffle_users = True

# Notebook specific parameters
num_bea = 15
trade_chance = 0.1  # on a given block, an agent will trade with probability `trade_chance`

bea_budget_mean = 500_000
bea_budget_std = 1_000
bea_budget_max = 1_00_000
bea_budget_min = 1_000

# Define the vault apr
vault_apr = np.array([0.01] * config.num_trading_days)
# vault_apr[config.num_trading_days//2:] = 0.05
config.variable_apr = vault_apr.tolist()
config.freeze()

fig_size = (5, 5)

# %%
# define root logging parameters
output_utils.setup_logging(log_filename=config.log_filename, log_level=config.log_level)

# %%
market_state = BorrowMarketState(
    loan_to_value_ratio={types.TokenType.BASE: FixedPoint("0.97")},
    borrow_shares=FixedPoint(0),
    collateral={types.TokenType.BASE: FixedPoint(0)},
    borrow_outstanding=FixedPoint(0),
    borrow_share_price=FixedPoint("1.0"),
    borrow_closed_interest=FixedPoint(0),
    collateral_spot_price={types.TokenType.BASE: FixedPoint("1.0")},
    lending_rate=FixedPoint("0.01"),
    spread_ratio=FixedPoint("1.25"),
)
market = Market(pricing_model=BorrowPricingModel(), market_state=market_state, block_time=elf_time.BlockTime())

agents = {
    0: Agent(
        wallet_address=1,
        policy=BorrowingBeatrice(
            budget=FixedPoint("10_000.0"),
            rng=config.rng,
            trade_chance=FixedPoint(trade_chance),
            risk_threshold=FixedPoint("0.02"),
        ),
    )
}


@dataclass
class BorrowSimState:
    """Sim state for borrow markets"""

    day: list[int] = field(default_factory=list)
    block: list[int] = field(default_factory=list)
    borrows: list[dict[FixedPoint, wallet.Borrow]] = field(default_factory=list)

    def add_dict_entries(self, dictionary: dict) -> None:
        """Add dict entries to the sim state"""
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
    for _ in range(config.num_blocks_per_day):
        agent_ids = list(agents)
        agents_and_trades: "list[tuple[int, types.Trade]]" = []
        for agent_id in agent_ids:
            agent = agents[agent_id]
            trades = agent.get_trades(market)
            agents_and_trades.extend((agent_id, trade) for trade in trades)
        for trade in agents_and_trades:
            action_details = (trade[0], trade[1].trade)
            agent_id, agent_deltas, market_deltas = market.perform_action(action_details)
            market.update_market(market_deltas)
            agents[agent_id].wallet.update(agent_deltas)
            simulation_state.day.append(day)
            simulation_state.block.append(block_number)
            agent_summary = agent_deltas.__dict__
            agent_summary["agent_id"] = agent_id
            simulation_state.add_dict_entries(agent_summary)
            simulation_state.add_dict_entries(market_deltas.__dict__)
            simulation_state.add_dict_entries({"config." + key: val for key, val in config.__dict__.items()})
            simulation_state.add_dict_entries(market.market_state.__dict__)
        block_number += 1

# %%
df = pd.DataFrame.from_dict(simulation_state.__dict__)
print(df)

# %%

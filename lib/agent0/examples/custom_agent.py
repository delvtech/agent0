"""Script to showcase setting up and running custom agents"""
# %%
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from agent0 import initialize_accounts
from agent0.base import Trade
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import setup_and_run_agent_loop
from agent0.hyperdrive.policies import HyperdrivePolicy
from agent0.hyperdrive.state import HyperdriveMarketAction

if TYPE_CHECKING:
    from ethpy.hyperdrive.interface import HyperdriveReadInterface

    from agent0.hyperdrive.state import HyperdriveWallet

# %%
# Define the unique agent env filename to use for this script
ENV_FILE = "custom_agent.account.env"
# Username binding for bots
USERNAME = "changeme"
# The amount of base token each bot receives
BASE_BUDGET_PER_BOT = FixedPoint(50).scaled_value  # 50 base in wei
ETH_BUDGET_PER_BOT = FixedPoint(1).scaled_value  # 1 eth in wei
# The slippage tolerance for trades
SLIPPAGE_TOLERANCE = FixedPoint("0.0001")  # 0.1% slippage
# Run this file with this flag set to true to close out all open positions
LIQUIDATE = False


# %%
# Build custom policy
# Simple agent, opens a set of all trades for a fixed amount and closes them after
# TODO this bot is almost identical to the one defined in test_fixtures for system tests
# On one hand, this bot is nice for an example since it shows all trades
# On the other, duplicated code between the two bots
class CustomCycleTradesPolicy(HyperdrivePolicy):
    """An agent that simply cycles through all trades"""

    @dataclass(kw_only=True)
    class Config(HyperdrivePolicy.Config):
        """Custom config arguments for this policy

        Attributes
        ----------
        static_trade_amount_wei: int
            The probability of this bot to make a trade on an action call
        """

        # Add additional parameters for custom policy here
        # Setting defaults for this parameter here
        static_trade_amount_wei: int = FixedPoint(100).scaled_value  # 100 base

    # Using default parameters
    def __init__(self, policy_config: Config):
        self.static_trade_amount_wei = policy_config.static_trade_amount_wei
        # We want to do a sequence of trades one at a time, so we keep an internal counter based on
        # how many times `action` has been called.
        self.counter = 0
        super().__init__(policy_config)

    def action(
        self, interface: HyperdriveReadInterface, wallet: HyperdriveWallet
    ) -> tuple[list[Trade[HyperdriveMarketAction]], bool]:
        """This agent simply opens all trades for a fixed amount and closes them after, one at a time

        Arguments
        ---------
        interface: HyperdriveReadInterface
            The trading market.
        wallet: HyperdriveWallet
            agent's wallet

        Returns
        -------
        tuple[list[MarketAction], bool]
            A tuple where the first element is a list of actions,
            and the second element defines if the agent is done trading
        """
        # pylint: disable=unused-argument
        action_list = []
        if self.counter == 0:
            # Add liquidity
            action_list.append(
                interface.add_liquidity_trade(trade_amount=FixedPoint(scaled_value=self.static_trade_amount_wei))
            )
        elif self.counter == 1:
            # Open Long
            action_list.append(
                interface.open_long_trade(
                    FixedPoint(scaled_value=self.static_trade_amount_wei), self.slippage_tolerance
                )
            )
        elif self.counter == 2:
            # Open Short
            action_list.append(
                interface.open_short_trade(
                    FixedPoint(scaled_value=self.static_trade_amount_wei), self.slippage_tolerance
                )
            )
        elif self.counter == 3:
            # Remove All Liquidity
            action_list.append(interface.remove_liquidity_trade(wallet.lp_tokens))
        elif self.counter == 4:
            # Close All Longs
            assert len(wallet.longs) == 1
            for long_time, long in wallet.longs.items():
                action_list.append(interface.close_long_trade(long.balance, long_time, self.slippage_tolerance))
        elif self.counter == 5:
            # Close All Shorts
            assert len(wallet.shorts) == 1
            for short_time, short in wallet.shorts.items():
                action_list.append(interface.close_short_trade(short.balance, short_time, self.slippage_tolerance))
        elif self.counter == 6:
            # Redeem all withdrawal shares
            action_list.append(interface.redeem_withdraw_shares_trade(wallet.withdraw_shares))

        self.counter += 1
        return action_list, False


# %%
# Build environment config
env_config = EnvironmentConfig(
    delete_previous_logs=False,
    halt_on_errors=False,
    log_filename=".logging/agent0_logs.logs",
    log_level=logging.CRITICAL,
    log_stdout=True,
    global_random_seed=1234,
    username=USERNAME,
)

# Build agent config
agent_config: list[AgentConfig] = [
    AgentConfig(
        policy=CustomCycleTradesPolicy,
        number_of_agents=1,
        base_budget_wei=BASE_BUDGET_PER_BOT,
        eth_budget_wei=ETH_BUDGET_PER_BOT,
        policy_config=CustomCycleTradesPolicy.Config(
            slippage_tolerance=SLIPPAGE_TOLERANCE,
            static_trade_amount_wei=FixedPoint(100).scaled_value,  # 100 base static trades
        ),
    ),
]
# %%

# Build accounts env var
# This function writes a user defined env file location.
# If it doesn't exist, create it based on agent_config
# (If os.environ["DEVELOP"] is False, will clean exit and print instructions on how to fund agent)
# If it does exist, read it in and use it
account_key_config = initialize_accounts(agent_config, ENV_FILE, random_seed=env_config.global_random_seed)

# Run agents
setup_and_run_agent_loop(env_config, agent_config, account_key_config, liquidate=LIQUIDATE)

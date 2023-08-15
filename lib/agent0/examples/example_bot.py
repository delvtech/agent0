"""Script to showcase setting up and running custom bots"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agent0 import initialize_accounts
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import run_bots
from agent0.hyperdrive.policies import HyperdrivePolicy
from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction
from elfpy.types import MarketType, Trade
from fixedpointmath import FixedPoint

if TYPE_CHECKING:
    from agent0.hyperdrive.agents import HyperdriveWallet
    from elfpy.markets.hyperdrive import HyperdriveMarket as HyperdriveMarketState
    from numpy.random._generator import Generator as NumpyGenerator

DEVELOP = False


# Build custom policy
# Simple bot, opens a set of all trades for a fixed amount and closes them after
class CycleTradesPolicy(HyperdrivePolicy):
    """A bot that simply cycles through all trades"""

    # Using default parameters
    def __init__(
        self,
        budget: FixedPoint,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        # Add additional parameters for custom policy here
        static_trade_amount: FixedPoint = FixedPoint("100"),
    ):
        self.static_trade_amount = static_trade_amount
        # We want to do a sequence of trades one at a time, so we keep an internal counter based on
        # how many times `action` has been called.
        self.counter = 0
        super().__init__(budget, rng, slippage_tolerance)

    def action(self, market: HyperdriveMarketState, wallet: HyperdriveWallet) -> list[Trade[HyperdriveMarketAction]]:
        """This bot simply opens all trades for a fixed amount and closes them after, one at a time"""
        action_list = []
        if self.counter == 0:
            # Add liquidity
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.ADD_LIQUIDITY,
                        trade_amount=self.static_trade_amount,
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 1:
            # Open Long
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_LONG,
                        trade_amount=self.static_trade_amount,
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 2:
            # Open Short
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_SHORT,
                        trade_amount=self.static_trade_amount,
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 3:
            # Remove All Liquidity
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.REMOVE_LIQUIDITY,
                        trade_amount=wallet.lp_tokens,
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 4:
            # Close All Longs
            assert len(wallet.longs) == 1
            for long_time, long in wallet.longs.items():
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_LONG,
                            trade_amount=long.balance,
                            wallet=wallet,
                            # TODO is this actually maturity time? Not mint time?
                            mint_time=long_time,
                        ),
                    )
                )
        elif self.counter == 4:
            # Close All Shorts
            assert len(wallet.shorts) == 1
            for short_time, short in wallet.shorts.items():
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=HyperdriveActionType.CLOSE_SHORT,
                            trade_amount=short.balance,
                            wallet=wallet,
                            # TODO is this actually maturity time? Not mint time?
                            mint_time=short_time,
                        ),
                    )
                )
        elif self.counter == 5:
            # Redeem all withdrawal shares
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.REDEEM_WITHDRAW_SHARE,
                        trade_amount=wallet.withdraw_shares,
                        wallet=wallet,
                    ),
                )
            )
        elif self.counter == 6:
            # One more dummy trade to ensure the previous trades get into the db
            # TODO test if we can remove this eventually
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=HyperdriveActionType.OPEN_LONG,
                        trade_amount=self.static_trade_amount,
                        wallet=wallet,
                    ),
                )
            )

        self.counter += 1
        return action_list


# Build environment config
env_config = EnvironmentConfig(
    delete_previous_logs=False,
    halt_on_errors=True,
    log_filename="agent0-bots",
    log_level=logging.INFO,
    log_stdout=True,
    random_seed=1234,
    username="tmp",
)

# Build agent config
agent_config: list[AgentConfig] = [
    AgentConfig(
        policy=CycleTradesPolicy,
        number_of_agents=1,
        slippage_tolerance=FixedPoint(0.0001),
        base_budget=FixedPoint(10000),
        eth_budget=FixedPoint(10),
        init_kwargs={"static_trade_amount": FixedPoint(100)},
    ),
]

# Build accounts env var
# TODO this function writes a user defined env file location.
# If it doesn't exist, create it based on agent_config
# If it does exist, read it in and use it
account_key_config = initialize_accounts(agent_config, random_seed=env_config.random_seed, develop=DEVELOP)

# Run the bot
# (if develop is off, print instructions on adding in user private key and running script to fund bots and exit).
# Note during the trading competition, running the bots will fail until you fund the bot via script
# The script takes in as a parameter the env file, and funds the bots from the user key
run_bots(env_config, agent_config, account_key_config, develop=DEVELOP)

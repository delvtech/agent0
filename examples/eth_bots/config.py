"""Experiment configuration"""
from __future__ import annotations

import logging

from elfpy.agents.policies import Policies
from elfpy.bots import BotInfo, Budget, EnvironmentConfig

agent_config: list[BotInfo] = [
    BotInfo(
        policy=Policies.RANDOM_AGENT,
        number_of_bots=3,
        budget=Budget(
            mean_wei=int(1e18),  # 1 ETH
            std_wei=int(1e17),  # 0.1 ETH
            min_wei=1,  # 1 WEI
            max_wei=int(1e21),  # 1k ETH
        ),
        init_kwargs={"trade_chance": 0.8},
    ),
    BotInfo(
        policy=Policies.LONG_LOUIE,
        number_of_bots=5,
        budget=Budget(
            mean_wei=int(1e18),  # 1 ETH
            std_wei=int(1e17),  # 0.1 ETH
            min_wei=1,  # 1 WEI
            max_wei=int(1e21),  # 1k ETH
        ),
        init_kwargs={"trade_chance": 0.8, "risk_threshold": 0.9},
    ),
    BotInfo(
        policy=Policies.SHORT_SALLY,
        number_of_bots=2,
        budget=Budget(
            mean_wei=int(1e18),  # 1 ETH
            std_wei=int(1e17),  # 0.1 ETH
            min_wei=1,  # 1 WEI
            max_wei=int(1e21),  # 1k ETH
        ),
        init_kwargs={"trade_chance": 0.8, "risk_threshold": 0.8},
    ),
]

environment_config = EnvironmentConfig(
    alchemy=False,
    artifacts_url="http://localhost:80",
    delete_previous_logs=False,
    devnet=True,
    halt_on_errors=False,
    log_filename="agent0-bots",
    log_level=logging.INFO,
    log_stdout=True,
    rpc_url="http://localhost:8545",
    random_seed=1234,
    username="changeme",
)

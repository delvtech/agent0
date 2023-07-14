"""Experiment configuration"""
from __future__ import annotations

import logging

from elfpy.bots import BotConfig, BotInfo, Budget

DEFAULT_USERNAME = "changeme"

bot_config = BotConfig(
    alchemy=False,
    artifacts_url="http://localhost:80",
    agents=[
        BotInfo(
            policy="RandomAgent",
            number_of_bots=3,
            budget=Budget(
                mean_wei=int(1e18),  # 1 ETH
                std_wei=int(1e17),  # 0.1 ETH
                min_wei=1,  # 1 WEI
                max_wei=1e21,  # 1k ETH
            ),
            init_kwargs={"trade_chance": 0.8},
        ),
        BotInfo(
            policy="LongLouie",
            number_of_bots=5,
            budget=Budget(
                mean_wei=int(1e18),  # 1 ETH
                std_wei=int(1e17),  # 0.1 ETH
                min_wei=1,  # 1 WEI
                max_wei=1e21,  # 1k ETH
            ),
            init_kwargs={"trade_chance": 0.8, "risk_threshold": 0.9},
        ),
        BotInfo(
            policy="ShortSally",
            number_of_bots=2,
            budget=Budget(
                mean_wei=int(1e18),  # 1 ETH
                std_wei=int(1e17),  # 0.1 ETH
                min_wei=1,  # 1 WEI
                max_wei=1e21,  # 1k ETH
            ),
            init_kwargs={"trade_chance": 0.8, "risk_threshold": 0.8},
        ),
    ],
    delete_previous_logs=False,
    devnet=True,
    halt_on_errors=False,
    log_filename="agent0-bots",
    log_level=logging.INFO,
    log_file_and_stdout=True,
    rpc_url="http://localhost:8545",
    random_seed=1234,
    username=DEFAULT_USERNAME,
)

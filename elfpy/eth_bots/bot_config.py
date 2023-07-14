"""Experiment configuration"""
from __future__ import annotations

import logging

from elfpy.bots import BotConfig, BotInfo, Budget

DEFAULT_USERNAME = "changeme"

bot_config = BotConfig(
    alchemy=False,
    artifacts_url="http://localhost:80",
    bots=[
        BotInfo(
            policy="RandomAgent",
            budget=Budget(
                mean_wei=int(1e18),  # 1 ETH
                std_wei=int(1e17),  # 0.1 ETH
                min_wei=1,  # 1 WEI
                max_wei=1e21,  # 1k ETH
            ),
            trade_chance=0.8,
            number_of_bots=3,
        ),
        BotInfo(
            policy="LongLouie",
            budget=Budget(
                mean_wei=int(1e18),  # 1 ETH
                std_wei=int(1e17),  # 0.1 ETH
                min_wei=1,  # 1 WEI
                max_wei=1e21,  # 1k ETH
            ),
            trade_chance=0.8,
            number_of_bots=5,
            scratch={"risk_threshold": 0.8},
        ),
        BotInfo(
            policy="ShortSally",
            budget=Budget(
                mean_wei=int(1e18),  # 1 ETH
                std_wei=int(1e17),  # 0.1 ETH
                min_wei=1,  # 1 WEI
                max_wei=1e21,  # 1k ETH
            ),
            trade_chance=0.8,
            number_of_bots=2,
            scratch={"risk_threshold": 0.8},
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

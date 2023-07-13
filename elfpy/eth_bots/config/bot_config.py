"""Experiment configuration"""
from __future__ import annotations

import logging

from elfpy.bots import BotConfig, BotInfo, Budget

bot_config = BotConfig(
    alchemy=False,
    artifacts_url="http://localhost:80",
    devnet=True,
    halt_on_errors=False,
    log_filename="agent0-bots",
    log_level=logging.INFO,
    delete_previous_logs=False,
    log_file_and_stdout=True,
    rpc_url="http://localhost:8545",
    random_seed=1234,
    bots=[
        BotInfo(
            policy="RandomAgent",
            trade_chance=0.8,
            risk_threshold=0.3,
            budget=Budget
    ]
)

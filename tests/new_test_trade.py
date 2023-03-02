"""Testing for the ElfPy package modules"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest
import logging

import elfpy.utils.outputs as output_utils  # utilities for file outputs
import elfpy.utils.sim_utils as sim_utils
import elfpy.simulators.simulators as simulators
import elfpy.agents.wallet as wallet
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.markets.hyperdrive as hyperdrive_market
import elfpy.types as types


class TradeTests(unittest.TestCase):
    """Tests for executing trades from policies"""

    config: simulators.Config

    def setUp(self):
        """Create a config to be used throught the tests"""
        self.config = simulators.Config()
        self.config.target_liquidity = 10e6
        self.config.trade_fee_percent = 0.1
        self.config.redemption_fee_percent = 0.0
        self.config.target_fixed_apr = 0.05
        self.config.num_trading_days = 3
        self.config.num_blocks_per_day = 3
        self.config.variable_apr = [0.05] * self.config.num_trading_days

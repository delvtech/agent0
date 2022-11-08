"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init

import os
import unittest
import json
import numpy as np

from elfpy.simulators import YieldSimulator

class BaseTradeTest(unittest.TestCase):
    """Generic Trade Test class"""

    def run_base_trade_test(self, policy):
        """Assigns member variables that are useful for many tests"""
        # load default config
        random_seed = 3
        simulator_rng = np.random.default_rng(random_seed)
        config = {
            "min_fee": 0.1, # decimal that assigns fee_percent
            "max_fee": 0.5, # decimal that assigns fee_percent
            "min_target_liquidity": 1e6, # in USD
            "max_target_liquidity": 10e6, # in USD
            "min_target_volume": 0.001, # fraction of pool liquidity
            "max_target_volume": 0.01, # fration of pool liquidity
            "min_pool_apy": 0.02, # as a decimal
            "max_pool_apy": 0.9, # as a decimal
            "pool_apy_target_range": [0.15,0.20], # as a decimal
            "pool_apy_target_range_convergence_speed": 0.52, # as a share of trades that move in convergence direction
            "min_vault_age": 0, # fraction of a year
            "max_vault_age": 1, # fraction of a year
            "min_vault_apy": 0.001, # as a decimal
            "max_vault_apy": 0.9, # as a decimal
            "base_asset_price": 2.5e3, # aka market price
            "pool_duration": 180, # in days
            "num_trading_days": 180, # should be <= pool_duration
            "floor_fee": 0, # minimum fee percentage (bps)
            "tokens": ["base", "fyt"],
            "trade_direction": "out",
            "precision": None,
            "rng": simulator_rng,
            "verbose": False,
            "pricing_model_name": 'HyperDrive',
            "user_policies": [policy],
            "num_trading_days": 90,
            "token_duration": 90,
            "num_blocks_per_day": int(24*60*60/13)
        }

        simulator = YieldSimulator(**config)
        simulator.set_random_variables()
        simulator.setup_simulated_entities()
        simulator.run_simulation()

class SingleLongTradeTest(BaseTradeTest):
    """Tests for the SingeLong policy"""

    def test_base_user(self):
        """Tests the BaseUser class"""
        self.run_base_trade_test("single_long")

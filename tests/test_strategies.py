"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init

import os, sys
import unittest
import json
import numpy as np

from elfpy.simulators import YieldSimulator
# from elfpy.pricing_models import ElementPricingModel, HyperdrivePricingModel
# from elfpy.markets import Market
from elfpy.utils.parse_json import parse_trade

class BaseStrategyTest(unittest.TestCase):
    """Generic test class"""

    def setup_test_vars(self):
        """Assigns member variables that are useful for many tests"""
        # load default config
        random_seed = 3
        simulator_rng = np.random.default_rng(random_seed)
        self.config = {
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
            "pricing_model_name": 'YieldSpacev2',
            "user_type": "WeightedRandom",
        }
        self.rng = self.config["rng"]

        simulator = YieldSimulator(**self.config)
        simulator.set_random_variables()
        self.market = simulator.market

    def check_trade(self, trade_action, trade_spec):
        """Checks that the trade action is valid"""
        token_in, token_out, input_amount_in_usd = trade_action
        assert token_in in ['base', 'pt']
        assert token_out in ['base', 'pt']
        assert input_amount_in_usd >= 0, (
            f"user.py: ERROR: Input trade amount in USD should not be negative, but is {input_amount_in_usd}"
            f" token_in={token_in} token_out={token_out}"
        )

class TestBaseUser(BaseStrategyTest):
    """Tests for the BaseUser class"""

    def test_base_user(self):
        """Tests the BaseUser class"""
        from elfpy.user import User
        self.setup_test_vars()

        # assign directory
        directory = os.path.join(os.getcwd(), "src", "elfpy", "strategies")
        
        # iterate over strategy files
        for filename in os.scandir(directory):
            if filename.is_file():
                policy = json.load(open(filename.path))
                user = User(policy, self.rng)
                trade_action = user.get_trade(self.market)
                self.check_trade(trade_action, policy)

class TestStrategyDefinitions(BaseStrategyTest):
    """Tests for all strategies"""

    def test_strategy_definitions(self):
        """Test constructing each user type"""
        self.setup_test_vars()
              
        # assign directory
        directory = os.path.join(os.getcwd(), "src", "elfpy", "strategies")
        
        # iterate over strategy files
        for filename in os.scandir(directory):
            if filename.is_file():
                policy = json.load(open(filename.path))
                trade_spec = policy["trade"]
                trade_action = parse_trade(trade_spec, self.market, self.rng)
                self.check_trade(trade_action, trade_spec)
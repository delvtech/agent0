"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init

import os, sys
import unittest
import json

sys.path.insert(1, os.path.join(os.getcwd(), "src"))

from elfpy.simulators import YieldSimulator
# from elfpy.pricing_models import ElementPricingModel, HyperdrivePricingModel
# from elfpy.markets import Market
from elfpy.utils.parse_json import parse_trade

class BaseStrategyTest(unittest.TestCase):
    """Generic test class"""

    def setup_test_vars(self):
        """Assigns member variables that are useful for many tests"""
        import elfpy.utils.config as config
        # load default config
        self.config = config.load()
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
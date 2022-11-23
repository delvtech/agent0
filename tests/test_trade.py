"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init

import unittest
import numpy as np


from elfpy.simulators import YieldSimulator
from elfpy.utils.parse_config import parse_simulation_config


class BaseTradeTest(unittest.TestCase):
    """Generic Trade Test class"""

    def run_base_trade_test(self, policy, additional_overrides=None):
        """Assigns member variables that are useful for many tests"""
        # load default config
        config_file = "./config/simulation_config.toml"
        simulator = YieldSimulator(parse_simulation_config(config_file))
        simulator_rng = np.random.default_rng(simulator.config.simulator.random_seed)
        simulator.reset_rng(simulator_rng)
        simulator.set_random_variables()
        override_dict = {
            "pricing_model_name": "HyperDrive",
            "target_liquidity": 10e6,
            "fee_percent": 0.1,
            "init_pool_apy": 0.05,
            "user_policies": [policy],
        }
        if additional_overrides:
            override_dict.update(additional_overrides)
        simulator.run_simulation(override_dict)


class SingleTradeTests(BaseTradeTest):
    """Tests for the SingeLong policy"""

    def test_single_long(self):
        """Tests the BaseUser class"""
        self.run_base_trade_test("single_long")

    def test_single_short(self):
        """Tests the BaseUser class"""
        self.run_base_trade_test("single_short")

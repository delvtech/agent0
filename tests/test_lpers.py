"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init

import unittest
from elfpy.utils.fmt import *
from elfpy.simulators import YieldSimulator


class BaseLPTest(unittest.TestCase):
    """Generic Trade Test class"""

    def run_base_lp_test(self, user_policies, config_file, additional_overrides=None):
        """Assigns member variables that are useful for many tests"""
        simulator = YieldSimulator(config_file)
        simulator.set_random_variables()
        override_dict = {
            "target_liquidity": 10e6,
            "fee_percent": 0.1,  # a fraction which represents a percentage!
            "init_pool_apy": 0.05,
            "num_blocks_per_day": 1,  # 1 block a day, keep it fast for testing
            "user_policies": user_policies,  # list of user policies by name
        }
        if additional_overrides:
            override_dict.update(additional_overrides)
        simulator.run_simulation(override_dict)


class LPTests(BaseLPTest):
    """Tests for the Simple LP policy"""

    def test_base_LPs(self):
        """Tests base LP setups"""
        self.run_base_lp_test(user_policies=["simple_LP"],config_file="config/hyperdrive_config.toml")

    # def test_complicated_LPs(self):
        """Tests complicated LP setups"""
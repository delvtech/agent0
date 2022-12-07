"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init
# pylint: disable=duplicate-code

import unittest
import os
import logging

import numpy as np

from elfpy.utils.parse_config import load_and_parse_config_file
from elfpy.simulators import YieldSimulator


class BaseTradeTest(unittest.TestCase):
    """Generic Trade Test class"""

    @staticmethod
    def setup_logging():
        """Setup test logging levels and handlers"""
        logging_level = logging.DEBUG
        log_dir = ".logging"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        name = "test_trades.log"
        handler = logging.FileHandler(os.path.join(log_dir, name), "w")
        logging.getLogger().setLevel(logging_level)  # events of this level and above will be tracked
        handler.setFormatter(
            logging.Formatter(
                "\n%(asctime)s: %(levelname)s: %(module)s.%(funcName)s:\n%(message)s", "%y-%m-%d %H:%M:%S"
            )
        )
        logging.getLogger().handlers = [
            handler,
        ]

    def run_base_trade_test(self, user_policies, config_file, additional_overrides=None):
        """Assigns member variables that are useful for many tests"""
        self.setup_logging()
        # load default config
        config = load_and_parse_config_file(config_file)
        simulator = YieldSimulator(config)
        simulator_rng = np.random.default_rng(simulator.config.simulator.random_seed)
        simulator.reset_rng(simulator_rng)
        simulator.set_random_variables()
        override_dict = {
            "pricing_model_name": "HyperDrive",
            "target_liquidity": 10e6,
            "fee_percent": 0.1,
            "init_pool_apy": 0.05,
            "vault_apy": 0.05,
            "num_blocks_per_day": 1,  # 1 block a day, keep it fast for testing
            "user_policies": user_policies,
            "simulator.verbose": True,
        }
        if additional_overrides:
            override_dict.update(additional_overrides)
        simulator.setup_simulated_entities(override_dict)
        simulator.run_simulation()
        # comment this to view the generated log files
        file_loc = logging.getLogger().handlers[0].baseFilename
        os.remove(file_loc)

    def run_base_lp_test(self, user_policies, config_file, additional_overrides=None):
        """
        Assigns member variables that are useful for many tests
        TODO: Check that the market values match the desired amounts
        """
        self.setup_logging()
        config = load_and_parse_config_file(config_file)
        simulator = YieldSimulator(config)
        simulator.set_random_variables()
        target_liquidity = 10e6
        target_pool_apr = 0.05
        override_dict = {
            "pricing_model_name": "Hyperdrive",
            "target_liquidity": target_liquidity,
            "init_pool_apy": target_pool_apr,
            "vault_apy": 0.05,
            "fee_percent": 0.1,
            "num_blocks_per_day": 1,  # 1 block a day, keep it fast for testing
            "user_policies": user_policies,  # list of user policies by name
        }
        if additional_overrides:
            override_dict.update(additional_overrides)
        simulator.setup_simulated_entities(override_dict)
        total_liquidity = simulator.market.bond_reserves + simulator.market.share_reserves
        market_apr = simulator.market.get_rate()
        # check that apr is within a 0.1% of the target
        assert np.allclose(
            market_apr, target_pool_apr, atol=0.001
        ), f"test_trade.run_base_lp_test: ERROR: {target_pool_apr=} does not equal {market_apr=}"
        # check that the liquidity is within 5% of the target
        assert np.allclose(
            total_liquidity, target_liquidity, atol=target_liquidity * 0.05
        ), f"test_trade.run_base_lp_test: ERROR: {target_liquidity=} does not equal {total_liquidity=}"
        simulator.run_simulation()
        # comment this to view the generated log files
        file_loc = logging.getLogger().handlers[0].baseFilename
        os.remove(file_loc)


class SingleTradeTests(BaseTradeTest):
    """Tests for the SingeLong policy"""

    def test_init_only(self):
        """Tests base LP setups"""
        self.run_base_lp_test(user_policies=[], config_file="config/example_config.toml")

    def test_single_long(self):
        """Tests the BaseUser class"""
        self.run_base_trade_test(user_policies=["single_long"], config_file="config/example_config.toml")

    def test_single_short(self):
        """Tests the BaseUser class"""
        self.run_base_trade_test(user_policies=["single_short"], config_file="config/example_config.toml")

    def test_base_lps(self):
        """Tests base LP setups"""
        self.run_base_lp_test(user_policies=["single_lp"], config_file="config/example_config.toml")

if __name__ == "__main__":
    test = SingleTradeTests()
    test.test_init_only()

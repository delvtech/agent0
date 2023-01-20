"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init
# pylint: disable=duplicate-code

import unittest
import logging
from importlib import import_module

import numpy as np
from elfpy.markets import Market

from elfpy.simulators import Simulator
from elfpy.utils import sim_utils
import elfpy.utils.outputs as output_utils  # utilities for file outputs
import elfpy.utils.parse_config as config_utils


class BaseTradeTest(unittest.TestCase):
    """Generic Trade Test class"""

    @staticmethod
    def setup_simulation_entities(config_file, override_dict, agent_policies) -> Simulator:
        """Construct and run the simulator"""
        # Instantiate the agents.
        agents = []
        for agent_id, policy_name in enumerate(agent_policies):
            wallet_address = agent_id + 1  # addresses start at one because there is an initial agent.
            agent = import_module(f"elfpy.policies.{policy_name}").Policy(
                wallet_address=wallet_address,  # first policy goes to init_lp_agent
            )
            agent.log_status_report()
            agents += [agent]

        # Initialize the simulator.
        config = config_utils.override_config_variables(
            config_utils.load_and_parse_config_file(config_file), override_dict
        )
        rng = np.random.default_rng(config.simulator.random_seed)
        simulator = sim_utils.get_simulator(config, rng, agents)

        return simulator

    @staticmethod
    def setup_logging():
        """Setup test logging levels and handlers"""
        log_filename = ".logging/test_trades.log"
        log_level = logging.DEBUG
        output_utils.setup_logging(log_filename, log_level=log_level)

    def run_base_trade_test(self, agent_policies, config_file, delete_logs=True):
        """Assigns member variables that are useful for many tests"""
        self.setup_logging()
        # load default config
        override_dict = {
            "pricing_model_name": "Yieldspace",
            "target_liquidity": 10e6,
            "fee_percent": 0.1,
            "target_pool_apr": 0.05,
            "vault_apr": {"type": "constant", "value": 0.05},
            "num_trading_days": 3,  # sim 3 days to keep it fast for testing
            "num_blocks_per_day": 3,  # 3 block a day, keep it fast for testing
        }
        simulator = self.setup_simulation_entities(config_file, override_dict, agent_policies)
        simulator.run_simulation()
        if delete_logs:
            output_utils.delete_log_file()

    def run_base_lp_test(self, agent_policies, config_file, delete_logs=True):
        """
        Assigns member variables that are useful for many tests
        """
        self.setup_logging()
        target_liquidity = 1e6
        target_pool_apr = 0.05
        override_dict = {
            "pricing_model_name": "Yieldspace",
            "target_liquidity": target_liquidity,
            "target_pool_apr": target_pool_apr,
            "vault_apr": {"type": "constant", "value": 0.05},
            "fee_percent": 0.1,
            "num_trading_days": 3,  # sim 3 days to keep it fast for testing
            "num_blocks_per_day": 3,  # 3 blocks per day to keep it fast for testing
        }
        simulator = self.setup_simulation_entities(config_file, override_dict, agent_policies)
        # check that apr is within 0.005 of the target
        market_apr = simulator.market.rate
        assert np.allclose(market_apr, target_pool_apr, atol=0.005), (
            f"test_trade.run_base_lp_test: ERROR: {target_pool_apr=} does not equal {market_apr=}"
            f"with error of {(np.abs(market_apr - target_pool_apr)/target_pool_apr)=}"
        )
        # check that the liquidity is within 0.001 of the target
        # TODO: This will not work with Hyperdrive PM
        total_liquidity = simulator.market.market_state.share_reserves * simulator.market.market_state.share_price
        assert np.allclose(total_liquidity, target_liquidity, atol=0.001), (
            f"test_trade.run_base_lp_test: ERROR: {target_liquidity=} does not equal {total_liquidity=} "
            f"with error of {(np.abs(total_liquidity - target_liquidity)/target_liquidity)=}."
        )
        # run the simulation
        simulator.run_simulation()
        if delete_logs:
            output_utils.delete_log_file()


class SingleTradeTests(BaseTradeTest):
    """
    Tests for the SingeLong policy
    TODO: In a followup PR, loop over pricing model types & rerun tests
    """

    def test_init_only(self):
        """Tests base LP setups"""
        self.run_base_lp_test(agent_policies=[], config_file="config/example_config.toml")

    def test_single_long(self):
        """Tests the BaseUser class"""
        self.run_base_trade_test(agent_policies=["single_long"], config_file="config/example_config.toml")

    def test_single_short(self):
        """Tests the BaseUser class"""
        self.run_base_trade_test(agent_policies=["single_short"], config_file="config/example_config.toml")

    def test_base_lps(self):
        """Tests base LP setups"""
        self.run_base_lp_test(agent_policies=["single_lp"], config_file="config/example_config.toml")

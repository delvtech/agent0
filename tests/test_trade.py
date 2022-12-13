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
from importlib import import_module

import numpy as np

from elfpy.utils.parse_config import load_and_parse_config_file
from elfpy.simulators import Simulator
from elfpy.utils import sim_utils


class BaseTradeTest(unittest.TestCase):
    """Generic Trade Test class"""

    @staticmethod
    def setup_simulation_entities(config_file, override_dict, agent_policies):
        """Construct and run the simulator"""
        # create config object
        config = sim_utils.override_config_variables(load_and_parse_config_file(config_file), override_dict)
        # instantiate rng object
        rng = np.random.default_rng(config.simulator.random_seed)
        # run random number generators to get random simulation arguments
        random_sim_vars = sim_utils.override_random_variables(
            sim_utils.get_random_variables(config, rng), override_dict
        )
        # instantiate the pricing model
        pricing_model = sim_utils.get_pricing_model(model_name=config.amm.pricing_model_name)
        # instantiate the market
        market = sim_utils.get_market(
            pricing_model,
            random_sim_vars.init_pool_apy,
            random_sim_vars.fee_percent,
            config.simulator.token_duration,
            random_sim_vars.init_share_price,
        )
        # instantiate the init_lp agent
        init_agents = {
            0: sim_utils.get_init_lp_agent(
                config,
                market,
                pricing_model,
                random_sim_vars.target_liquidity,
                random_sim_vars.init_pool_apy,
                random_sim_vars.fee_percent,
            )
        }
        # set up simulator with only the init_lp_agent
        simulator = Simulator(
            config=config,
            pricing_model=pricing_model,
            market=market,
            agents=init_agents,
            rng=rng,
            random_simulation_variables=random_sim_vars,
        )
        # initialize the market using the LP agent
        simulator.collect_and_execute_trades()
        print(random_sim_vars.target_liquidity)
        print(random_sim_vars.init_pool_apy)
        print(simulator.market.get_rate(pricing_model))
        print(agent_policies)
        # get trading agent list
        for agent_id, policy_name in enumerate(agent_policies):
            wallet_address = len(init_agents) + agent_id
            agent = import_module(f"elfpy.policies.{policy_name}").Policy(
                wallet_address=wallet_address,  # first policy goes to init_lp_agent
            )
            agent.log_status_report()
            simulator.agents.update({agent.wallet_address: agent})
        return (simulator, market, pricing_model)

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

    def run_base_trade_test(self, agent_policies, config_file, delete_logs=True):
        """Assigns member variables that are useful for many tests"""
        self.setup_logging()
        # load default config
        override_dict = {
            "pricing_model_name": "HyperDrive",
            "target_liquidity": 10e6,
            "fee_percent": 0.1,
            "init_pool_apy": 0.05,
            "vault_apy": 0.05,
            "num_blocks_per_day": 1,  # 1 block a day, keep it fast for testing
        }
        config = sim_utils.override_config_variables(load_and_parse_config_file(config_file), override_dict)
        simulator = self.setup_simulation_entities(config, override_dict, agent_policies)[0]
        simulator.run_simulation()
        if delete_logs:
            file_loc = logging.getLogger().handlers[0].baseFilename
            os.remove(file_loc)

    def run_base_lp_test(self, agent_policies, config_file, delete_logs=True):
        """
        Assigns member variables that are useful for many tests
        TODO: Check that the market values match the desired amounts
        """
        self.setup_logging()
        target_liquidity = 10e6
        target_pool_apr = 0.05
        override_dict = {
            "pricing_model_name": "Hyperdrive",
            "target_liquidity": target_liquidity,
            "init_pool_apy": target_pool_apr,
            "vault_apy": 0.05,
            "fee_percent": 0.1,
            "num_trading_days": 3,  # sim 3 days to keep it fast for testing
            "num_blocks_per_day": 3,  # 3 blocks per day to keep it fast for testing
        }
        simulator, market, pricing_model = self.setup_simulation_entities(config_file, override_dict, agent_policies)
        total_liquidity = market.bond_reserves + market.share_reserves
        market_apr = market.get_rate(pricing_model)
        # check that apr is within a 0.1% of the target
        assert np.allclose(
            market_apr, target_pool_apr, atol=0.001
        ), f"test_trade.run_base_lp_test: ERROR: {target_pool_apr=} does not equal {market_apr=}"
        # check that the liquidity is within 7% of the target
        assert np.allclose(total_liquidity, target_liquidity, atol=target_liquidity * 0.07), (
            f"test_trade.run_base_lp_test: ERROR: {target_liquidity=} does not equal {total_liquidity=} "
            f"with error rate {(np.abs(total_liquidity-target_liquidity)/target_liquidity)=}."
        )
        # run the simulation
        simulator.run_simulation()
        if delete_logs:
            file_loc = logging.getLogger().handlers[0].baseFilename
            os.remove(file_loc)


class SingleTradeTests(BaseTradeTest):
    """Tests for the SingeLong policy"""

    def test_init_only(self):
        """Tests base LP setups"""
        self.run_base_lp_test(agent_policies=[], config_file="config/example_config.toml")

    # def test_single_long(self):
    #    """Tests the BaseUser class"""
    #    self.run_base_trade_test(agent_policies=["single_long"], config_file="config/example_config.toml")

    # def test_single_short(self):
    #    """Tests the BaseUser class"""
    #    self.run_base_trade_test(agent_policies=["single_short"], config_file="config/example_config.toml")

    # def test_base_lps(self):
    #    """Tests base LP setups"""
    #    self.run_base_lp_test(agent_policies=["single_lp"], config_file="config/example_config.toml")

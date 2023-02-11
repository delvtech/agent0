"""Testing for the ElfPy package modules"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest
import logging

import utils_for_tests as test_utils  # utilities for testing

from elfpy.types import Config
import elfpy.utils.outputs as output_utils  # utilities for file outputs


class BaseParameterTest(unittest.TestCase):
    """Generic Parameter Test class"""

    def run_base_trade_test(
        self,
        agent_policies,
        override=None,
        delete_logs=True,
    ):
        """Assigns member variables that are useful for many tests"""
        output_utils.setup_logging(log_filename=".logging/test_max_short.log", log_level=logging.DEBUG)
        config = Config()
        config.num_trading_days = 3  # sim 3 days to keep it fast for testing
        config.num_blocks_per_day = 3  # 3 block a day, keep it fast for testing
        config.num_position_days = 90
        config.init_lp = False
        if override is not None:
            for key, value in override.items():
                setattr(config, key, value)
        simulator = test_utils.setup_simulation_entities(config=config, agent_policies=agent_policies)
        print(f"{simulator.agents=}")
        print(f"running simulator with {len(simulator.agents)} agents")
        simulator.run_simulation()
        output_utils.close_logging(delete_logs=delete_logs)
        return simulator


class GetMaxShortTests(BaseParameterTest):
    """Tests of custom parameters"""

    def test_max_short_without_init(self):
        """set up a short that will attempt to trade more than possible"""
        agent_policies = ["single_lp:amount_to_lp=200", "single_short:amount_to_trade=500"]
        self.run_base_trade_test(agent_policies=agent_policies)

    def test_max_short_with_init_shuffle_users(self):
        """set up a short that will attempt to trade more than possible, but with init_lp"""
        agent_policies = ["single_lp:amount_to_lp=200", "single_short:amount_to_trade=500"]
        self.run_base_trade_test(agent_policies=agent_policies, override={"init_lp": True})

    def test_max_short_with_init_deterministic(self):
        """set up a short that will attempt to trade more than possible, but with init_lp"""
        agent_policies = ["single_lp:amount_to_lp=200", "single_short:amount_to_trade=500"]
        self.run_base_trade_test(agent_policies=agent_policies, override={"init_lp": True, "shuffle_users": False})

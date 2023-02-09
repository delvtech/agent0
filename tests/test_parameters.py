"""Testing for the ElfPy package modules"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest
import logging

import numpy as np
import utils_for_tests as test_utils  # utilities for testing

import elfpy.utils.outputs as output_utils  # utilities for file outputs


class BaseParameterTest(unittest.TestCase):
    """Generic Parameter Test class"""

    def run_base_trade_test(
        self,
        agent_policies,
        config_file="config/example_config.toml",
        delete_logs=True,
    ):
        """Assigns member variables that are useful for many tests"""
        output_utils.setup_logging(log_filename=".logging/test_parameters.log", log_level=logging.DEBUG)
        override_dict = {
            "num_trading_days": 3,  # sim 3 days to keep it fast for testing
            "num_blocks_per_day": 3,  # 3 block a day, keep it fast for testing
            "num_position_days": 90,
        }
        simulator = test_utils.setup_simulation_entities(
            config_file=config_file, override_dict=override_dict, agent_policies=agent_policies
        )
        simulator.run_simulation()
        output_utils.close_logging(delete_logs=delete_logs)
        return simulator

    def run_custom_parameters_test(self, agent_policies, expected_result, delete_logs=True):
        """Test custom parameters passed to agent creation"""
        # create simulator with agent_policies
        simulator = self.run_base_trade_test(agent_policies=agent_policies, delete_logs=delete_logs)
        number_of_init_agents = 0  # count number of init agents so we can skip over them
        for all_agent_index, agent in simulator.agents.items():  # loop over all agents
            if agent.name == "init_lp":
                number_of_init_agents += 1
            else:  # only for custom agents, loop across them and check their parameters
                custom_agent_index = all_agent_index - number_of_init_agents  # identify which custom agent we are on
                expected_result_dict = expected_result[custom_agent_index]
                for key, value in expected_result_dict.items():  # for each custom parameter to check
                    np.testing.assert_equal(
                        getattr(agent, key),
                        value,
                        err_msg=f"{key} does not equal {value}",
                    )


class CustomParameterTests(BaseParameterTest):
    """Tests of custom parameters"""

    def test_successfully_pass_custom_parameters(self):
        """Test successfully setting to passsed in values"""
        agent_policies = ["single_lp:amount_to_lp=200", "single_short:amount_to_trade=500"]
        expected_result = [{"amount_to_lp": 200}, {"amount_to_trade": 500}]
        self.run_custom_parameters_test(agent_policies=agent_policies, expected_result=expected_result)

    def test_failure_first_parameter_smaller(self):
        """Test failure when first parameter is smaller"""
        agent_policies = ["single_lp:amount_to_lp=199", "single_short:amount_to_trade=500"]
        expected_result = [{"amount_to_lp": 200}, {"amount_to_trade": 500}]
        exception_type = AssertionError
        with self.assertRaises(exception_type):
            self.run_custom_parameters_test(agent_policies=agent_policies, expected_result=expected_result)

    def test_failure_first_parameter_larger(self):
        """Test failure when first parameter is larger"""
        agent_policies = ["single_lp:amount_to_lp=201", "single_short:amount_to_trade=500"]
        expected_result = [{"amount_to_lp": 200}, {"amount_to_trade": 500}]
        exception_type = AssertionError
        with self.assertRaises(exception_type):
            self.run_custom_parameters_test(agent_policies=agent_policies, expected_result=expected_result)

    def test_failure_second_parameter_smaller(self):
        """Test failure when second parameter is smaller"""
        agent_policies = ["single_lp:amount_to_lp=200", "single_short:amount_to_trade=499"]
        expected_result = [{"amount_to_lp": 200}, {"amount_to_trade": 500}]
        exception_type = AssertionError
        with self.assertRaises(exception_type):
            self.run_custom_parameters_test(agent_policies=agent_policies, expected_result=expected_result)

    def test_failure_second_parameter_larger(self):
        """Test failure when second parameter is larger"""
        agent_policies = ["single_lp:amount_to_lp=200", "single_short:amount_to_trade=501"]
        expected_result = [{"amount_to_lp": 200}, {"amount_to_trade": 500}]
        exception_type = AssertionError
        with self.assertRaises(exception_type):
            self.run_custom_parameters_test(agent_policies=agent_policies, expected_result=expected_result)

    def test_failure_incorrect_first_parameter(self):
        """Test failure when trying to assignt a parameter that doesn't exist"""
        agent_policies = ["single_lp:amount_to_lpx=200", "single_short:amount_to_trade=500"]
        expected_result = [{"amount_to_lp": 200}, {"amount_to_trade": 500}]
        exception_type = AttributeError
        with self.assertRaises(exception_type):
            self.run_custom_parameters_test(agent_policies=agent_policies, expected_result=expected_result)

    def test_failure_incorrect_second_parameter(self):
        """Test failure when trying to assignt a parameter that doesn't exist"""
        agent_policies = ["single_lp:amount_to_lp=200", "single_short:amount_to_tradex=500"]
        expected_result = [{"amount_to_lp": 200}, {"amount_to_trade": 500}]
        exception_type = AttributeError
        with self.assertRaises(exception_type):
            self.run_custom_parameters_test(agent_policies=agent_policies, expected_result=expected_result)

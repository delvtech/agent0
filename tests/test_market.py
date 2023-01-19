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


class BaseMarketTest(unittest.TestCase):
    """Generic Parameter Test class"""

    @staticmethod
    def setup_simulation_entities(config_file, override_dict, agent_policies) -> tuple[Simulator, Market]:
        """Construct and run the simulator"""
        # create config object
        config = config_utils.override_config_variables(
            config_utils.load_and_parse_config_file(config_file), override_dict
        )
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
            random_sim_vars.target_pool_apr,
            random_sim_vars.fee_percent,
            config.simulator.token_duration,
            random_sim_vars.vault_apr,
            random_sim_vars.init_share_price,
        )
        # instantiate the init_lp agent
        init_agents = {
            0: sim_utils.get_init_lp_agent(
                market,
                random_sim_vars.target_liquidity,
                random_sim_vars.target_pool_apr,
                random_sim_vars.fee_percent,
            )
        }
        # set up simulator with only the init_lp_agent
        simulator = Simulator(
            config=config,
            market=market,
            agents=init_agents.copy(),  # we use this variable later, so pass a copy ;)
            rng=rng,
            random_simulation_variables=random_sim_vars,
        )
        # initialize the market using the LP agent
        simulator.collect_and_execute_trades()
        # get trading agent list
        for agent_id, policy_instruction in enumerate(agent_policies):
            if ":" in policy_instruction:  # we have custom parameters
                policy_name, not_kwargs = BaseMarketTest.validate_custom_parameters(policy_instruction)
            else:  # we don't have custom parameters
                policy_name = policy_instruction
                not_kwargs = {}
            wallet_address = len(init_agents) + agent_id
            agent = import_module(f"elfpy.policies.{policy_name}").Policy(
                wallet_address=wallet_address,  # first policy goes to init_lp_agent
            )
            for key, value in not_kwargs.items():
                setattr(agent, key, value)
            agent.log_status_report()
            simulator.agents.update({agent.wallet.address: agent})
        return simulator, market

    @staticmethod
    def validate_custom_parameters(policy_instruction):
        """
        separate the policy name from the policy arguments and validate the arguments
        """
        policy_name, policy_args = policy_instruction.split(":")
        try:
            policy_args = policy_args.split(",")
        except AttributeError as exception:
            logging.info("ERROR: No policy arguments provided")
            raise exception
        try:
            policy_args = [arg.split("=") for arg in policy_args]
        except AttributeError as exception:
            logging.info("ERROR: Policy arguments must be provided as key=value pairs")
            raise exception
        try:
            kwargs = {key: float(value) for key, value in policy_args}
        except ValueError as exception:
            logging.info("ERROR: Policy arguments must be provided as key=value pairs")
            raise exception
        return policy_name, kwargs

    def run_base_market_test_one_timestep(
        self,
        agent_policies,
        config_file="config/example_config.toml",
        delete_logs=True,
    ):
        """Create base structure for future tests"""
        output_utils.setup_logging(log_filename=".logging/test_trades.log", log_level=logging.DEBUG)
        # load default config
        override_dict = {
            "pricing_model_name": "Yieldspace",
            "target_liquidity": 10e6,
            "fee_percent": 0.1,
            "target_pool_apr": 0.05,
            "vault_apr": {"type": "constant", "value": 0.05},
            # minimal simulation steps, we only care to investigate the first day's trades
            "num_trading_days": 10,
            "num_blocks_per_day": 3,
            "shuffle_users": False,  # make it deterministic
        }
        simulator, market = self.setup_simulation_entities(
            config_file=config_file, override_dict=override_dict, agent_policies=agent_policies
        )
        # simulator.run_simulation()  # run the simulation
        simulator.collect_and_execute_trades()  # execute one time-step only
        output_utils.close_logging(delete_logs=delete_logs)
        return simulator, market

    def run_market_test_one_timestep(self, agent_policies, expected_wallet, delete_logs=True):
        """Test market trades result in the expected wallet balances"""
        simulator, market = self.run_base_market_test_one_timestep(
            agent_policies=agent_policies, delete_logs=delete_logs
        )
        # simulation is over, now we inspect the output of the agents' wallets
        number_of_init_agents = 0  # count number of init agents so we can skip over them
        for all_agent_index, agent in simulator.agents.items():  # loop over all agents
            if agent.name == "init_lp":
                number_of_init_agents += 1
            else:  # only for custom agents, loop across them and check their parameters
                custom_agent_index = all_agent_index - number_of_init_agents  # identify which custom agent we are on
                expected_wallet_dict = expected_wallet[custom_agent_index]
                for account, expected_balance in expected_wallet_dict.items():  # for each custom parameter to check
                    agent_balance = getattr(agent.wallet, account)
                    if isinstance(agent_balance, dict):
                        list_of_account_values = list(agent_balance.values())
                        agent_balance_in_pts = sum(x.balance for x in list_of_account_values)
                    agent_balance_in_base = agent_balance_in_pts * market.spot_price

                    # value of Long position in base has to be less than the # of PTs
                    # it could only get close if price were equal to 1, and even then there would be slippage
                    assert agent_balance_in_base < agent.amount_to_trade, (
                        f"agent #{custom_agent_index}'s {account} is worth more than the amount they traded",
                    )

                    # this holds only if we know the exact value
                    # np.testing.assert_almost_equal(
                    #     getattr(agent.wallet, account),
                    #     expected_balance,
                    #     err_msg=f"agent #{custom_agent_index}'s {account} does not equal {expected_balance}, instead we have (base,pt)=({agent_balance_in_base},{agent_balance_in_pts})",
                    # )


class CustomParameterTests(BaseMarketTest):
    """Tests of market trades"""

    def test_100_long_one_timestep(self):
        """self-explanatory"""
        agent_policies = ["single_long:amount_to_trade=100"]  # this is a list to allow testing multiple agents
        expected_wallet = [{"longs": 101}]  # list to test multiple agents, dict to test multiple balances
        self.run_market_test_one_timestep(agent_policies=agent_policies, expected_wallet=expected_wallet)

    # def test_failure_first_parameter_smaller(self):
    #     """Test failure when first parameter is smaller"""
    #     agent_policies = ["single_lp:amount_to_lp=199", "single_short:pt_to_short=500"]
    #     expected_wallet = [{"amount_to_lp": 200}, {"pt_to_short": 500}]
    #     exception_type = AssertionError
    #     with self.assertRaises(exception_type):
    #         self.run_market_test(agent_policies=agent_policies, expected_wallet=expected_wallet)

    # def test_failure_first_parameter_larger(self):
    #     """Test failure when first parameter is larger"""
    #     agent_policies = ["single_lp:amount_to_lp=201", "single_short:pt_to_short=500"]
    #     expected_wallet = [{"amount_to_lp": 200}, {"pt_to_short": 500}]
    #     exception_type = AssertionError
    #     with self.assertRaises(exception_type):
    #         self.run_market_test(agent_policies=agent_policies, expected_wallet=expected_wallet)

    # def test_failure_second_parameter_smaller(self):
    #     """Test failure when second parameter is smaller"""
    #     agent_policies = ["single_lp:amount_to_lp=200", "single_short:pt_to_short=499"]
    #     expected_wallet = [{"amount_to_lp": 200}, {"pt_to_short": 500}]
    #     exception_type = AssertionError
    #     with self.assertRaises(exception_type):
    #         self.run_market_test(agent_policies=agent_policies, expected_wallet=expected_wallet)

    # def test_failure_second_parameter_larger(self):
    #     """Test failure when second parameter is larger"""
    #     agent_policies = ["single_lp:amount_to_lp=200", "single_short:pt_to_short=501"]
    #     expected_wallet = [{"amount_to_lp": 200}, {"pt_to_short": 500}]
    #     exception_type = AssertionError
    #     with self.assertRaises(exception_type):
    #         self.run_market_test(agent_policies=agent_policies, expected_wallet=expected_wallet)


if __name__ == "__main__":
    unittest.main()

"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init
# pylint: disable=duplicate-code

import unittest
import logging

import numpy as np

import elfpy.utils.outputs as output_utils  # utilities for file outputs
import elfpy.utils.testing as test_utils  # utilities for testing


class BaseMarketTest(unittest.TestCase):
    """Generic Parameter Test class"""

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
        simulator = test_utils.setup_simulation_entities(
            config_file=config_file, override_dict=override_dict, agent_policies=agent_policies
        )
        # simulator.run_simulation()  # run the simulation
        simulator.collect_and_execute_trades()  # execute one time-step only
        output_utils.close_logging(delete_logs=delete_logs)
        return simulator

    def run_market_test_one_timestep(self, agent_policies, expected_wallet, delete_logs=True):
        """Test market trades result in the expected wallet balances"""
        simulator = self.run_base_market_test_one_timestep(agent_policies=agent_policies, delete_logs=delete_logs)
        # simulation is over, now we inspect the output of the agents' wallets
        number_of_init_agents = 0  # count number of init agents so we can skip over them
        for all_agent_index, agent in simulator.agents.items():  # loop over all agents
            if agent.name == "init_lp":
                number_of_init_agents += 1
            else:  # only for custom agents, loop across them and check their parameters
                custom_agent_index = all_agent_index - number_of_init_agents  # identify which custom agent we are on
                expected_wallet_dict = expected_wallet[custom_agent_index]
                for account, expected_balance in expected_wallet_dict.items():  # for each custom parameter to check
                    agent_balance_in_pts = getattr(agent.wallet, account)
                    if isinstance(agent_balance_in_pts, dict):
                        list_of_account_values = list(agent_balance_in_pts.values())
                        agent_balance_in_pts = sum(x.balance for x in list_of_account_values)
                    agent_balance_in_base = agent_balance_in_pts * simulator.market.spot_price

                    ##### GENERAL LOGIC TESTING #####
                    # value of Long position in base has to be less than the # of PTs
                    # it could only get close if price were equal to 1, and even then there would be slippage
                    assert agent_balance_in_base < agent.amount_to_trade, (
                        f"agent #{custom_agent_index}'s {account} is worth more than the amount they traded",
                    )

                    ##### SPECIFIC MANUAL TESTING #####
                    # this holds only if we know the exact value
                    np.testing.assert_almost_equal(
                        agent_balance_in_pts,
                        expected_balance,  # passed in as pt's
                        err_msg=(
                            f"agent #{custom_agent_index}'s {account} does not equal {expected_balance}"
                            f", instead we have (base,pt)=({agent_balance_in_base},{agent_balance_in_pts})",
                        ),
                    )


class CustomParameterTests(BaseMarketTest):
    """Tests of market trades"""

    def test_100_long_one_timestep(self):
        """self-explanatory"""
        # list to test multiple agents, dict to test multiple balances
        agent_policies = ["single_long:amount_to_trade=100"]
        expected_wallet = [{"longs": 101.12192099324383}]
        self.run_market_test_one_timestep(agent_policies=agent_policies, expected_wallet=expected_wallet)

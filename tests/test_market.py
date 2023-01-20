"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init
# pylint: disable=duplicate-code

from dataclasses import dataclass
import unittest
import logging

import numpy as np
import utils_for_tests as test_utils  # utilities for testing
from elfpy.types import MarketDeltas
from elfpy.wallet import Wallet, Long, Short

import elfpy.utils.outputs as output_utils  # utilities for file outputs


@dataclass
class Deltas:
    """Expected deltas for a trade"""

    market_deltas: MarketDeltas
    agent_deltas: Wallet

    __test__ = False  # pytest: don't test this class


class BaseMarketTest(unittest.TestCase):
    """Generic Parameter Test class"""

    def set_up_test(
        self,
        agent_policies,
        config_file="config/example_config.toml",
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
        return simulator

    def run_market_test(self, agent_policies, expected_wallet, delete_logs=True, full_sim=False):
        """Test market trades result in the expected wallet balances"""
        simulator = self.set_up_test(agent_policies=agent_policies)
        if full_sim:
            simulator.run_simulation()  # run the simulation
        else:
            simulator.collect_and_execute_trades()  # execute one time-step only
        output_utils.close_logging(delete_logs=delete_logs)
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
                            f", instead we have (base,pt)=({agent_balance_in_base},{agent_balance_in_pts})"
                        ),
                    )

    def run_market_test_open_long(self, agent_policy, expected_deltas: Deltas, delete_logs=True):
        """Test market trades result in the expected wallet balances"""
        simulator = self.set_up_test(agent_policies=[agent_policy])
        agent = simulator.agents[1]
        market_deltas, agent_deltas = simulator.market.open_long(
            wallet_address=1,
            trade_amount=agent.amount_to_trade,
        )
        # end simulation here, now we check values
        actual_deltas = Deltas(market_deltas=market_deltas, agent_deltas=agent_deltas)
        logging.debug(
            "=== MARKET DELTAS ===\nexpected market deltas: %s\nactual market deltas: %s",
            expected_deltas.market_deltas,
            actual_deltas.market_deltas,
        )
        self.assertEqual(expected_deltas.market_deltas, actual_deltas.market_deltas, "market deltas do not match")
        logging.debug(
            "=== AGENT DELTAS ===\nexpected agent deltas: %s\nactual agent deltas: %s",
            expected_deltas.agent_deltas,
            actual_deltas.agent_deltas,
        )
        self.assertEqual(expected_deltas.agent_deltas, actual_deltas.agent_deltas, "market deltas do not match")
        output_utils.close_logging(delete_logs=delete_logs)


class MarketTestsOneFunction(BaseMarketTest):
    """Tests of market trades that execute only one market function"""

    def test_100_long(self):
        """self-explanatory"""
        agent_policy = "single_long:amount_to_trade=100"
        # agent wants to go long 100 base asset so they will sell 100 base asset and buy equivalent amount of bonds
        # assume trade_result is correct, since we're not testing the pricing model here
        trade_result = 101.12192099324383
        # assign to appropriate token, for readability, signs from the perspective of the agent
        d_base = -100
        d_bonds = trade_result
        # signs are flipped from the perspective of the market
        expected_market_deltas = MarketDeltas(
            d_base_asset=-d_base,
            d_token_asset=-d_bonds,
            d_base_buffer=-d_base,
            d_bond_buffer=0,
            d_lp_reserves=0,
            d_share_price=0,
        )
        expected_agent_deltas = Wallet(
            address=1,
            base=d_base,
            longs={0: Long(d_bonds)},
        )
        expected_deltas = Deltas(market_deltas=expected_market_deltas, agent_deltas=expected_agent_deltas)
        self.run_market_test_open_long(agent_policy=agent_policy, expected_deltas=expected_deltas)


class MarketTestsOneTimestep(BaseMarketTest):
    """Tests of market trades that execute the simulation for one timestep only"""

    def test_100_long(self):
        """self-explanatory"""
        # list to test multiple agents, dict to test multiple balances
        agent_policies = ["single_long:amount_to_trade=100"]
        expected_wallet = [{"longs": 101.12192099324383}]
        self.run_market_test(agent_policies=agent_policies, expected_wallet=expected_wallet)

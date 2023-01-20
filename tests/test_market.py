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

    def compare_deltas(self, actual_deltas: Deltas, expected_deltas: Deltas, delete_logs):
        """Compare actual deltas to expected deltas"""

        def compare_thing(thing: str, expected_thing, actual_thing):
            logging.debug(
                "=== %s ===\nexpected %s: %s\nactual %s: %s",
                thing.upper(),
                thing,
                expected_thing,
                thing,
                actual_thing,
            )
            self.assertEqual(expected_thing, actual_thing, f"{thing} do not match")

        compare_thing("market deltas", expected_deltas.market_deltas, actual_deltas.market_deltas)
        compare_thing("agent deltas", expected_deltas.agent_deltas, actual_deltas.agent_deltas)
        output_utils.close_logging(delete_logs=delete_logs)

    def run_market_test_open_long(self, agent_policy, expected_deltas: Deltas, delete_logs=True):
        """Test market trades result in the expected wallet balances"""
        simulator = self.set_up_test(agent_policies=[agent_policy])
        agent = simulator.agents[1]
        market_deltas, agent_deltas = simulator.market.open_long(
            wallet_address=1,
            trade_amount=agent.amount_to_trade,
        )
        actual_deltas = Deltas(market_deltas=market_deltas, agent_deltas=agent_deltas)
        self.compare_deltas(actual_deltas=actual_deltas, expected_deltas=expected_deltas, delete_logs=delete_logs)

    def run_market_test_open_short(self, agent_policy, expected_deltas: Deltas, delete_logs=True):
        """Test market trades result in the expected wallet balances"""
        simulator = self.set_up_test(agent_policies=[agent_policy])
        agent = simulator.agents[1]
        market_deltas, agent_deltas = simulator.market.open_short(
            wallet_address=1,
            trade_amount=agent.amount_to_trade,
        )
        actual_deltas = Deltas(market_deltas=market_deltas, agent_deltas=agent_deltas)
        self.compare_deltas(actual_deltas=actual_deltas, expected_deltas=expected_deltas, delete_logs=delete_logs)

    def run_market_test_close_long(self, agent_policy, expected_deltas: Deltas, delete_logs=True):
        """Test market trades result in the expected wallet balances"""
        simulator = self.set_up_test(agent_policies=[agent_policy])
        agent = simulator.agents[1]
        market_deltas, agent_deltas = simulator.market.open_long(
            wallet_address=1,
            trade_amount=agent.amount_to_trade,  # in base: that's the thing in your wallet you want to sell
        )
        # peek inside the agent's wallet and see how many bonds they have
        amount_of_bonds_purchased = agent_deltas.longs[0].balance
        # sell those bonds to close the long
        market_deltas, agent_deltas = simulator.market.close_long(
            mint_time=0,
            wallet_address=1,
            trade_amount=amount_of_bonds_purchased,  # in bonds: that's the thing in your wallet you want to sell
        )
        actual_deltas = Deltas(market_deltas=market_deltas, agent_deltas=agent_deltas)
        self.compare_deltas(actual_deltas=actual_deltas, expected_deltas=expected_deltas, delete_logs=delete_logs)

    def run_market_test_close_short(self, agent_policy, expected_deltas: Deltas, delete_logs=True):
        """Test market trades result in the expected wallet balances"""
        simulator = self.set_up_test(agent_policies=[agent_policy])
        agent = simulator.agents[1]
        market_deltas, agent_deltas = simulator.market.open_short(
            wallet_address=1,
            trade_amount=agent.amount_to_trade,  # in bonds: that's the thing you want to short
        )
        # peek inside the agent's wallet and see how many bonds they have
        amount_of_bonds_sold = agent_deltas.shorts[0].balance
        # sell those bonds to close the short
        market_deltas, agent_deltas = simulator.market.close_short(
            mint_time=0,
            wallet_address=1,
            trade_amount=amount_of_bonds_sold,  # in bonds: that's the thing you owe, and need to buy back
        )
        actual_deltas = Deltas(market_deltas=market_deltas, agent_deltas=agent_deltas)
        self.compare_deltas(actual_deltas=actual_deltas, expected_deltas=expected_deltas, delete_logs=delete_logs)


class MarketTestsOneFunction(BaseMarketTest):
    """Tests of market trades that execute only one market function"""

    def test_100_open_long(self):
        """self-explanatory"""
        # agent_policies = [f"single_long:amount_to_trade={amount}" for amount in [100, 10_000, 1_000_000, 100_000_000]]

        agent_policy = "single_long:amount_to_trade=100"
        # agent wants to go long 100 base asset so they will sell 100 base asset and buy equivalent amount of bonds
        # assume trade_result is correct, since we're not testing the pricing model here
        trade_result = 101.12192099324383
        # assign to appropriate token, for readability using absolute values, assigning +/- below
        d_base = 100
        d_bonds = trade_result
        fees_paid = 0.12465872084668873
        # signs are flipped from the perspective of the market
        expected_market_deltas = MarketDeltas(
            d_base_asset=d_base,  # base asset increases because agent is selling base into the market to buy bonds
            d_token_asset=-d_bonds,  # token asset increases because agent is buying bonds from the market to sell base
            d_base_buffer=d_bonds,  # base buffer increases, identifying agent deposits, set aside from LPs
            d_bond_buffer=0,  # bond buffer doesn't change because agent did not deposit bonds
            d_lp_reserves=0,
            d_share_price=0,
        )
        expected_agent_deltas = Wallet(
            address=1,
            base=-d_base,  # base asset decreases because agent is spending base to buy bonds
            longs={0: Long(d_bonds)},  # longs increase by the amount of bonds bought
            fees_paid=fees_paid,
        )
        expected_deltas = Deltas(market_deltas=expected_market_deltas, agent_deltas=expected_agent_deltas)
        self.run_market_test_open_long(agent_policy=agent_policy, expected_deltas=expected_deltas)

    def test_100_close_long(self):
        """self-explanatory"""
        # agent_policies = [f"single_long:amount_to_trade={amount}" for amount in [100, 10_000, 1_000_000, 100_000_000]]

        agent_policy = "single_long:amount_to_trade=100"
        # agent wants to go long 100 base asset so they will sell 100 base asset and buy equivalent amount of bonds
        # assume trade_result is correct, since we're not testing the pricing model here
        trade_result_open_long_in_bonds = 101.12192099324383  # result of the first trade
        trade_result_close_long_in_base = 99.75235611262872  # result of the second trade
        # assign to appropriate token, for readability using absolute values, assigning +/- below
        d_base = trade_result_close_long_in_base  # result of the second trade
        d_bonds = trade_result_open_long_in_bonds  # result of the first trade
        fees_paid = 0.12450522697246555
        # signs are flipped from the perspective of the market
        expected_market_deltas = MarketDeltas(
            d_base_asset=-d_base,  # base asset decreases because agent is buying base into the market to sell bonds
            d_token_asset=d_bonds,  # token asset increases because agent is selling bonds into the market to buy base
            d_base_buffer=-d_bonds,  # base buffer decreases, identifying agent withdrawals, no longer set aside
            d_bond_buffer=0,  # bond buffer doesn't change because agent did not withdraw bonds
            d_lp_reserves=0,
            d_share_price=0,
        )
        expected_agent_deltas = Wallet(
            address=1,
            base=d_base,  # base asset increases because agent is getting base back to close his bond position
            longs={0: Long(-d_bonds)},  # longs decrease by the amount of bonds sold to close the position
            fees_paid=fees_paid,
        )
        expected_deltas = Deltas(market_deltas=expected_market_deltas, agent_deltas=expected_agent_deltas)
        self.run_market_test_close_long(agent_policy=agent_policy, expected_deltas=expected_deltas)

    def test_100_open_short(self):
        """self-explanatory"""
        # agent_policies = [f"single_long:amount_to_trade={amount}" for amount in [100, 10_000, 1_000_000, 100_000_000]]

        agent_policy = "single_short:amount_to_trade=100"
        # agent wants to go short 100 base asset so they will sell 100 base asset and buy equivalent amount of bonds
        # assume trade_result is correct, since we're not testing the pricing model here
        trade_result = 98.64563016085916
        max_loss = 100 - trade_result  # worst case scenario: price goes up, forced to buy back at 100
        fees_paid = 0.12312387437812222
        # assign to appropriate token, for readability using absolute values, assigning +/- below
        d_base = trade_result  # proceeds from your sale of bonds, go into your margin account so you don't rug
        d_bonds = 100
        d_margin = d_base + max_loss
        # signs are flipped from the perspective of the market
        expected_market_deltas = MarketDeltas(
            d_base_asset=-d_base,  # base asset decreases because agent is buying base from the market to sell bonds
            d_token_asset=d_bonds,  # token asset increases because agent is selling bonds into the market to buy base
            d_base_buffer=0,  # bond buffer doesn't change because agent did not deposit base
            d_bond_buffer=d_bonds,  # bond buffer increases, identifying agent deposits, set aside from LPs
            d_lp_reserves=0,
            d_share_price=0,
        )
        expected_agent_deltas = Wallet(
            address=1,
            base=-max_loss,  # base asset decreases because agent is spending base to buy bonds
            # shorts increase by the amount of bonds sold
            # margin is the amount of base asset that is in the agent's margin account
            # it is composed of two parts: proceeds from sale of bonds (d_base)
            # and the additional base deposited by the agent to cover the worst case scenario (max_loss)
            shorts={0: Short(balance=d_bonds, margin=d_margin)},
            fees_paid=fees_paid,
        )
        expected_deltas = Deltas(market_deltas=expected_market_deltas, agent_deltas=expected_agent_deltas)
        self.run_market_test_open_short(agent_policy=agent_policy, expected_deltas=expected_deltas)

    def test_100_close_short(self):
        """self-explanatory"""
        # agent_policies = [f"single_long:amount_to_trade={amount}" for amount in [100, 10_000, 1_000_000, 100_000_000]]

        agent_policy = "single_short:amount_to_trade=100"
        # agent wants to go long 100 base asset so they will sell 100 base asset and buy equivalent amount of bonds
        # assume trade_result is correct, since we're not testing the pricing model here
        trade_result_close_short_in_base = 98.89189235154787  # result of the second trade
        # assign to appropriate token: for readability using absolute values, assigning +/- below
        d_base_market = trade_result_close_short_in_base  # result of the second trade
        d_bonds = 100
        d_margin = d_bonds  # reducing the margin in your account by the total amount put up (covering worst case)
        d_base_agent = 100 - trade_result_close_short_in_base  # remaining margin after closing the position
        fees_paid = 0.12312387437812222
        # signs are flipped from the perspective of the market
        expected_market_deltas = MarketDeltas(
            d_base_asset=d_base_market,  # base asset decreases because agent is buying base from the market to sell bonds
            d_token_asset=-d_bonds,  # token asset increases because agent is selling bonds into the market to buy base
            d_base_buffer=0,  # base buffer doesn't change because agent did not withdraw base
            d_bond_buffer=-d_bonds,  # bond buffer decreases, identifying agent withdrawals, no longer set aside
            d_lp_reserves=0,
            d_share_price=0,
        )
        expected_agent_deltas = Wallet(
            address=1,
            base=d_base_agent,  # base asset increases because agent is getting base back to close his bond position
            shorts={
                0: Short(balance=-d_bonds, margin=-d_margin)
            },  # shorts decrease by the amount of bonds sold to close the position
            fees_paid=fees_paid,
        )
        # FOLLOW THE MONEY
        # trade 1: short some shit
        # - wallet looks like this: Short(balance: 100.0, margin: 100.0)
        # - you're short 100 and put up 100 margin to cover the worst case scenario
        # trade 2: close short
        # - wallet looks like this: Short(balance: 0.0, margin: 0.0)
        # - you're short 0 and put up 0 margin to cover the worst case scenario
        expected_deltas = Deltas(market_deltas=expected_market_deltas, agent_deltas=expected_agent_deltas)
        self.run_market_test_close_short(agent_policy=agent_policy, expected_deltas=expected_deltas)


class MarketTestsOneTimestep(BaseMarketTest):
    """Tests of market trades that execute the simulation for one timestep only"""

    def test_100_long(self):
        """self-explanatory"""
        # list to test multiple agents, dict to test multiple balances
        agent_policies = ["single_long:amount_to_trade=100"]
        expected_wallet = [{"longs": 101.12192099324383}]
        self.run_market_test(agent_policies=agent_policies, expected_wallet=expected_wallet)

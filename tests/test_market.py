"""Testing for the ElfPy package modules"""
from __future__ import annotations  # types are strings by default in 3.11

from dataclasses import dataclass
import unittest
import logging
from typing import Any

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
            "trade_fee_percent": 0.1,
            # our model currently has no redemption fee for yieldspace, if added these tests will break
            "redemption_fee_percent": 0.1,
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

    def assert_equal_and_log(self, descriptor: str, expected: Any, actual: Any):
        """Compare actual thing to expected thing"""
        logging.debug(
            "=== %s ===\nexpected %s: %s\nactual %s: %s", descriptor.upper(), descriptor, expected, descriptor, actual
        )
        self.assertEqual(expected, actual, f"{descriptor} do not match")

    def compare_deltas(self, actual_deltas: Deltas, expected_deltas: Deltas):
        """Compare actual deltas to expected deltas"""
        self.assert_equal_and_log("market deltas", expected_deltas.market_deltas, actual_deltas.market_deltas)
        self.assert_equal_and_log("agent deltas", expected_deltas.agent_deltas, actual_deltas.agent_deltas)

    def run_market_test_open_long(self, agent_policy, expected_deltas: Deltas):
        """Test market trades result in the expected wallet balances"""
        simulator = self.set_up_test(agent_policies=[agent_policy])
        agent = simulator.agents[1]
        market_deltas, agent_deltas = simulator.market.open_long(
            wallet_address=1,
            trade_amount=agent.amount_to_trade,
        )
        actual_deltas = Deltas(market_deltas=market_deltas, agent_deltas=agent_deltas)
        self.compare_deltas(actual_deltas=actual_deltas, expected_deltas=expected_deltas)

    def run_market_test_open_short(self, agent_policy, expected_deltas: Deltas):
        """Test market trades result in the expected wallet balances"""
        simulator = self.set_up_test(agent_policies=[agent_policy])
        agent = simulator.agents[1]
        market_deltas, agent_deltas = simulator.market.open_short(
            wallet_address=1,
            trade_amount=agent.amount_to_trade,
        )
        actual_deltas = Deltas(market_deltas=market_deltas, agent_deltas=agent_deltas)
        self.compare_deltas(actual_deltas=actual_deltas, expected_deltas=expected_deltas)

    def run_market_test_close_long(self, agent_policy, expected_deltas: Deltas):
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
        self.compare_deltas(actual_deltas=actual_deltas, expected_deltas=expected_deltas)

    def run_market_test_close_short(
        self, agent_policy, expected_deltas: Deltas, delete_logs=True, partial: float = 1, tick_time=False
    ):  # pylint: disable=too-many-arguments
        # disabling pylint because this function is used in 3 tests w/ tiny parameter tweaks
        """Test market trades result in the expected wallet balances"""
        simulator = self.set_up_test(agent_policies=[agent_policy])
        agent = simulator.agents[1]
        market_deltas, agent_deltas = simulator.market.open_short(
            wallet_address=1,
            trade_amount=agent.amount_to_trade,  # in bonds: that's the thing you want to short
        )
        # peek inside the agent's wallet and see how many bonds they have
        amount_of_bonds_sold = agent_deltas.shorts[0].balance
        # sell those bonds to close the short (partial is the amount of the short to close, 1.0 by default)
        trade_amount = amount_of_bonds_sold * partial
        mint_time = 0
        if tick_time:
            simulator.market.tick(simulator.market_step_size())
        market_deltas, agent_deltas = simulator.market.close_short(
            mint_time=mint_time,
            wallet_address=1,
            open_share_price=agent_deltas.shorts[mint_time].open_share_price,
            trade_amount=trade_amount,  # in bonds: that's the thing you owe, and need to buy back
        )
        actual_deltas = Deltas(market_deltas=market_deltas, agent_deltas=agent_deltas)
        self.compare_deltas(actual_deltas=actual_deltas, expected_deltas=expected_deltas)
        # TODO: do we want to test the final value in the wallet?
        # we're not actually updating wallets here, but a full simulation test would
        # we could test the final wallet value there much more easily
        output_utils.close_logging(delete_logs=delete_logs)


class MarketTestsOneFunction(BaseMarketTest):
    """
    This test concerns itself with:
    - outputs of the 4 trade-executing market functions: open_long, close_long, open_short, close_short
    - namely market_deltas and agent_deltas (change to market and agent wallets)
    - testing limited as close as possible to one function at a time (not running the simulation)
    This results in different number of trades:
    - execute one trade: for open long and short
    - open a position then close it (two trades): for close long and short
    Additionally, we add a few extra checks for close short only (the trickier case, as it involves margin):
    - partially close a short
    - tick time forward before closing short
    Does not check the outputs of the pricing model, those are taken as given, and stored as numbers below
    """

    def test_100_open_long(self):
        """open long of 100 bonds"""
        agent_policy = "single_long:amount_to_trade=100"
        # agent wants to go long 100 base asset so they will sell 100 base asset and buy equivalent amount of bonds
        trade_result = 101.10958152508731  # taken from pricing model output, not tested here
        # assign to appropriate token, for readability using absolute values, assigning +/- below
        d_base = 100
        d_bonds = trade_result
        fees_paid = 0.12328767123287677  # taken from pricing model output, not tested here

        expected_market_deltas = MarketDeltas(
            d_base_asset=d_base,  # base asset increases because agent is selling base into market to buy bonds
            d_token_asset=-d_bonds,  # token asset increases because agent is buying bonds from market to sell base
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
        """open long of 100 bonds, close long of 100 bonds"""
        agent_policy = "single_long:amount_to_trade=100"
        # agent wants to go long 100 base asset so they will sell 100 base asset and buy equivalent amount of bonds
        trade_result_open_long_in_bonds = 101.10958152508731  # pricing model output of first test, not tested here
        trade_result_close_long_in_base = 99.7550614568167  # pricing model output of second test, not tested here
        # assign to appropriate token, for readability using absolute values, assigning +/- below
        d_bonds = trade_result_open_long_in_bonds  # result of the first trade
        d_base = trade_result_close_long_in_base  # result of the second trade
        trade_fees_paid = 0.12313751471255564  # taken from pricing model output, not tested here
        redemption_fees_paid = 0  # taken from pricing model output, not tested here

        expected_market_deltas = MarketDeltas(
            d_base_asset=-d_base,  # base asset decreases because agent is buying base into market to sell bonds
            d_token_asset=d_bonds,  # token asset increases because agent is selling bonds into market to buy base
            d_base_buffer=-d_bonds,  # base buffer decreases, identifying agent withdrawals, no longer set aside
            d_bond_buffer=0,  # bond buffer doesn't change because agent did not withdraw bonds
            d_lp_reserves=0,
            d_share_price=0,
        )
        expected_agent_deltas = Wallet(
            address=1,
            base=d_base,  # base asset increases because agent is getting base back to close his bond position
            longs={0: Long(-d_bonds)},  # longs decrease by the amount of bonds sold to close the position
            fees_paid=trade_fees_paid + redemption_fees_paid,
        )
        expected_deltas = Deltas(market_deltas=expected_market_deltas, agent_deltas=expected_agent_deltas)
        self.run_market_test_close_long(agent_policy=agent_policy, expected_deltas=expected_deltas)

    def test_100_open_short(self):
        """open short of 100 bonds"""
        agent_policy = "single_short:amount_to_trade=100"
        # agent wants to go short 100 base asset so they will sell 100 base asset and buy equivalent amount of bonds
        trade_result = 98.66034458202579  # taken from pricing model output, not tested here
        max_loss = 100 - trade_result  # worst case scenario: price goes up, forced to buy back at 100
        fees_paid = 0.12178619756427611  # taken from pricing model output, not tested here
        # assign to appropriate token, for readability using absolute values, assigning +/- below
        d_base = trade_result  # proceeds from your sale of bonds, go into your margin account so you don't rug
        d_bonds = 100
        d_margin = d_base + max_loss
        open_share_price = 1.0086194128439765

        expected_market_deltas = MarketDeltas(
            d_base_asset=-d_base,  # base asset decreases because agent is buying base from market to sell bonds
            d_token_asset=d_bonds,  # token asset increases because agent is selling bonds into market to buy base
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
            shorts={0: Short(balance=d_bonds, open_share_price=open_share_price)},
            fees_paid=fees_paid,
        )
        expected_deltas = Deltas(market_deltas=expected_market_deltas, agent_deltas=expected_agent_deltas)
        self.run_market_test_open_short(agent_policy=agent_policy, expected_deltas=expected_deltas)

    def test_100_close_short_full_right_away(self):
        """open short of 100 bonds, close short of 100 bonds"""
        agent_policy = "single_short:amount_to_trade=100"
        # agent wants to go long 100 base asset so they will sell 100 base asset and buy equivalent amount of bonds
        trade_result_close_short_in_base = 98.90393146665825  # pricing model output of second test, not tested here
        # assign to appropriate token: for readability using absolute values, assigning +/- below
        d_base_market = trade_result_close_short_in_base  # result of the second trade
        d_bonds = 100
        d_margin = d_bonds  # reducing the margin in your account by the total amount put up (covering worst case)
        d_base_agent = 100 - trade_result_close_short_in_base  # remaining margin after closing the position
        fees_paid = 0.12178619756427611  # taken from pricing model output, not tested here
        expected_market_deltas = MarketDeltas(
            d_base_asset=d_base_market,  # base asset decreases because agent is buying base from market to sell bonds
            d_token_asset=-d_bonds,  # token asset increases because agent is selling bonds into market to buy base
            d_base_buffer=0,  # base buffer doesn't change because agent did not withdraw base
            d_bond_buffer=-d_bonds,  # bond buffer decreases, identifying agent withdrawals, no longer set aside
            d_lp_reserves=0,
            d_share_price=0,
        )
        expected_agent_deltas = Wallet(
            address=1,
            base=d_base_agent,  # base asset increases because agent is getting base back to close his bond position
            shorts={
                0: Short(balance=-d_bonds, open_share_price=0)
            },  # shorts decrease by the amount of bonds sold to close the position
            fees_paid=fees_paid,
        )
        expected_deltas = Deltas(market_deltas=expected_market_deltas, agent_deltas=expected_agent_deltas)
        self.run_market_test_close_short(agent_policy=agent_policy, expected_deltas=expected_deltas)

    def test_100_close_short_full_one_tick_later(self):
        """open short of 100 bonds, close short of 100 bonds"""
        agent_policy = "single_short:amount_to_trade=100"
        # agent wants to go long 100 base asset so they will sell 100 base asset and buy equivalent amount of bonds
        trade_result_close_short_in_base = 98.9079662511094  # pricing model output of second test, not tested here
        # assign to appropriate token: for readability using absolute values, assigning +/- below
        d_base_market = trade_result_close_short_in_base  # result of the second trade
        d_bonds = 100
        d_margin = d_bonds  # reducing the margin in your account by the total amount put up (covering worst case)
        d_base_agent = 100 - trade_result_close_short_in_base  # remaining margin after closing the position
        fees_paid = 0.12133788526308154  # taken from pricing model output, not tested here
        expected_market_deltas = MarketDeltas(
            d_base_asset=d_base_market,  # base asset decreases because agent is buying base from market to sell bonds
            d_token_asset=-d_bonds,  # token asset increases because agent is selling bonds into market to buy base
            d_base_buffer=0,  # base buffer doesn't change because agent did not withdraw base
            d_bond_buffer=-d_bonds,  # bond buffer decreases, identifying agent withdrawals, no longer set aside
            d_lp_reserves=0,
            d_share_price=0,
        )
        expected_agent_deltas = Wallet(
            address=1,
            base=d_base_agent,  # base asset increases because agent is getting base back to close his bond position
            shorts={
                0: Short(balance=-d_bonds, open_share_price=0)
            },  # shorts decrease by the amount of bonds sold to close the position
            fees_paid=fees_paid,
        )
        expected_deltas = Deltas(market_deltas=expected_market_deltas, agent_deltas=expected_agent_deltas)
        self.run_market_test_close_short(agent_policy=agent_policy, expected_deltas=expected_deltas, tick_time=True)

    def test_100_close_short_half_right_away(self):
        """open short of 100 bonds, close short of 50 bonds"""
        agent_policy = "single_short:amount_to_trade=100"
        # agent wants to go long 100 base asset so they will sell 100 base asset and buy equivalent amount of bonds
        trade_result_close_short_in_base = 49.451963922146845  # pricing model output of second test, not tested here
        # assign to appropriate token: for readability using absolute values, assigning +/- below
        d_base_market = trade_result_close_short_in_base  # result of the second trade
        d_bonds = 50  # face value
        d_worst_case_scenario = d_bonds  # in the worst case for the short, p=1 and they owe the face value
        # calculate the improvement in your max loss (worst case scenario - cost to close the short)
        d_max_loss = d_worst_case_scenario - trade_result_close_short_in_base
        d_base_agent = d_max_loss  # get back the improvement in your max loss
        d_margin = d_bonds  # reducing the margin in your account by the trade face value (covering worst case)
        fees_paid = 0.060893098782138055  # taken from pricing model output, not tested here
        expected_market_deltas = MarketDeltas(
            d_base_asset=d_base_market,  # base asset decreases because agent is buying base from market to sell bonds
            d_token_asset=-d_bonds,  # token asset increases because agent is selling bonds into market to buy base
            d_base_buffer=0,  # base buffer doesn't change because agent did not withdraw base
            d_bond_buffer=-d_bonds,  # bond buffer decreases, identifying agent withdrawals, no longer set aside
            d_lp_reserves=0,
            d_share_price=0,
        )
        expected_agent_deltas = Wallet(
            address=1,
            base=d_base_agent,  # base asset increases because agent is getting base back to close his bond position
            shorts={
                0: Short(balance=-d_bonds, open_share_price=0)
            },  # shorts decrease by the amount of bonds sold to close the position
            fees_paid=fees_paid,
        )
        expected_deltas = Deltas(market_deltas=expected_market_deltas, agent_deltas=expected_agent_deltas)
        self.run_market_test_close_short(agent_policy=agent_policy, expected_deltas=expected_deltas, partial=0.5)

    def test_100_close_short_half_one_tick_later(self):
        """open short of 100 bonds, close short of 50 bonds, one tick later"""
        agent_policy = "single_short:amount_to_trade=100"
        # agent wants to go long 100 base asset so they will sell 100 base asset and buy equivalent amount of bonds
        trade_result_close_short_in_base = 49.45398132093731  # pricing model output of second test, not tested here
        # assign to appropriate token: for readability using absolute values, assigning +/- below
        d_base_market = trade_result_close_short_in_base  # result of the second trade
        d_bonds = 50  # face value
        d_worst_case_scenario = d_bonds  # in the worst case for the short, p=1 and they owe the face value
        # calculate the improvement in your max loss (worst case scenario - cost to close the short)
        d_max_loss = d_worst_case_scenario - trade_result_close_short_in_base
        d_base_agent = d_max_loss  # get back the improvement in your max loss
        d_margin = d_bonds  # reducing the margin in your account by the trade face value (covering worst case)
        fees_paid = 0.06066894263154077  # taken from pricing model output, not tested here
        expected_market_deltas = MarketDeltas(
            d_base_asset=d_base_market,  # base asset decreases because agent is buying base from market to sell bonds
            d_token_asset=-d_bonds,  # token asset increases because agent is selling bonds into market to buy base
            d_base_buffer=0,  # base buffer doesn't change because agent did not withdraw base
            d_bond_buffer=-d_bonds,  # bond buffer decreases, identifying agent withdrawals, no longer set aside
            d_lp_reserves=0,
            d_share_price=0,
        )
        expected_agent_deltas = Wallet(
            address=1,
            base=d_base_agent,  # base asset increases because agent is getting base back to close his bond position
            shorts={
                0: Short(balance=-d_bonds, open_share_price=0)
            },  # shorts decrease by the amount of bonds sold to close the position
            fees_paid=fees_paid,
        )
        expected_deltas = Deltas(market_deltas=expected_market_deltas, agent_deltas=expected_agent_deltas)
        self.run_market_test_close_short(
            agent_policy=agent_policy, expected_deltas=expected_deltas, partial=0.5, tick_time=True
        )

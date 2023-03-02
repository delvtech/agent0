"""Testing for the ElfPy package modules"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest
import logging

import elfpy.utils.outputs as output_utils  # utilities for file outputs
import elfpy.utils.sim_utils as sim_utils
import elfpy.simulators.simulators as simulators
import elfpy.agents.wallet as wallet
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.markets.hyperdrive as hyperdrive_market
import elfpy.types as types


class TradeTests(unittest.TestCase):
    """Tests for executing trades from policies"""

    config: simulators.Config

    def setUp(self):
        """Create a config to be used throught the tests"""
        self.config = simulators.Config()
        self.config.target_liquidity = 10e6
        self.config.trade_fee_percent = 0.1
        self.config.redemption_fee_percent = 0.0
        self.config.target_fixed_apr = 0.05
        self.config.num_trading_days = 3
        self.config.num_blocks_per_day = 3
        self.config.variable_apr = [0.05] * self.config.num_trading_days

    def test_single_trade(self):
        """Tests the single_long and single_short policies where the amount traded is the full liquidity of the market"""
        output_utils.setup_logging(log_filename="test_trades", log_level=logging.DEBUG)
        test_cases = [
            {"agent_policy": "single_long", "num_position_days": 90, "pricing_model_name": "Yieldspace"},  # Test 1
            {"agent_policy": "single_long", "num_position_days": 365, "pricing_model_name": "Yieldspace"},  # Test 2
            {"agent_policy": "single_long", "num_position_days": 90, "pricing_model_name": "Hyperdrive"},  # Test 3
            {"agent_policy": "single_long", "num_position_days": 365, "pricing_model_name": "Hyperdrive"},  # Test 4
            {"agent_policy": "single_short", "num_position_days": 90, "pricing_model_name": "Yieldspace"},  # Test 5
            {"agent_policy": "single_short", "num_position_days": 365, "pricing_model_name": "Yieldspace"},  # Test 6
            {"agent_policy": "single_short", "num_position_days": 90, "pricing_model_name": "Hyperdrive"},  # Test 7
            {"agent_policy": "single_short", "num_position_days": 365, "pricing_model_name": "Hyperdrive"},  # Test 8
        ]
        for test_number, test_case in enumerate(test_cases):
            self.config.pricing_model_name = test_case["pricing_model_name"]
            self.config.num_position_days = test_case["num_position_days"]
            simulator = sim_utils.get_simulator(self.config)
            simulator.add_agents(
                [sim_utils.get_policy(test_case["agent_policy"])(wallet_address=1, budget=self.config.target_liquidity)]
            )
            simulator.run_simulation(liquidate_on_end=False)
            print(
                f"\n\n----\n{test_number=}\n{test_case=}\n"
                f"{simulator.market.market_state=}\n{simulator.agents[1].wallet=}"
            )
            if test_case["agent_policy"] == "single_long":
                assert len(simulator.agents[1].wallet.longs) > 0
            elif test_case["agent_policy"] == "single_short":
                assert len(simulator.agents[1].wallet.shorts) > 0
            else:
                assert False, "Agent policy test only enabled for single_long and single_short"
        output_utils.close_logging()

    def test_open_long(self):
        """Open a long position"""
        # set up some test parameters
        self.config.pricing_model_name = "hyperdrive"
        self.config.target_liquidity = 1e5
        self.config.num_position_days = 180
        agent_policy = "single_long"
        wallet_address = 1
        trade = types.Quantity(amount=100, unit=types.TokenType.BASE)
        # mock the trade using the pricing model
        simulator = sim_utils.get_simulator(self.config)
        pricing_model = hyperdrive_pm.HyperdrivePricingModel()
        expected_result = pricing_model.calc_out_given_in(
            in_=trade,
            market_state=simulator.market.market_state,
            time_remaining=simulator.market.position_duration,
        )
        expected_market_deltas = hyperdrive_market.MarketDeltas(
            d_base_asset=expected_result.market_result.d_base,
            d_bond_asset=expected_result.market_result.d_bonds,
            d_base_buffer=expected_result.market_result.d_bonds,
        )
        expected_agent_deltas = wallet.Wallet(
            address=wallet_address,
            balance=types.Quantity(amount=expected_result.user_result.d_base, unit=types.TokenType.BASE),
            longs={0: wallet.Long(expected_result.user_result.d_bonds)},
            fees_paid=expected_result.breakdown.fee,
        )
        # Execute the trade using the simulator
        policy = sim_utils.get_policy(agent_policy)
        simulator.add_agents([policy(wallet_address=wallet_address, budget=trade.amount)])
        actual_market_deltas, actual_agent_deltas = simulator.market.open_long(
            wallet_address=wallet_address,
            base_amount=trade.amount,
        )
        # check that the deltas are the same
        self.assertEqual(expected_market_deltas, actual_market_deltas, msg="market deltas did not match")
        self.assertEqual(expected_agent_deltas, actual_agent_deltas, msg="agent deltas did not match")

    def test_close_long(self):
        """open a long, then close it"""
        # set up some test parameters
        self.config.pricing_model_name = "hyperdrive"
        self.config.target_liquidity = 1e5
        self.config.num_position_days = 180
        agent_policy = "single_long"
        wallet_address = 1
        trade = types.Quantity(amount=100, unit=types.TokenType.BASE)
        # mock the trade using the pricing model
        simulator = sim_utils.get_simulator(self.config)
        pricing_model = hyperdrive_pm.HyperdrivePricingModel()
        expected_result_open = pricing_model.calc_out_given_in(
            in_=trade,
            market_state=simulator.market.market_state,
            time_remaining=simulator.market.position_duration,
        )
        open_market_deltas = hyperdrive_market.MarketDeltas(
            d_base_asset=expected_result_open.market_result.d_base,
            d_bond_asset=expected_result_open.market_result.d_bonds,
            d_base_buffer=expected_result_open.market_result.d_bonds,
        )
        new_market_state = simulator.market.market_state.copy()
        new_market_state.apply_delta(open_market_deltas)
        expected_result_close = pricing_model.calc_out_given_in(
            in_=types.Quantity(amount=expected_result_open.user_result.d_bonds, unit=types.TokenType.PT),
            market_state=new_market_state,
            time_remaining=simulator.market.position_duration,
        )
        base_volume = simulator.market.calculate_base_volume(
            expected_result_close.market_result.d_base,
            expected_result_open.user_result.d_bonds,
            simulator.market.position_duration.normalized_time,
        )
        close_market_deltas = hyperdrive_market.MarketDeltas(
            d_base_asset=expected_result_close.market_result.d_base,
            d_bond_asset=expected_result_close.market_result.d_bonds,
            d_base_buffer=expected_result_close.market_result.d_bonds,
            long_base_volume=-base_volume,
        )
        close_agent_deltas = wallet.Wallet(
            address=wallet_address,
            balance=types.Quantity(amount=expected_result_close.user_result.d_base, unit=types.TokenType.BASE),
            longs={0: wallet.Long(expected_result_close.user_result.d_bonds)},
            fees_paid=expected_result_close.breakdown.fee,
        )
        # Execute the trade using the simulator
        policy = sim_utils.get_policy(agent_policy)
        simulator.add_agents([policy(wallet_address=wallet_address, budget=trade.amount)])
        actual_market_deltas, actual_agent_deltas = simulator.market.open_long(
            wallet_address=wallet_address,
            base_amount=trade.amount,
        )
        simulator.market.market_state.apply_delta(actual_market_deltas)
        simulator.agents[1].update_wallet(actual_agent_deltas)
        # peek inside the agent's wallet and see how many bonds they have
        amount_of_bonds_purchased = actual_agent_deltas.longs[0].balance
        # sell those bonds to close the long
        actual_market_deltas, actual_agent_deltas = simulator.market.close_long(
            mint_time=0,
            wallet_address=wallet_address,
            # in bonds: that's the thing in your wallet you want to sell
            bond_amount=amount_of_bonds_purchased,
        )
        # check that the deltas are the same
        self.assertEqual(
            close_market_deltas,
            actual_market_deltas,
            msg=f"\n\n{close_market_deltas=}\n----\n{actual_market_deltas=}\nmarket deltas did not match",
        )
        self.assertEqual(close_agent_deltas, actual_agent_deltas, msg="agent deltas did not match")

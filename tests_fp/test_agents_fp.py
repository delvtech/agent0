"""Unit tests for the core Agent API"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest
from dataclasses import dataclass
from importlib import import_module
from os import path, walk

import numpy as np

import elfpy.agents.agent as agent
import elfpy.agents.policies as policies
import elfpy.agents.wallet as wallet
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time
import elfpy.types as types
from elfpy.agents.get_wallet_state import get_wallet_state_fp
from elfpy.utils.math import FixedPoint


# class TestPolicy(agent.Agent):
#    """This class was made for testing purposes. It does not implement the required self.action() method"""
#
#    def __init__(self, wallet_address, budget=1000):
#        """call basic policy init then add custom stuff"""
#        super().__init__(wallet_address, budget)
#        # TODO: mock up a wallet that has done trades
#
#    def action(self, market):
#        pass
#
#    __test__ = False  # pytest: don't test this class
#
#
# @dataclass
# class TestCaseGetMax:
#    """Test case for get_max_long and get_max_short tests"""
#
#    market_state: hyperdrive_market.MarketState
#    time_remaining: time.StretchedTime
#
#    __test__ = False  # pytest: don't test this class
#
#
# class TestAgent(unittest.TestCase):
#    """Unit tests for the core Agent API"""
#
#    def setUp(self):
#        """Set up a list of agents for testing"""
#        # Get a list of all implemented agent policies in elfpy/policies directory
#        policies_path = f"{list(policies.__path__)[0]}"
#        filenames = next(walk(policies_path), (None, None, []))[2]
#        agent_policies = [path.splitext(filename)[0] for filename in filenames if "__init__" not in filename]
#        # Instantiate an agent for each policy
#        self.agent_list: list[agent.AgentFP] = []
#        for agent_id, policy_name in enumerate(agent_policies):
#            if policy_name == "random_agent":
#                example_agent = import_module(f"elfpy.agents.policies.{policy_name}").Policy(
#                    rng=np.random.default_rng(seed=1234),
#                    trade_chance=1.0,
#                    wallet_address=agent_id,
#                    budget=1_000,
#                )
#            else:
#                example_agent = import_module(f"elfpy.agents.policies.{policy_name}").Policy(
#                    wallet_address=agent_id, budget=1_000
#                )
#            self.agent_list.append(example_agent)
#        # One more test agent that uses a test policy
#        self.test_agent = TestPolicy(wallet_address=len(agent_policies))
#        # Get a mock Market
#        self.market = hyperdrive_market.MarketFP(
#            pricing_model=hyperdrive_pm.HyperdrivePricingModelFP(),
#            market_state=hyperdrive_market.MarketStateFP(),
#            position_duration=time.StretchedTimeFP(
#                days=FixedPoint("365.0"), time_stretch=FixedPoint("10.0"), normalizing_constant=FixedPoint("365.0")
#            ),
#            block_time=time.BlockTimeFP(),
#        )
#        self.market.initialize(wallet_address=0, contribution=FixedPoint("1_000_000.0"), target_apr=FixedPoint("0.01"))
#
#    def test_wallet_state_matches_state_keys(self):
#        """Tests that an agent wallet has the right keys"""
#        for get_state_key, state_key in zip(
#            self.test_agent.wallet.get_state_keys(), get_wallet_state_fp(self.test_agent.wallet, self.market).keys()
#        ):
#            assert get_state_key == state_key, f"ERROR: {get_state_key=} did not equal {state_key=}"
#
#    def test_wallet_copy(self):
#        """Test the wallet ability to deep copy itself"""
#        example_wallet = wallet.WalletFP(
#            address=0, balance=types.QuantityFP(amount=FixedPoint("100.0"), unit=types.TokenType.BASE)
#        )
#        wallet_copy = example_wallet.copy()
#        assert example_wallet is not wallet_copy  # not the same object
#        assert example_wallet == wallet_copy  # they have the same attribute values
#        wallet_copy.address += 1
#        assert example_wallet != wallet_copy  # now they should have different attribute values
#
#    def test_wallet_update(self):
#        """Test that the wallet updates correctly & does not use references to the deltas argument"""
#        example_wallet = wallet.WalletFP(
#            address=0, balance=types.QuantityFP(amount=FixedPoint("100.0"), unit=types.TokenType.BASE)
#        )
#        example_deltas = wallet.WalletFP(
#            address=0,
#            balance=types.QuantityFP(amount=FixedPoint("-10.0"), unit=types.TokenType.BASE),
#            longs={0: wallet.LongFP(FixedPoint("15.0"))},
#            fees_paid=FixedPoint("0.001"),
#        )
#        example_wallet.update(example_deltas)
#        assert id(example_wallet.longs[0]) != id(example_deltas.longs[0]), (
#            f"{example_wallet.longs=} should not hold a reference to {example_deltas.longs=},"
#            f"but have the same ids: {id(example_wallet.longs[0])=}, {id(example_deltas.longs[0])=}."
#        )
#        assert example_wallet.longs[0].balance == FixedPoint(
#            "15.0"
#        ), f"{example_wallet.longs[0].balance=} should equal the delta amount, 15."
#        assert example_wallet.balance.amount == FixedPoint(
#            "90.0"
#        ), f"{example_wallet.balance.amount=} should be 100-10=90."
#        new_example_deltas = wallet.WalletFP(
#            address=0,
#            balance=types.QuantityFP(amount=FixedPoint("-5.0"), unit=types.TokenType.BASE),
#            longs={0: wallet.LongFP(FixedPoint("8"))},
#            fees_paid=FixedPoint("0.0008"),
#        )
#        example_wallet.update(new_example_deltas)
#        assert example_wallet.longs[0].balance == FixedPoint(
#            "23.0"
#        ), f"{example_wallet.longs[0].balance=} should equal 15+8=23."
#        assert example_wallet.balance.amount == FixedPoint(
#            "85.0"
#        ), f"{example_wallet.balance.amount=} should be 100-10-5=85."
#        assert example_deltas.longs[0].balance == FixedPoint(
#            "15.0"
#        ), f"{example_deltas.longs[0].balance=} should be unchanged and equal 15."
#
#    # Test agent instantiation
#    def test_no_action_failure(self):
#        """Tests for Agent instantiation when no action function was defined"""
#
#        class TestErrorPolicy(agent.Agent):
#            """This class was made for testing purposes. It does not implement the required self.action() method"""
#
#            # Purposefully incorrectly implemented
#            ### pylint: disable=abstract-method
#
#            def __init__(self, wallet_address, budget=1000):
#                """call basic policy init then add custom stuff"""
#                super().__init__(wallet_address, budget)
#
#            # self.action() method is intentionally not implemented, so we can test error behavior
#
#            __test__ = False  # pytest: don't test this class
#
#        # Instantiate a wrongly implemented agent policy
#        example_agent = TestErrorPolicy(wallet_address=1)
#        with self.assertRaises(NotImplementedError):
#            example_agent.action(self.market)
#
#    def test_policy_action(self):
#        """Test for calling the action() method on all implemented policies
#        A check to ensure the implemented action() doesn't call for invalid trades
#        """
#        # instantiate the market
#        # Instantiate an agent for each policy, with a variety of budgets
#        budget_list = [10.0, 100.0, 1_000.0]
#        for agent_budget in budget_list:
#            for example_agent in self.agent_list:
#                example_agent.budget = agent_budget
#                if hasattr(example_agent, "amount_to_trade"):
#                    setattr(example_agent, "amount_to_trade", agent_budget)
#                example_agent.wallet.balance = types.QuantityFP(
#                    amount=FixedPoint(str(agent_budget)), unit=types.TokenType.BASE
#                )
#                # For each agent policy, call their action() method
#                actions_list = example_agent.get_trades(self.market)
#                for market_action in actions_list:
#                    # Ensure trade size is smaller than wallet size
#                    self.assertGreaterEqual(
#                        example_agent.budget,
#                        market_action.trade.trade_amount,
#                        msg=f"{market_action.trade.trade_amount=} should be <= {example_agent.budget=}",
#                    )
#

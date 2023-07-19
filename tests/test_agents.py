"""Unit tests for the core Agent API"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest
from dataclasses import dataclass
from os import path, walk

import numpy as np
from fixedpointmath import FixedPoint

import elfpy.agents.policies as policies
import elfpy.time as time
import elfpy.types as types
from elfpy.agents.agent import Agent
from elfpy.agents.get_wallet_state import get_wallet_state
from elfpy.agents.policies import (
    InitializeLiquidityAgent,
    LongLouie,
    LpAndWithdrawAgent,
    NoActionPolicy,
    RandomAgent,
    ShortSally,
    SingleLongAgent,
    SingleLpAgent,
    SingleShortAgent,
)
from elfpy.agents.policies.base import BasePolicy
from elfpy.markets.hyperdrive import HyperdriveMarket, HyperdriveMarketState, HyperdrivePricingModel
from elfpy.wallet.wallet import Long, Wallet
from elfpy.wallet.wallet_deltas import WalletDeltas

# pylint: disable=too-few-public-methods


class TestPolicy(BasePolicy):
    """This class was made for testing purposes. It does not implement the required self.action() method"""

    def __init__(self, budget: FixedPoint = FixedPoint("1000.0")):
        """call basic policy init then add custom stuff"""
        super().__init__(budget, rng=None)
        # TODO: mock up a wallet that has done trades

    def action(self, market, wallet):
        pass

    __test__ = False  # pytest: don't test this class


@dataclass
class TestCaseGetMax:
    """Test case for get_max_long and get_max_short tests"""

    market_state: HyperdriveMarketState
    time_remaining: time.StretchedTime

    __test__ = False  # pytest: don't test this class


class TestAgent(unittest.TestCase):
    """Unit tests for the core Agent API"""

    def setUp(self):
        """Set up a list of agents for testing"""
        # Get a list of all implemented agent policies in elfpy/policies directory
        policies_path = f"{list(policies.__path__)[0]}"
        filenames = next(walk(policies_path), (None, None, []))[2]
        agent_policies = [path.splitext(filename)[0] for filename in filenames if "__init__" not in filename]
        # Instantiate an agent for each policy
        self.agent_list: list[Agent] = []
        for agent_id, policy_name in enumerate(agent_policies):
            if policy_name == "random_agent":
                example_agent = Agent(
                    wallet_address=agent_id,
                    policy=RandomAgent(
                        budget=FixedPoint("1_000.0"),
                        rng=np.random.default_rng(seed=1234),
                        trade_chance=FixedPoint("1.0"),
                    ),
                )
            elif policy_name == "lp_and_withdraw":
                example_agent = Agent(
                    wallet_address=agent_id,
                    policy=LpAndWithdrawAgent(
                        budget=FixedPoint("1_000.0"),
                    ),
                )
            elif policy_name == "single_long":
                example_agent = Agent(
                    wallet_address=agent_id,
                    policy=SingleLongAgent(
                        budget=FixedPoint("1_000.0"),
                    ),
                )
            elif policy_name == "single_short":
                example_agent = Agent(
                    wallet_address=agent_id,
                    policy=SingleShortAgent(
                        budget=FixedPoint("1_000.0"),
                    ),
                )
            elif policy_name == "smart_long":
                example_agent = Agent(
                    wallet_address=agent_id,
                    policy=LongLouie(
                        budget=FixedPoint("1_000.0"),
                        rng=np.random.default_rng(seed=1234),
                        trade_chance=FixedPoint("1.0"),
                        risk_threshold=FixedPoint("1.0"),
                    ),
                )
            elif policy_name == "smart_short":
                example_agent = Agent(
                    wallet_address=agent_id,
                    policy=ShortSally(
                        budget=FixedPoint("1_000.0"),
                        rng=np.random.default_rng(seed=1234),
                        trade_chance=FixedPoint("1.0"),
                        risk_threshold=FixedPoint("1.0"),
                    ),
                )
            elif policy_name == "single_lp":
                example_agent = Agent(
                    wallet_address=agent_id,
                    policy=SingleLpAgent(
                        budget=FixedPoint("1_000.0"),
                    ),
                )
            elif policy_name == "init_lp":
                example_agent = Agent(
                    wallet_address=agent_id,
                    policy=InitializeLiquidityAgent(
                        budget=FixedPoint("1_000.0"),
                    ),
                )
            elif policy_name == "no_action":
                example_agent = Agent(
                    wallet_address=agent_id,
                    policy=NoActionPolicy(
                        budget=FixedPoint("1_000.0"),
                    ),
                )
            elif policy_name == "base":
                continue
            else:
                raise ValueError(f"agent type {policy_name} not supported")
            self.agent_list.append(example_agent)
        # One more test agent that uses a test policy
        self.test_agent = Agent(wallet_address=len(agent_policies), policy=TestPolicy())
        # Get a mock Market
        self.market = HyperdriveMarket(
            pricing_model=HyperdrivePricingModel(),
            market_state=HyperdriveMarketState(),
            position_duration=time.StretchedTime(
                days=FixedPoint("365.0"), time_stretch=FixedPoint("10.0"), normalizing_constant=FixedPoint("365.0")
            ),
            block_time=time.BlockTime(),
        )
        self.market.initialize(contribution=FixedPoint("1_000_000.0"), target_apr=FixedPoint("0.01"))

    def test_wallet_state_matches_state_keys(self):
        """Tests that an agent wallet has the right keys"""
        for get_state_key, state_key in zip(
            self.test_agent.wallet.get_state_keys(), get_wallet_state(self.test_agent.wallet, self.market).keys()
        ):
            assert get_state_key == state_key, f"ERROR: {get_state_key=} did not equal {state_key=}"

    def test_wallet_copy(self):
        """Test the wallet ability to deep copy itself"""
        example_wallet = Wallet(
            address=0, balance=types.Quantity(amount=FixedPoint("100.0"), unit=types.TokenType.BASE)
        )
        wallet_copy = example_wallet.copy()
        assert example_wallet is not wallet_copy  # not the same object
        assert example_wallet == wallet_copy  # they have the same attribute values
        wallet_copy.address += 1
        assert example_wallet != wallet_copy  # now they should have different attribute values

    def test_wallet_update(self):
        """Test that the wallet updates correctly & does not use references to the deltas argument"""
        example_wallet = Wallet(
            address=0, balance=types.Quantity(amount=FixedPoint("100.0"), unit=types.TokenType.BASE)
        )
        example_deltas = WalletDeltas(
            balance=types.Quantity(amount=FixedPoint("-10.0"), unit=types.TokenType.BASE),
            longs={FixedPoint(0): Long(FixedPoint("15.0"))},
            fees_paid=FixedPoint("0.001"),
        )
        example_wallet.update(example_deltas)
        assert id(example_wallet.longs[FixedPoint(0)]) != id(example_deltas.longs[FixedPoint(0)]), (
            f"{example_wallet.longs=} should not hold a reference to {example_deltas.longs=},"
            f"but have the same ids: {id(example_wallet.longs[FixedPoint(0)])=}, "
            f"{id(example_deltas.longs[FixedPoint(0)])=}."
        )
        assert example_wallet.longs[FixedPoint(0)].balance == FixedPoint(
            "15.0"
        ), f"{example_wallet.longs[FixedPoint(0)].balance=} should equal the delta amount, 15."
        assert example_wallet.balance.amount == FixedPoint(
            "90.0"
        ), f"{example_wallet.balance.amount=} should be 100-10=90."
        new_example_deltas = WalletDeltas(
            balance=types.Quantity(amount=FixedPoint("-5.0"), unit=types.TokenType.BASE),
            longs={FixedPoint(0): Long(FixedPoint("8.0"))},
            fees_paid=FixedPoint("0.0008"),
        )
        example_wallet.update(new_example_deltas)
        assert example_wallet.longs[FixedPoint(0)].balance == FixedPoint(
            "23.0"
        ), f"{example_wallet.longs[FixedPoint(0)].balance=} should equal 15+8=23."
        assert example_wallet.balance.amount == FixedPoint(
            "85.0"
        ), f"{example_wallet.balance.amount=} should be 100-10-5=85."
        assert example_deltas.longs[FixedPoint(0)].balance == FixedPoint(
            "15.0"
        ), f"{example_deltas.longs[FixedPoint(0)].balance=} should be unchanged and equal 15."

    # Test agent instantiation
    def test_no_action_failure(self):
        """Tests for Agent instantiation when no action function was defined"""

        class TestErrorPolicy(BasePolicy):
            """This class was made for testing purposes. It does not implement the required self.action() method"""

            # Purposefully incorrectly implemented
            ### pylint: disable=abstract-method

            def __init__(self, budget: FixedPoint = FixedPoint(1000)):
                """call basic policy init then add custom stuff"""
                super().__init__(budget, rng=None)

            # self.action() method is intentionally not implemented, so we can test error behavior

            __test__ = False  # pytest: don't test this class

        # Instantiate a wrongly implemented agent policy
        example_agent = Agent(wallet_address=1, policy=TestErrorPolicy())
        with self.assertRaises(NotImplementedError):
            example_agent.policy.action(self.market, example_agent.wallet)

    @unittest.skip("Skipping this test until parity efforts resume (issue #693)")
    def test_policy_action(self):
        """Test for calling the action() method on all implemented policies

        A check to ensure the implemented action() doesn't call for invalid trades
        """
        # instantiate the market
        # Instantiate an agent for each policy, with a variety of budgets
        budget_list = [FixedPoint("10.0"), FixedPoint("100.0"), FixedPoint("1_000.0")]
        for agent_budget in budget_list:
            for example_agent in self.agent_list:
                example_agent.policy.budget = agent_budget
                if hasattr(example_agent, "amount_to_trade"):
                    setattr(example_agent, "amount_to_trade", agent_budget)
                example_agent.wallet.balance = types.Quantity(
                    amount=FixedPoint(str(agent_budget)), unit=types.TokenType.BASE
                )
                # For each agent policy, call their action() method
                actions_list = example_agent.get_trades(self.market)
                for market_action in actions_list:
                    # Ensure trade size is smaller than wallet size
                    self.assertGreaterEqual(
                        example_agent.policy.budget,
                        market_action.trade.trade_amount,
                        msg=f"{market_action.trade.trade_amount=} should be <= {example_agent.policy.budget=}",
                    )

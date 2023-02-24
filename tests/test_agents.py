"""Unit tests for the core Agent API"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest
from dataclasses import dataclass
from importlib import import_module
from os import walk, path

import numpy as np

import utils_for_tests as test_utils  # utilities for testing

import elfpy.agents.policies as policies
import elfpy.agents.agent as agent
import elfpy.types as types
import elfpy.simulators as simulators
import elfpy.time as time
import elfpy.markets.hyperdrive as hyperdrive
import elfpy.markets.pricing_models.base_pm as base_pm
import elfpy.markets.pricing_models.yieldspace_pm as yieldspace_pm
import elfpy.markets.pricing_models.hyperdrive_pm as hyperdrive_pm


class TestErrorPolicy(agent.Agent):
    """This class was made for testing purposes. It does not implement the required self.action() method"""

    # Purposefully incorrectly implemented
    ### pylint: disable=abstract-method

    def __init__(self, wallet_address, budget=1000):
        """call basic policy init then add custom stuff"""
        super().__init__(wallet_address, budget)
        self.amount_to_spend = 500

    # self.action() method is intentionally not implemented, so we can test error behavior

    __test__ = False  # pytest: don't test this class


@dataclass
class TestCaseGetMax:
    """Test case for get_max_long and get_max_short tests"""

    market_state: hyperdrive.MarketState
    time_remaining: time.utils.StretchedTime

    __test__ = False  # pytest: don't test this class


class TestAgent(unittest.TestCase):
    """Unit tests for the core Agent API"""

    @staticmethod
    def setup_market() -> hyperdrive.HyperdriveMarket:
        """Instantiates a market object for testing purposes"""
        # Give an initial market state
        pricing_model = hyperdrive_pm.HyperdrivePricingModel()
        market_state = hyperdrive.MarketState(
            share_reserves=1_000_000,
            bond_reserves=1_000_000,
            base_buffer=0,
            bond_buffer=0,
            init_share_price=1,
            share_price=1,
            trade_fee_percent=0.1,
            redemption_fee_percent=0.1,
        )
        time_remaining = time.utils.StretchedTime(
            days=365, time_stretch=pricing_model.calc_time_stretch(0.05), normalizing_constant=365
        )
        # NOTE: lint error false positives: This message may report object members that are created dynamically,
        # but exist at the time they are accessed.
        time_remaining.freeze()  # pylint: disable=no-member # type: ignore
        market = hyperdrive.HyperdriveMarket(
            pricing_model=pricing_model,
            market_state=market_state,
            position_duration=time_remaining,
        )
        return market

    @staticmethod
    def get_implemented_policies() -> list[str]:
        """Get a list of all implemented agent policies in elfpy/policies directory"""
        policies_path = f"{list(policies.__path__)[0]}/policies"
        filenames = next(walk(policies_path), (None, None, []))[2]
        agent_policies = [path.splitext(filename)[0] for filename in filenames]
        return agent_policies

    def test_wallet_keys(self):
        """Tests that an agent wallet has the right keys"""
        # get the list of policies in the elfpy/policies directory
        agent_policies = self.get_implemented_policies()
        # setup a simulation environment
        simulator = test_utils.setup_simulation_entities(simulators.Config(), agent_policies)
        simulator.collect_and_execute_trades()
        for my_agent in simulator.agents.values():
            wallet_state = my_agent.wallet.get_state(simulator.market)
            wallet_keys = my_agent.wallet.get_state_keys()
            assert np.all(list(wallet_state.keys()) == wallet_keys)

    def test_get_max_safety(self):
        """
        Ensures that get_max_long and get_max_short will not exceed the balance
        of an agent in a variety of market conditions.
        """
        models: list[base_pm.PricingModel] = [
            hyperdrive_pm.HyperdrivePricingModel(),
            yieldspace_pm.YieldSpacePricingModel(),
        ]

        test_cases: list[TestCaseGetMax] = [
            TestCaseGetMax(
                market_state=hyperdrive.MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1,
                    share_price=1,
                    trade_fee_percent=0.1,
                ),
                time_remaining=time.utils.StretchedTime(
                    days=365, time_stretch=models[0].calc_time_stretch(0.05), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=hyperdrive.MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=100_000,
                    bond_buffer=100_000,
                    init_share_price=1,
                    share_price=1,
                    trade_fee_percent=0.1,
                ),
                time_remaining=time.utils.StretchedTime(
                    days=365, time_stretch=models[0].calc_time_stretch(0.05), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=hyperdrive.MarketState(
                    share_reserves=100_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1,
                    share_price=1,
                    trade_fee_percent=0.1,
                ),
                time_remaining=time.utils.StretchedTime(
                    days=365, time_stretch=models[0].calc_time_stretch(0.05), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=hyperdrive.MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=100_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1,
                    share_price=1,
                    trade_fee_percent=0.1,
                ),
                time_remaining=time.utils.StretchedTime(
                    days=365, time_stretch=models[0].calc_time_stretch(0.05), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=hyperdrive.MarketState(
                    share_reserves=500_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                    trade_fee_percent=0.1,
                ),
                time_remaining=time.utils.StretchedTime(
                    days=365, time_stretch=models[0].calc_time_stretch(0.05), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=hyperdrive.MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                    trade_fee_percent=0.1,
                ),
                time_remaining=time.utils.StretchedTime(
                    days=365, time_stretch=models[0].calc_time_stretch(0.05), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=hyperdrive.MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                    trade_fee_percent=0.5,
                ),
                time_remaining=time.utils.StretchedTime(
                    days=365, time_stretch=models[0].calc_time_stretch(0.05), normalizing_constant=365
                ),
            ),
            TestCaseGetMax(
                market_state=hyperdrive.MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                    trade_fee_percent=0.1,
                ),
                time_remaining=time.utils.StretchedTime(
                    days=91, time_stretch=models[0].calc_time_stretch(0.05), normalizing_constant=91
                ),
            ),
            TestCaseGetMax(
                market_state=hyperdrive.MarketState(
                    share_reserves=1_000_000,
                    bond_reserves=1_000_000,
                    base_buffer=0,
                    bond_buffer=0,
                    init_share_price=1.5,
                    share_price=2,
                    trade_fee_percent=0.1,
                ),
                time_remaining=time.utils.StretchedTime(
                    days=91, time_stretch=models[0].calc_time_stretch(0.25), normalizing_constant=91
                ),
            ),
        ]
        for test_case in test_cases:
            for pricing_model in models:
                market = hyperdrive.HyperdriveMarket(
                    pricing_model=pricing_model,
                    market_state=test_case.market_state,
                    position_duration=test_case.time_remaining,
                )
                # Ensure safety for Agents with different budgets.
                for budget in (1e-3 * 10 ** (3 * x) for x in range(5)):
                    my_agent = agent.Agent(wallet_address=0, budget=budget)
                    # Ensure that get_max_long is safe.
                    max_long = market.get_max_long(my_agent.wallet)
                    self.assertGreaterEqual(my_agent.wallet.balance.amount, max_long)
                    (market_max_long, _) = market.pricing_model.get_max_long(
                        market_state=market.market_state,
                        time_remaining=market.position_duration,
                    )
                    self.assertLessEqual(
                        max_long,
                        market_max_long,
                    )
                    # Ensure that get_max_short is safe.
                    max_short = market.get_max_short(my_agent.wallet)
                    trade_result = market.pricing_model.calc_out_given_in(
                        in_=types.Quantity(amount=max_short, unit=types.TokenType.PT),
                        market_state=market.market_state,
                        time_remaining=market.position_duration,
                    )
                    max_loss = max_short - trade_result.user_result.d_base
                    self.assertGreaterEqual(my_agent.wallet.balance.amount, max_loss)
                    (_, market_max_short) = market.pricing_model.get_max_short(
                        market_state=market.market_state,
                        time_remaining=market.position_duration,
                    )
                    self.assertLessEqual(
                        max_short,
                        market_max_short,
                    )

    # Test agent instantiation
    def test_init(self):
        """Tests for Agent instantiation"""
        # Instantiate a test market
        market = self.setup_market()
        # Instantiate a wrongly implemented agent policy
        my_agent = TestErrorPolicy(wallet_address=1)
        with self.assertRaises(NotImplementedError):
            my_agent.action(market)
        # Get the list of policies in the elfpy/policies directory
        agent_policies = self.get_implemented_policies()
        # Instantiate an agent for each policy
        agent_list = []
        for agent_id, policy_name in enumerate(agent_policies):
            wallet_address = agent_id
            agent_list.extend(
                import_module(f"elfpy.policies.{policy_name}").Policy(
                    wallet_address=wallet_address,  # first policy goes to init_lp_agent
                )
            )

    def test_action(self):
        """
        Test for calling the action() method on all implemented policies

        Does a basic check to ensure the implemented action() doesn't call for
        invalid trades
        """
        # instantiate the market
        market = self.setup_market()
        # Get the list of policies in the elfpy/policies directory
        agent_policies = self.get_implemented_policies()
        # Instantiate an agent for each policy, with a variety of budgets
        budget_list = [10, 1_000, 1_000_000, 100_000_000]
        agent_list = []
        for agent_budget in budget_list:
            for agent_id, policy_name in enumerate(agent_policies):
                wallet_address = agent_id
                agent_list.extend(
                    import_module(f"elfpy.policies.{policy_name}").Policy(
                        wallet_address=wallet_address, budget=agent_budget
                    )
                )
        # For each agent policy, call their action() method
        for my_agent in agent_list:
            actions_list = my_agent.get_trade_list(market)
            for market_action in actions_list:
                # Ensure trade size is smaller than wallet size
                self.assertGreaterEqual(market_action.trade_amount, my_agent.budget)

    def test_wallet_state(self):
        """Tests for Agent wallet state initialization"""
        # Get the list of policies in the elfpy/policies directory
        agent_policies = self.get_implemented_policies()
        # Instantiate an agent for each policy
        agent_list = []
        for agent_id, policy_name in enumerate(agent_policies):
            wallet_address = agent_id
            agent_list.extend(
                import_module(f"elfpy.policies.{policy_name}").Policy(
                    wallet_address=wallet_address,  # first policy goes to init_lp_agent
                )
            )
        for my_agent in agent_list:
            expected_keys = [
                f"agent_{my_agent.address}_base",
                f"agent_{my_agent.address}_lp_tokens",
                f"agent_{my_agent.address}_total_longs",
                f"agent_{my_agent.address}_total_shorts",
            ]
            assert expected_keys == list(my_agent.wallet.state)

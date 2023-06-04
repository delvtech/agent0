"""Fixtures for elfpy & solidity agents"""
import ape
import pytest
from ape.api.accounts import TestAccountAPI

from elfpy.agents.agent import Agent
from elfpy.math.fixed_point import FixedPoint

# pylint: disable=redefined-outer-name


class PythonAgents:
    """Python Agents Type"""

    def __init__(self, alice: Agent, bob: Agent, celine: Agent):
        self.alice = alice
        self.bob = bob
        self.celine = celine


class SolidityAgents:
    """Solidity Agents Type"""

    def __init__(self, alice: TestAccountAPI, bob: TestAccountAPI, celine: TestAccountAPI):
        self.alice = alice
        self.bob = bob
        self.celine = celine


class Agents:
    """Agents Type"""

    def __init__(self, solidity_agents: SolidityAgents, python_agents: PythonAgents):
        self.solidity = solidity_agents
        self.python = python_agents


@pytest.fixture(scope="function")
def python_agents() -> PythonAgents:
    """Returns some python agents initialized with some budget"""
    budget: FixedPoint = FixedPoint("50_000_000.0")

    alice = Agent(wallet_address=0, budget=budget)
    bob = Agent(wallet_address=1, budget=budget)
    celine = Agent(wallet_address=2, budget=budget)

    return PythonAgents(alice, bob, celine)


@pytest.fixture(scope="function")
def solidity_agents(deployer: TestAccountAPI):
    """Returns solidity agents initialized with some ETH"""
    budget: FixedPoint = FixedPoint("50_000_000.0")

    alice = ape.accounts.test_accounts.generate_test_account()
    bob = ape.accounts.test_accounts.generate_test_account()
    celine = ape.accounts.test_accounts.generate_test_account()

    deployer.provider.set_balance(alice.address, budget.scaled_value)
    deployer.provider.set_balance(bob.address, budget.scaled_value)
    deployer.provider.set_balance(celine.address, budget.scaled_value)

    return SolidityAgents(alice, bob, celine)


@pytest.fixture(scope="function")
def agents(python_agents: PythonAgents, solidity_agents: SolidityAgents):
    """Returns python and solidity agents."""
    return Agents(solidity_agents, python_agents)

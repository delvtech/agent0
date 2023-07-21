"""Fixtures for elfpy & solidity agents"""
from __future__ import annotations

from dataclasses import dataclass

# TODO: convert to not use ape
__test__ = False

import ape
import pytest
from ape.api.accounts import TestAccountAPI
from fixedpointmath import FixedPoint

from elfpy.agents.agent import Agent

# pylint: disable=redefined-outer-name


@dataclass
class PythonAgents:
    """Python Agents Type"""

    alice: Agent
    bob: Agent
    celine: Agent


@dataclass
class SolidityAgents:
    """Solidity Agents Type"""

    alice: TestAccountAPI
    bob: TestAccountAPI
    celine: TestAccountAPI


@dataclass
class Agents:
    """Agents Type"""

    solidity: SolidityAgents
    python: PythonAgents


@pytest.fixture(scope="function")
def python_agents() -> PythonAgents:
    """Returns some python agents initialized with some budget"""
    alice = Agent(wallet_address=0)
    bob = Agent(wallet_address=1)
    celine = Agent(wallet_address=2)

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

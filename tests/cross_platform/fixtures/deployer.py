"""Deployer fixture"""
import ape
import pytest
from ape.api.accounts import TestAccountAPI
from fixedpointmath import FixedPoint

# TODO: convert to not use ape
__test__ = False

@pytest.fixture(scope="function")
def deployer() -> TestAccountAPI:
    """Returns solidity agents initialized with some ETH"""
    budget: FixedPoint = FixedPoint("50_000_000.0")
    agent_deployer = ape.accounts.test_accounts.generate_test_account()
    agent_deployer.provider.set_balance(agent_deployer.address, budget.scaled_value)
    return agent_deployer

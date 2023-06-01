"""Deployer fixture"""
import ape
from ape.api.accounts import TestAccountAPI
import pytest

from elfpy.math.fixed_point import FixedPoint


@pytest.fixture(scope="function")
def deployer() -> TestAccountAPI:
    """Returns solidity agents initialized with some ETH"""
    budget: FixedPoint = FixedPoint("50_000_000.0")
    agent_deployer = ape.accounts.test_accounts.generate_test_account()
    agent_deployer.provider.set_balance(agent_deployer.address, int(budget))
    return agent_deployer

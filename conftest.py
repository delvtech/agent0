"""Fixtures for cross-platform tests."""
from __future__ import annotations

import unittest

import ape
import pytest
from ape.api.accounts import TestAccountAPI
from ape.api.providers import ProviderAPI
from ape.managers.project import ProjectManager

from elfpy.markets.hyperdrive.hyperdrive_market import Market as HyperdriveMarket
from elfpy.math.fixed_point import FixedPoint
from tests.cross_platform import fixtures

# load all fixtures, this can only be done in a root level conftest.py file.
pytest_plugins = [
    "tests.cross_platform.fixtures.agents",
    "tests.cross_platform.fixtures.base_erc20",
    "tests.cross_platform.fixtures.contracts",
    "tests.cross_platform.fixtures.deployer",
    "tests.cross_platform.fixtures.fixed_math_contract",
    "tests.cross_platform.fixtures.hyperdrive_config",
    "tests.cross_platform.fixtures.hyperdrive_sim",
    "tests.cross_platform.fixtures.project",
    "tests.cross_platform.fixtures.provider",
]


class HyperdriveFixture:
    "Fixture Type"

    def __init__(
        self,
        config: fixtures.HyperdriveConfig,
        project: ProjectManager,
        provider: ProviderAPI,
        deployer: TestAccountAPI,
        agents: fixtures.Agents,
        contracts: fixtures.Contracts,
        hyperdrive_sim: HyperdriveMarket,
    ):
        self.config = config
        self.project = project
        self.provider = provider
        self.agents = agents
        self.deployer = deployer
        self.contracts = contracts
        self.genesis_block_number = ape.chain.blocks[-1].number
        self.genesis_timestamp = ape.chain.provider.get_block(self.genesis_block_number).timestamp  # type:ignore
        self.hyperdrive_sim = hyperdrive_sim


@pytest.fixture(scope="function")
def hyperdrive_fixture(
    hyperdrive_config: fixtures.HyperdriveConfig,
    project: ProjectManager,
    provider: ProviderAPI,
    agents: fixtures.Agents,
    deployer: TestAccountAPI,
    contracts: fixtures.Contracts,
    hyperdrive_sim: HyperdriveMarket,
):
    """Adds the fixture dictionary"""

    fixture: HyperdriveFixture = HyperdriveFixture(
        hyperdrive_config, project, provider, deployer, agents, contracts, hyperdrive_sim
    )
    return fixture


class TestCaseWithHyperdriveFixture(unittest.TestCase):
    """A Basic fixure for local Cross-Platform testing."""

    fixture: HyperdriveFixture

    def inititalize(self, fixture: HyperdriveFixture | None = None):
        """Initializes the hyperdrive contract and simulation market."""
        if fixture:
            fx = fixture  # pylint: disable=invalid-name
        else:
            fx = self.fixture  # pylint: disable=invalid-name

        # Initialize hyperdrive contract
        with ape.accounts.use_sender(fx.deployer):
            # give some base token to the deployer and approve hyperdrive to take it
            fx.contracts.base_erc20.mint(fx.config.target_liquidity.scaled_value)
            fx.contracts.base_erc20.approve(fx.contracts.hyperdrive_contract, fx.config.target_liquidity.scaled_value)
            # sets the appropriate share and base reserves to create the initial apr, gives deployer lp tokens
            fx.contracts.hyperdrive_contract.initialize(
                fx.config.target_liquidity.scaled_value, fx.config.initial_apr.scaled_value, fx.deployer.address, True
            )

        # initialize hyperdrive simulation market
        fx.hyperdrive_sim.initialize(
            fx.agents.python.alice.wallet.address,
            FixedPoint(fx.config.target_liquidity),
            FixedPoint(fx.config.initial_apr),
        )

    @pytest.fixture(autouse=True)
    # pylint: disable=redefined-outer-name
    def add_fixture(self, hyperdrive_fixture: HyperdriveFixture):
        """Gets the simulation and solidity test fixutres."""
        self.fixture = hyperdrive_fixture

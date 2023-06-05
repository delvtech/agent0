"""Fixtures for cross-platform tests."""
from __future__ import annotations

import unittest

import ape
import pytest
from ape.api.accounts import TestAccountAPI
from ape.api.providers import ProviderAPI
from ape.managers.project import ProjectManager
from attr import dataclass

from elfpy.markets.hyperdrive.hyperdrive_market import HyperdriveMarket
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


@dataclass
class HyperdriveFixture:
    "Fixture Type"

    config: fixtures.HyperdriveConfig
    project: ProjectManager
    provider: ProviderAPI
    deployer: TestAccountAPI
    agents: fixtures.Agents
    contracts: fixtures.Contracts
    hyperdrive_sim: HyperdriveMarket
    genesis_block_number: int
    genesis_timestamp: int


# pylint: disable=too-many-arguments
@pytest.fixture(scope="function")
def hyperdrive_fixture(
    hyperdrive_config: fixtures.HyperdriveConfig,
    project: ProjectManager,
    provider: ProviderAPI,
    agents: fixtures.Agents,
    deployer: TestAccountAPI,
    contracts: fixtures.Contracts,
    hyperdrive_sim: HyperdriveMarket,
) -> HyperdriveFixture:
    """Adds the fixture dictionary"""

    genesis_block_number = ape.chain.blocks[-1].number or 0
    genesis_timestamp = ape.chain.provider.get_block(genesis_block_number).timestamp  # type:ignore
    fixture: HyperdriveFixture = HyperdriveFixture(
        hyperdrive_config,
        project,
        provider,
        deployer,
        agents,
        contracts,
        hyperdrive_sim,
        genesis_block_number,
        genesis_timestamp,
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
            FixedPoint(fx.config.target_liquidity),
            FixedPoint(fx.config.initial_apr),
        )

    @pytest.fixture(autouse=True)
    # pylint: disable=redefined-outer-name
    def add_fixture(self, hyperdrive_fixture: HyperdriveFixture):
        """Gets the simulation and solidity test fixutres."""
        self.fixture = hyperdrive_fixture

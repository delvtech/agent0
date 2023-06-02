"""Fixtures for cross-platform tests."""
import unittest

import ape
import pytest
from ape.api.accounts import TestAccountAPI
from ape.api.providers import ProviderAPI
from ape.managers.project import ProjectManager

from elfpy.markets.hyperdrive.hyperdrive_market import Market as HyperdriveMarket
from elfpy.math.fixed_point import FixedPoint

from tests_fp.cross_platform import fixtures

pytest_plugins = [
    "tests_fp.cross_platform.fixtures.agents",
    "tests_fp.cross_platform.fixtures.base_erc20",
    "tests_fp.cross_platform.fixtures.contracts",
    "tests_fp.cross_platform.fixtures.deployer",
    "tests_fp.cross_platform.fixtures.fixed_math_contract",
    "tests_fp.cross_platform.fixtures.hyperdrive_config",
    "tests_fp.cross_platform.fixtures.hyperdrive_sim",
    "tests_fp.cross_platform.fixtures.project",
    "tests_fp.cross_platform.fixtures.provider",
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

    def inititalize(self, agents: fixtures.Agents):
        """Initializes the hyperdrive contract and simulation market."""
        fx = self.fixture  # pylint: disable=invalid-name

        # give some base token to the deployer
        fx.contracts.base_erc20_contract.mint(fx.config.target_liquidity, sender=fixtures.deployer)  # type: ignore

        # Initialize hyperdrive contract
        with ape.accounts.use_sender(self.fixture.deployer):
            fixtures.base_erc20.mint(fx.config.target_liquidity, sender=fixtures.deployer)
            fixtures.base_erc20.approve(fx.contracts.hyperdrive_contract, fx.config.target_liquidity)
            fixtures.contracts.hyperdrive_contract.initialize(
                fx.config.target_liquidity, fx.config.initial_apr, fixtures.deployer, True
            )

        # initialize hyperdrive simulation market
        self.fixture.hyperdrive_sim.initialize(
            agents.python.alice.wallet.address,
            FixedPoint(self.fixture.config.target_liquidity),
            FixedPoint(self.fixture.config.initial_apr),
        )

    @pytest.fixture(autouse=True)
    # pylint: disable=redefined-outer-name
    def add_fixture(self, hyperdrive_fixture: HyperdriveFixture):
        """Gets the simulation and solidity test fixutres."""
        self.fixture = hyperdrive_fixture

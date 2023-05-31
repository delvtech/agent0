"""Fixtures for cross-platform tests."""
import unittest
from pathlib import Path

import ape
from attr import dataclass
import pytest
from ape.api.accounts import TestAccountAPI
from ape.api.providers import ProviderAPI
from ape.managers.project import ProjectManager
from ape.contracts import ContractInstance

import elfpy.pricing_models.hyperdrive as hyperdrive_pm
from elfpy.agents.agent import AgentFP
from elfpy.markets.hyperdrive import hyperdrive_market
from elfpy.math.fixed_point import FixedPoint
from elfpy.time.time import BlockTimeFP, StretchedTimeFP

# pylint: disable=redefined-outer-name


class PythonAgents:
    """Python Agents Type"""

    def __init__(self, alice: AgentFP, bob: AgentFP, celine: AgentFP):
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

    def __init__(self, solidity: SolidityAgents, python: PythonAgents):
        self.solidity = solidity
        self.python = python


@pytest.fixture(scope="function")
def provider() -> ProviderAPI:
    """Creates the provider for the local blockchain."""
    # This is the prescribed pattern, ignore the pylint warning about using __enter__
    # pylint: disable=unnecessary-dunder-call
    return ape.networks.parse_network_choice("ethereum:local:foundry").__enter__()


@pytest.fixture(scope="function")
def project() -> ProjectManager:
    "Returns the ape project."
    project_root = Path.cwd()
    return ape.Project(path=project_root)


@pytest.fixture(scope="function")
def python_agents() -> PythonAgents:
    """Returns some python agents initialized with some budget"""
    budget: FixedPoint = FixedPoint("50_000_000.0")

    alice = AgentFP(wallet_address=0, budget=budget)
    bob = AgentFP(wallet_address=1, budget=budget)
    celine = AgentFP(wallet_address=2, budget=budget)

    return PythonAgents(alice, bob, celine)


@pytest.fixture(scope="function")
def solidity_agents(deployer: TestAccountAPI):
    """Returns solidity agents initialized with some ETH"""
    budget: FixedPoint = FixedPoint("50_000_000.0")

    alice = ape.accounts.test_accounts.generate_test_account()
    bob = ape.accounts.test_accounts.generate_test_account()
    celine = ape.accounts.test_accounts.generate_test_account()

    deployer.provider.set_balance(alice.address, int(budget))
    deployer.provider.set_balance(bob.address, int(budget))
    deployer.provider.set_balance(celine.address, int(budget))

    return SolidityAgents(alice, bob, celine)


@pytest.fixture(scope="function")
def agents(python_agents: PythonAgents, solidity_agents: SolidityAgents):
    """Returns python and solidity agents."""
    return Agents(solidity_agents, python_agents)


@pytest.fixture(scope="function")
def deployer() -> TestAccountAPI:
    """Returns solidity agents initialized with some ETH"""
    budget: FixedPoint = FixedPoint("50_000_000.0")

    deployer = ape.accounts.test_accounts.generate_test_account()
    deployer.provider.set_balance(deployer.address, int(budget))

    return deployer


@pytest.fixture(scope="function")
def base_erc20(project: ProjectManager, deployer: TestAccountAPI) -> ContractInstance:
    """Deploys the base erc20 contract"""
    # deploy base token contract
    base_erc20 = deployer.deploy(project.ERC20Mintable)  # type: ignore
    return base_erc20


@pytest.fixture(scope="function")
def fixed_math_contract(project: ProjectManager, deployer: TestAccountAPI) -> ContractInstance:
    """Deploys the base erc20 contract"""
    # deploy fixed math contract
    fixed_math = deployer.deploy(project.MockFixedPointMath)  # type: ignore
    return fixed_math


@dataclass
class HyperdriveConfig:
    """Configuration variables to setup hyperdrive fixtures."""

    initial_apr: int = 50000000000000000
    share_price: int = 1000000000000000000
    checkpoint_duration_seconds: int = 86400
    checkpoints: int = 182
    time_stretch: int = 22186877016851913475
    curve_fee: int = 0
    flat_fee: int = 0
    gov_fee: int = 0
    position_duration_seconds: int = checkpoint_duration_seconds * checkpoints
    target_liquidity = 1 * 10**6 * 10**18  # 1M


@pytest.fixture(scope="function")
def hyperdrive_config() -> HyperdriveConfig:
    """Returns a hyperdrive configuration dataclass with default values.  This fixture should be
    overridden as needed in test classes."""
    return HyperdriveConfig()


@pytest.fixture(scope="function")
def hyperdrive_contract(
    project: ProjectManager, hyperdrive_config: HyperdriveConfig, deployer: TestAccountAPI, base_erc20: ContractInstance
) -> ContractInstance:
    """Deploys the base erc20 contract"""

    hc = hyperdrive_config  # pylint: disable=invalid-name

    print(f"{project.MockHyperdriveDataProviderTestnet=}")
    print(f"{base_erc20=}")
    print(f"{hc.initial_apr=}")
    print(f"{hc.share_price=}")
    print(f"{hc.position_duration_seconds=}")
    print(f"{hc.checkpoint_duration_seconds=}")
    print(f"{hc.time_stretch=}")
    print(f"{hc.gov_fee=}")
    print(f"{hc.flat_fee=}")
    print(f"{hc.curve_fee=}")
    hyperdrive_data_provider_contract = deployer.deploy(
        project.MockHyperdriveDataProviderTestnet,  # type: ignore
        base_erc20,
        hc.initial_apr,
        hc.share_price,
        hc.position_duration_seconds,
        hc.checkpoint_duration_seconds,
        hc.time_stretch,
        (hc.curve_fee, hc.flat_fee, hc.gov_fee),
        deployer,
    )

    hyperdrive_contract = deployer.deploy(
        project.MockHyperdriveTestnet,  # type: ignore
        hyperdrive_data_provider_contract,
        base_erc20,
        hc.initial_apr,
        hc.share_price,
        hc.position_duration_seconds,
        hc.checkpoint_duration_seconds,
        hc.time_stretch,
        (hc.curve_fee, hc.flat_fee, hc.gov_fee),
        deployer,
    )

    return hyperdrive_contract


@pytest.fixture(scope="function")
def hyperdrive_data_contract(project: ProjectManager, hyperdrive_contract: ContractInstance) -> ContractInstance:
    """Gets the data provider interface for the hyperdrive contract"""
    hyperdrive_data_contract: ContractInstance = project.MockHyperdriveDataProviderTestnet.at(
        hyperdrive_contract.address
    )  # type: ignore
    return hyperdrive_data_contract


@pytest.fixture(scope="function")
def hyperdrive_sim(hyperdrive_config: HyperdriveConfig) -> hyperdrive_market.MarketFP:
    """Returns an elfpy hyperdrive Market."""
    position_duration_days = FixedPoint(float(hyperdrive_config.position_duration_seconds)) / FixedPoint(
        float(24 * 60 * 60)
    )
    pricing_model = hyperdrive_pm.HyperdrivePricingModelFP()
    position_duration = StretchedTimeFP(
        days=position_duration_days,
        time_stretch=pricing_model.calc_time_stretch(FixedPoint(hyperdrive_config.initial_apr)),
        normalizing_constant=position_duration_days,
    )
    hyperdrive_sim = hyperdrive_market.MarketFP(
        pricing_model=hyperdrive_pm.HyperdrivePricingModelFP(),
        market_state=hyperdrive_market.MarketStateFP(),
        position_duration=position_duration,
        block_time=BlockTimeFP(),
    )
    return hyperdrive_sim


class Contracts:
    "Contracts Type"

    def __init__(
        self,
        base_erc20: ContractInstance,
        hyperdrive_contract: ContractInstance,
        hyperdrive_data_contract: ContractInstance,
        fixed_math_contract: ContractInstance,
    ):
        self.base_erc20 = base_erc20
        self.hyperdrive_contract = hyperdrive_contract
        self.hyperdrive_data_contract = hyperdrive_data_contract
        self.fixed_math_contract = fixed_math_contract


@pytest.fixture(scope="function")
def contracts(
    base_erc20: ContractInstance,
    hyperdrive_contract: ContractInstance,
    hyperdrive_data_contract: ContractInstance,
    fixed_math_contract: ContractInstance,
):
    """Returns a Contracts object."""
    return Contracts(
        base_erc20=base_erc20,
        hyperdrive_contract=hyperdrive_contract,
        hyperdrive_data_contract=hyperdrive_data_contract,
        fixed_math_contract=fixed_math_contract,
    )


class HyperdriveFixture:
    "Fixture Type"

    def __init__(
        self,
        config: HyperdriveConfig,
        project: ProjectManager,
        provider: ProviderAPI,
        deployer: TestAccountAPI,
        agents: Agents,
        contracts: Contracts,
        hyperdrive_sim: hyperdrive_market.MarketFP,
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
    hyperdrive_config: HyperdriveConfig,
    project: ProjectManager,
    provider: ProviderAPI,
    agents: Agents,
    deployer: TestAccountAPI,
    contracts: Contracts,
    hyperdrive_sim: hyperdrive_market.MarketFP,
):
    """Adds the fixture dictionary"""

    fixture: HyperdriveFixture = HyperdriveFixture(
        hyperdrive_config, project, provider, deployer, agents, contracts, hyperdrive_sim
    )
    return fixture


class TestCaseWithHyperdriveFixture(unittest.TestCase):
    """A Basic fixure for local Cross-Platform testing."""

    fixture: HyperdriveFixture

    def inititalize(self):
        """Initializes the hyperdrive contract and simulation market."""
        fx = self.fixture  # pylint: disable=invalid-name

        # give some base token to the deployer
        fx.contracts.base_erc20_contract.mint(fx.config.target_liquidity, sender=deployer)  # type: ignore

        # Initialize hyperdrive contract
        with ape.accounts.use_sender(self.fixture.deployer):
            base_erc20.mint(fx.config.target_liquidity, sender=deployer)
            base_erc20.approve(hyperdrive_contract, fx.config.target_liquidity)
            hyperdrive_contract.initialize(fx.config.target_liquidity, fx.config.initial_apr, deployer, True)

        # initialize hyperdrive simulation market
        self.fixture.hyperdrive_sim.initialize(
            agents.python.alice.wallet.address,
            FixedPoint(self.fixture.config.target_liquidity),
            FixedPoint(self.fixture.config.initial_apr),
        )

    @pytest.fixture(autouse=True)
    def add_fixture(self, hyperdrive_fixture: HyperdriveFixture):
        """Gets the simulation and solidity test fixutres."""
        self.fixture = hyperdrive_fixture

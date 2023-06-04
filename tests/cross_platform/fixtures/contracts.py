"""Fixtures for contracts"""
import pytest
from ape.api.accounts import TestAccountAPI
from ape.contracts import ContractInstance
from ape.managers.project import ProjectManager

from .hyperdrive_config import HyperdriveConfig

# pylint: disable=redefined-outer-name


@pytest.fixture(scope="function")
def hyperdrive_data_contract(project: ProjectManager, hyperdrive_contract: ContractInstance) -> ContractInstance:
    """Gets the data provider interface for the hyperdrive contract"""
    hyperdrive_data_contract: ContractInstance = project.MockHyperdriveDataProviderTestnet.at(
        hyperdrive_contract.address
    )  # type: ignore
    return hyperdrive_data_contract


@pytest.fixture(scope="function")
def hyperdrive_contract(
    project: ProjectManager, hyperdrive_config: HyperdriveConfig, deployer: TestAccountAPI, base_erc20: ContractInstance
) -> ContractInstance:
    """Deploys the base erc20 contract"""
    hyperdrive_data_provider_contract = deployer.deploy(
        project.MockHyperdriveDataProviderTestnet,  # type: ignore
        base_erc20,
        hyperdrive_config.initial_apr.scaled_value,
        hyperdrive_config.share_price.scaled_value,
        hyperdrive_config.position_duration_seconds,
        hyperdrive_config.checkpoint_duration_seconds,
        hyperdrive_config.time_stretch,
        (
            hyperdrive_config.curve_fee.scaled_value,
            hyperdrive_config.flat_fee.scaled_value,
            hyperdrive_config.gov_fee.scaled_value,
        ),
        deployer.address,
    )
    hyperdrive_contract = deployer.deploy(
        project.MockHyperdriveTestnet,  # type: ignore
        hyperdrive_data_provider_contract.address,
        base_erc20,
        hyperdrive_config.initial_apr.scaled_value,
        hyperdrive_config.share_price.scaled_value,
        hyperdrive_config.position_duration_seconds,
        hyperdrive_config.checkpoint_duration_seconds,
        hyperdrive_config.time_stretch,
        (
            hyperdrive_config.curve_fee.scaled_value,
            hyperdrive_config.flat_fee.scaled_value,
            hyperdrive_config.gov_fee.scaled_value,
        ),
        deployer.address,
    )

    return hyperdrive_contract


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

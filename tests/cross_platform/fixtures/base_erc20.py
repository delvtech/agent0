"""Base ERC20 contract fixture"""
from ape.api.accounts import TestAccountAPI
from ape.contracts import ContractInstance
from ape.managers.project import ProjectManager
import pytest

# TODO: convert to not use ape
__test__ = False

@pytest.fixture(scope="function")
def base_erc20(project: ProjectManager, deployer: TestAccountAPI) -> ContractInstance:
    """Deploys the base erc20 contract"""
    deployed_base_erc20 = deployer.deploy(project.ERC20Mintable)  # type: ignore
    return deployed_base_erc20

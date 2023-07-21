"""Solidity fixed-point math contract"""
from ape.api.accounts import TestAccountAPI
from ape.contracts import ContractInstance
from ape.managers.project import ProjectManager
import pytest

# TODO: convert to not use ape
__test__ = False

@pytest.fixture(scope="function")
def fixed_math_contract(project: ProjectManager, deployer: TestAccountAPI) -> ContractInstance:
    """Deploys the base erc20 contract"""
    # deploy fixed math contract
    fixed_math = deployer.deploy(project.MockFixedPointMath)  # type: ignore
    return fixed_math

# pylint: disable=invalid-name
"""A web3.py Contract class for the ERC4626HyperdriveDeployer contract."""
from __future__ import annotations

from typing import Any, cast
from eth_typing import ChecksumAddress
from web3.contract.contract import Contract, ContractFunction, ContractFunctions
from web3.exceptions import FallbackNotFound


class ERC4626HyperdriveDeployerDeployContractFunction(ContractFunction):
    """ContractFunction for the deploy method."""

    def __call__(
        self, PoolConfig: tuple, _dataProvider: str, _linkerCodeHash: bytes, _linkerFactory: str, _extraData: bytes
    ) -> "ERC4626HyperdriveDeployerDeployContractFunction":
        super().__call__(PoolConfig, _dataProvider, _linkerCodeHash, _linkerFactory, _extraData)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveDeployerContractFunctions(ContractFunctions):
    """ContractFunctions for the ERC4626HyperdriveDeployer contract."""

    deploy: ERC4626HyperdriveDeployerDeployContractFunction


class ERC4626HyperdriveDeployerContract(Contract):
    """A web3.py Contract class for the ERC4626HyperdriveDeployer contract."""

    def __init__(self, address: ChecksumAddress | None = None, abi=Any) -> None:
        self.abi = abi
        # TODO: make this better, shouldn't initialize to the zero address, but the Contract's init
        # function requires an address.
        self.address = address if address else cast(ChecksumAddress, "0x0000000000000000000000000000000000000000")

        try:
            # Initialize parent Contract class
            super().__init__(address=address)

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    # TODO: add events
    # events: ERC20ContractEvents

    functions: ERC4626HyperdriveDeployerContractFunctions

"""A web3.py Contract class for the ERC4626HyperdriveDeployer contract."""

# contracts have PascalCase names
# pylint: disable=invalid-name

# contracts control how many attributes and arguments we have in generated code
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments

# we don't need else statement if the other conditionals all have return,
# but it's easier to generate
# pylint: disable=no-else-return

# This file is bound to get very long depending on contract sizes.
# pylint: disable=too-many-lines

from __future__ import annotations
from typing import cast

from eth_typing import ChecksumAddress
from web3.types import ABI
from web3.contract.contract import Contract, ContractFunction, ContractFunctions
from web3.exceptions import FallbackNotFound


class ERC4626HyperdriveDeployerDeployContractFunction(ContractFunction):
    """ContractFunction for the deploy method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _config: tuple,
        _dataProvider: str,
        _linkerCodeHash: bytes,
        _linkerFactory: str,
        _extraData: list[bytes],
    ) -> "ERC4626HyperdriveDeployerDeployContractFunction":
        super().__call__(_config, _dataProvider, _linkerCodeHash, _linkerFactory, _extraData)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveDeployerContractFunctions(ContractFunctions):
    """ContractFunctions for the ERC4626HyperdriveDeployer contract."""

    deploy: ERC4626HyperdriveDeployerDeployContractFunction


erc4626hyperdrivedeployer_abi: ABI = cast(
    ABI,
    [
        {
            "inputs": [
                {
                    "internalType": "contract IERC4626",
                    "name": "_pool",
                    "type": "address",
                }
            ],
            "stateMutability": "nonpayable",
            "type": "constructor",
        },
        {
            "inputs": [
                {
                    "components": [
                        {
                            "internalType": "contract IERC20",
                            "name": "baseToken",
                            "type": "address",
                        },
                        {
                            "internalType": "uint256",
                            "name": "initialSharePrice",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "minimumShareReserves",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "minimumTransactionAmount",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "positionDuration",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "checkpointDuration",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "timeStretch",
                            "type": "uint256",
                        },
                        {
                            "internalType": "address",
                            "name": "governance",
                            "type": "address",
                        },
                        {
                            "internalType": "address",
                            "name": "feeCollector",
                            "type": "address",
                        },
                        {
                            "components": [
                                {
                                    "internalType": "uint256",
                                    "name": "curve",
                                    "type": "uint256",
                                },
                                {
                                    "internalType": "uint256",
                                    "name": "flat",
                                    "type": "uint256",
                                },
                                {
                                    "internalType": "uint256",
                                    "name": "governance",
                                    "type": "uint256",
                                },
                            ],
                            "internalType": "struct IHyperdrive.Fees",
                            "name": "fees",
                            "type": "tuple",
                        },
                        {
                            "internalType": "uint256",
                            "name": "oracleSize",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "updateGap",
                            "type": "uint256",
                        },
                    ],
                    "internalType": "struct IHyperdrive.PoolConfig",
                    "name": "_config",
                    "type": "tuple",
                },
                {
                    "internalType": "address",
                    "name": "_dataProvider",
                    "type": "address",
                },
                {
                    "internalType": "bytes32",
                    "name": "_linkerCodeHash",
                    "type": "bytes32",
                },
                {
                    "internalType": "address",
                    "name": "_linkerFactory",
                    "type": "address",
                },
                {
                    "internalType": "bytes32[]",
                    "name": "_extraData",
                    "type": "bytes32[]",
                },
            ],
            "name": "deploy",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ],
)


class ERC4626HyperdriveDeployerContract(Contract):
    """A web3.py Contract class for the ERC4626HyperdriveDeployer contract."""

    abi: ABI = erc4626hyperdrivedeployer_abi

    def __init__(self, address: ChecksumAddress | None = None) -> None:
        try:
            # Initialize parent Contract class
            super().__init__(address=address)

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    # TODO: add events
    # events: ERC20ContractEvents

    functions: ERC4626HyperdriveDeployerContractFunctions

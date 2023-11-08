"""A web3.py Contract class for the ForwarderFactory contract."""

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


class ForwarderFactoryERC20LINK_HASHContractFunction(ContractFunction):
    """ContractFunction for the ERC20LINK_HASH method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ForwarderFactoryERC20LINK_HASHContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ForwarderFactoryCreateContractFunction(ContractFunction):
    """ContractFunction for the create method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, token: str, tokenId: int) -> "ForwarderFactoryCreateContractFunction":
        super().__call__(token, tokenId)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ForwarderFactoryGetDeployDetailsContractFunction(ContractFunction):
    """ContractFunction for the getDeployDetails method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ForwarderFactoryGetDeployDetailsContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ForwarderFactoryGetForwarderContractFunction(ContractFunction):
    """ContractFunction for the getForwarder method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, token: str, tokenId: int) -> "ForwarderFactoryGetForwarderContractFunction":
        super().__call__(token, tokenId)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ForwarderFactoryContractFunctions(ContractFunctions):
    """ContractFunctions for the ForwarderFactory contract."""

    ERC20LINK_HASH: ForwarderFactoryERC20LINK_HASHContractFunction

    create: ForwarderFactoryCreateContractFunction

    getDeployDetails: ForwarderFactoryGetDeployDetailsContractFunction

    getForwarder: ForwarderFactoryGetForwarderContractFunction


forwarderfactory_abi: ABI = cast(
    ABI,
    [
        {"inputs": [], "stateMutability": "nonpayable", "type": "constructor"},
        {"inputs": [], "name": "InvalidForwarderAddress", "type": "error"},
        {
            "inputs": [],
            "name": "ERC20LINK_HASH",
            "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "contract IMultiToken",
                    "name": "token",
                    "type": "address",
                },
                {
                    "internalType": "uint256",
                    "name": "tokenId",
                    "type": "uint256",
                },
            ],
            "name": "create",
            "outputs": [
                {
                    "internalType": "contract ERC20Forwarder",
                    "name": "",
                    "type": "address",
                }
            ],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getDeployDetails",
            "outputs": [
                {
                    "internalType": "contract IMultiToken",
                    "name": "",
                    "type": "address",
                },
                {"internalType": "uint256", "name": "", "type": "uint256"},
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "contract IMultiToken",
                    "name": "token",
                    "type": "address",
                },
                {
                    "internalType": "uint256",
                    "name": "tokenId",
                    "type": "uint256",
                },
            ],
            "name": "getForwarder",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
    ],
)


class ForwarderFactoryContract(Contract):
    """A web3.py Contract class for the ForwarderFactory contract."""

    abi: ABI = forwarderfactory_abi

    def __init__(self, address: ChecksumAddress | None = None) -> None:
        try:
            # Initialize parent Contract class
            super().__init__(address=address)

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    # TODO: add events
    # events: ERC20ContractEvents

    functions: ForwarderFactoryContractFunctions

"""A web3.py Contract class for the ForwarderFactory contract."""
# contracts have PascalCase names
# pylint: disable=invalid-name
# contracts control how many attributes and arguments we have in generated code
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
# we don't need else statement if the other conditionals all have return,
# but it's easier to generate
# pylint: disable=no-else-return
from __future__ import annotations

from typing import Any, cast

from eth_typing import ChecksumAddress
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


class ForwarderFactoryContract(Contract):
    """A web3.py Contract class for the ForwarderFactory contract."""

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

    functions: ForwarderFactoryContractFunctions

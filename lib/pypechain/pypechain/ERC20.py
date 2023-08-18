from __future__ import annotations
from typing import Any, cast
from eth_typing import ChecksumAddress
from web3 import Web3
from web3.contract.contract import Contract, ContractFunction, ContractFunctions
from web3.exceptions import FallbackNotFound


class ERC20allowanceContractFunction(ContractFunction):
    """ContractFunction for the allowance method."""

    # pylint: disable=arguments-differ
    def __call__(self, owner: address, spender: address) -> "ERC20allowanceContractFunction":
        super().__call__(owner: address, spender: address)
        return self

class ERC20approveContractFunction(ContractFunction):
    """ContractFunction for the approve method."""

    # pylint: disable=arguments-differ
    def __call__(self, spender: address, amount: uint256) -> "ERC20approveContractFunction":
        super().__call__(spender: address, amount: uint256)
        return self

class ERC20balanceOfContractFunction(ContractFunction):
    """ContractFunction for the balanceOf method."""

    # pylint: disable=arguments-differ
    def __call__(self, account: address) -> "ERC20balanceOfContractFunction":
        super().__call__(account: address)
        return self

class ERC20decimalsContractFunction(ContractFunction):
    """ContractFunction for the decimals method."""

    # pylint: disable=arguments-differ
    def __call__(self, ) -> "ERC20decimalsContractFunction":
        super().__call__()
        return self

class ERC20decreaseAllowanceContractFunction(ContractFunction):
    """ContractFunction for the decreaseAllowance method."""

    # pylint: disable=arguments-differ
    def __call__(self, spender: address, subtractedValue: uint256) -> "ERC20decreaseAllowanceContractFunction":
        super().__call__(spender: address, subtractedValue: uint256)
        return self

class ERC20increaseAllowanceContractFunction(ContractFunction):
    """ContractFunction for the increaseAllowance method."""

    # pylint: disable=arguments-differ
    def __call__(self, spender: address, addedValue: uint256) -> "ERC20increaseAllowanceContractFunction":
        super().__call__(spender: address, addedValue: uint256)
        return self

class ERC20nameContractFunction(ContractFunction):
    """ContractFunction for the name method."""

    # pylint: disable=arguments-differ
    def __call__(self, ) -> "ERC20nameContractFunction":
        super().__call__()
        return self

class ERC20symbolContractFunction(ContractFunction):
    """ContractFunction for the symbol method."""

    # pylint: disable=arguments-differ
    def __call__(self, ) -> "ERC20symbolContractFunction":
        super().__call__()
        return self

class ERC20totalSupplyContractFunction(ContractFunction):
    """ContractFunction for the totalSupply method."""

    # pylint: disable=arguments-differ
    def __call__(self, ) -> "ERC20totalSupplyContractFunction":
        super().__call__()
        return self

class ERC20transferContractFunction(ContractFunction):
    """ContractFunction for the transfer method."""

    # pylint: disable=arguments-differ
    def __call__(self, to: address, amount: uint256) -> "ERC20transferContractFunction":
        super().__call__(to: address, amount: uint256)
        return self

class ERC20transferFromContractFunction(ContractFunction):
    """ContractFunction for the transferFrom method."""

    # pylint: disable=arguments-differ
    def __call__(self, from: address, to: address, amount: uint256) -> "ERC20transferFromContractFunction":
        super().__call__(from: address, to: address, amount: uint256)
        return self


class ERC20ContractFunctions(ContractFunctions):
    """ContractFunctions for the ERC20 contract."""

    allowance: ERC20allowanceContractFunction

    approve: ERC20approveContractFunction

    balanceOf: ERC20balanceOfContractFunction

    decimals: ERC20decimalsContractFunction

    decreaseAllowance: ERC20decreaseAllowanceContractFunction

    increaseAllowance: ERC20increaseAllowanceContractFunction

    name: ERC20nameContractFunction

    symbol: ERC20symbolContractFunction

    totalSupply: ERC20totalSupplyContractFunction

    transfer: ERC20transferContractFunction

    transferFrom: ERC20transferFromContractFunction


class ERC20Contract(Contract):
    def __init__(self, address: ChecksumAddress | None = None, abi=Any) -> None:
        self.abi = abi
        self.w3 = Web3()
        # TODO: make this better, shouldn't initialize to the zero address, but the Contract's init
        # function requires an address.
        self.address = address if address else cast(ChecksumAddress, "0x0000000000000000000000000000000000000000")

        try:
            # Initialize parent Contract class
            super().__init__(address=address)

            # Additional initialization, if any
            # self.functions = super().functions

            # TODO: map types like 'address' to Address
            # TODO: map inputs to functions.functionName.args
            # for function in self.functions._functions:  # type: ignore
            #     result = [(item["name"], item["type"]) for item in function["inputs"]]
            #     self.functions[function.name]["args"] = result

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    # TODO: add events
    # events: ERC20ContractEvents

    functions: ERC20ContractFunctions
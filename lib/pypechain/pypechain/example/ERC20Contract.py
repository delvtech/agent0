from __future__ import annotations

from typing import Any, cast

from eth_typing import ChecksumAddress
from web3 import Web3
from web3.contract.contract import Contract, ContractFunction, ContractFunctions
from web3.exceptions import FallbackNotFound


class AllowanceContractFunction(ContractFunction):
    """ContractFunction for the Allowance method."""

    # pylint: disable=arguments-differ
    def __call__(self, owner: str, spender: str) -> "AllowanceContractFunction":
        super().__call__(owner, spender)
        return self


class ApproveContractFunction(ContractFunction):
    """ContractFunction for the Approve method."""

    # pylint: disable=arguments-differ
    def __call__(self, spender: str, amount: str) -> "ApproveContractFunction":
        super().__call__(spender, amount)
        return self


class ERC20ContractFunctions(ContractFunctions):
    allowance: AllowanceContractFunction
    approve: ContractFunction


# class ERC20ContractEvents(ContractEvents):


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

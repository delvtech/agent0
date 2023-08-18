# pylint: disable=C0103
"""Working file to check outputs of run_pypechain.py against.  TODOs kept track of in here as well
as in the jinja template"""
from __future__ import annotations

from typing import Any, cast

from eth_typing import ChecksumAddress
from web3.contract.contract import Contract, ContractFunction, ContractFunctions
from web3.exceptions import FallbackNotFound


# TODO: break out function classes to their own files?
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
    """ContractFunctions for the ERC20 contract."""

    allowance: AllowanceContractFunction
    approve: ContractFunction


# TODO: Add Events.  These will have names like class ERC20TransferSingleEvent
# class ERC20ContractEvents(ContractEvents):


class ERC20Contract(Contract):
    """A web3.py Contract class for the ERC20 contract."""

    def __init__(self, address: ChecksumAddress | None = None, abi=Any) -> None:
        self.abi = abi
        # TODO: make this better, shouldn't initialize to the zero address, but the Contract's init
        # function requires an address.
        self.address = address if address else cast(ChecksumAddress, "0x0000000000000000000000000000000000000000")

        try:
            # Initialize parent Contract class
            super().__init__(address=address)

            # TODO: Additional initialization, if any
            # self.functions = super().functions

            # TODO: map types like 'address' to Address
            # TODO: map inputs to functions.functionName.args

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    # TODO: add events
    # events: ERC20ContractEvents

    functions: ERC20ContractFunctions

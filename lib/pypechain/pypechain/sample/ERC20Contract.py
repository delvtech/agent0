# pylint: disable=C0103
"""A web3.py Contract class for the ERC20 contract."""
from __future__ import annotations

from typing import Any, cast

from eth_typing import ChecksumAddress
from web3.contract.contract import Contract, ContractFunction, ContractFunctions
from web3.exceptions import FallbackNotFound


class ERC20allowanceContractFunction(ContractFunction):
    """ContractFunction for the allowance method."""

    # pylint: disable=arguments-differ
    def __call__(self, owner: str, spender: str) -> "ERC20allowanceContractFunction":
        super().__call__(owner, spender)
        return self


class ERC20approveContractFunction(ContractFunction):
    """ContractFunction for the approve method."""

    # pylint: disable=arguments-differ
    def __call__(self, spender: str, amount: int) -> "ERC20approveContractFunction":
        super().__call__(spender, amount)
        return self


class ERC20balanceOfContractFunction(ContractFunction):
    """ContractFunction for the balanceOf method."""

    # pylint: disable=arguments-differ
    def __call__(self, account: str) -> "ERC20balanceOfContractFunction":
        super().__call__(account)
        return self


class ERC20decimalsContractFunction(ContractFunction):
    """ContractFunction for the decimals method."""

    # pylint: disable=arguments-differ
    def __call__(
        self,
    ) -> "ERC20decimalsContractFunction":
        super().__call__()
        return self


class ERC20decreaseAllowanceContractFunction(ContractFunction):
    """ContractFunction for the decreaseAllowance method."""

    # pylint: disable=arguments-differ
    def __call__(self, spender: str, subtractedValue: int) -> "ERC20decreaseAllowanceContractFunction":
        super().__call__(spender, subtractedValue)
        return self


class ERC20increaseAllowanceContractFunction(ContractFunction):
    """ContractFunction for the increaseAllowance method."""

    # pylint: disable=arguments-differ
    def __call__(self, spender: str, addedValue: int) -> "ERC20increaseAllowanceContractFunction":
        super().__call__(spender, addedValue)
        return self


class ERC20nameContractFunction(ContractFunction):
    """ContractFunction for the name method."""

    # pylint: disable=arguments-differ
    def __call__(
        self,
    ) -> "ERC20nameContractFunction":
        super().__call__()
        return self


class ERC20symbolContractFunction(ContractFunction):
    """ContractFunction for the symbol method."""

    # pylint: disable=arguments-differ
    def __call__(
        self,
    ) -> "ERC20symbolContractFunction":
        super().__call__()
        return self


class ERC20totalSupplyContractFunction(ContractFunction):
    """ContractFunction for the totalSupply method."""

    # pylint: disable=arguments-differ
    def __call__(
        self,
    ) -> "ERC20totalSupplyContractFunction":
        super().__call__()
        return self


class ERC20transferContractFunction(ContractFunction):
    """ContractFunction for the transfer method."""

    # pylint: disable=arguments-differ
    def __call__(self, to: str, amount: int) -> "ERC20transferContractFunction":
        super().__call__(to, amount)
        return self


class ERC20transferFromContractFunction(ContractFunction):
    """ContractFunction for the transferFrom method."""

    # pylint: disable=arguments-differ
    def __call__(self, _from: str, to: str, amount: int) -> "ERC20transferFromContractFunction":
        super().__call__(_from, to, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


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
    """A web3.py Contract class for the ERC20 contract."""

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

    functions: ERC20ContractFunctions

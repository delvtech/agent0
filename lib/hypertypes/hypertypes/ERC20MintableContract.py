"""A web3.py Contract class for the ERC20Mintable contract."""
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


class ERC20MintableAllowanceContractFunction(ContractFunction):
    """ContractFunction for the allowance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, owner: str, spender: str
    ) -> "ERC20MintableAllowanceContractFunction":
        super().__call__(owner, spender)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableApproveContractFunction(ContractFunction):
    """ContractFunction for the approve method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, spender: str, amount: int
    ) -> "ERC20MintableApproveContractFunction":
        super().__call__(spender, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableBalanceOfContractFunction(ContractFunction):
    """ContractFunction for the balanceOf method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, account: str
    ) -> "ERC20MintableBalanceOfContractFunction":
        super().__call__(account)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableBurnContractFunction(ContractFunction):
    """ContractFunction for the burn method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, amount: int, destination: str | None = None
    ) -> "ERC20MintableBurnContractFunction":
        if all([destination is None]):
            super().__call__()
            return self

        else:
            super().__call__()
            return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableDecimalsContractFunction(ContractFunction):
    """ContractFunction for the decimals method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC20MintableDecimalsContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableDecreaseAllowanceContractFunction(ContractFunction):
    """ContractFunction for the decreaseAllowance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, spender: str, subtractedValue: int
    ) -> "ERC20MintableDecreaseAllowanceContractFunction":
        super().__call__(spender, subtractedValue)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableIncreaseAllowanceContractFunction(ContractFunction):
    """ContractFunction for the increaseAllowance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, spender: str, addedValue: int
    ) -> "ERC20MintableIncreaseAllowanceContractFunction":
        super().__call__(spender, addedValue)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableMintContractFunction(ContractFunction):
    """ContractFunction for the mint method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, amount: int, destination: str | None = None
    ) -> "ERC20MintableMintContractFunction":
        if all([destination is not None]):
            super().__call__()
            return self

        else:
            super().__call__()
            return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableNameContractFunction(ContractFunction):
    """ContractFunction for the name method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC20MintableNameContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableSymbolContractFunction(ContractFunction):
    """ContractFunction for the symbol method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC20MintableSymbolContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableTotalSupplyContractFunction(ContractFunction):
    """ContractFunction for the totalSupply method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC20MintableTotalSupplyContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableTransferContractFunction(ContractFunction):
    """ContractFunction for the transfer method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, to: str, amount: int
    ) -> "ERC20MintableTransferContractFunction":
        super().__call__(to, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableTransferFromContractFunction(ContractFunction):
    """ContractFunction for the transferFrom method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _from: str, to: str, amount: int
    ) -> "ERC20MintableTransferFromContractFunction":
        super().__call__(_from, to, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableContractFunctions(ContractFunctions):
    """ContractFunctions for the ERC20Mintable contract."""

    allowance: ERC20MintableAllowanceContractFunction

    approve: ERC20MintableApproveContractFunction

    balanceOf: ERC20MintableBalanceOfContractFunction

    burn: ERC20MintableBurnContractFunction

    decimals: ERC20MintableDecimalsContractFunction

    decreaseAllowance: ERC20MintableDecreaseAllowanceContractFunction

    increaseAllowance: ERC20MintableIncreaseAllowanceContractFunction

    mint: ERC20MintableMintContractFunction

    name: ERC20MintableNameContractFunction

    symbol: ERC20MintableSymbolContractFunction

    totalSupply: ERC20MintableTotalSupplyContractFunction

    transfer: ERC20MintableTransferContractFunction

    transferFrom: ERC20MintableTransferFromContractFunction


class ERC20MintableContract(Contract):
    """A web3.py Contract class for the ERC20Mintable contract."""

    def __init__(self, address: ChecksumAddress | None = None, abi=Any) -> None:
        self.abi = abi
        # TODO: make this better, shouldn't initialize to the zero address, but the Contract's init
        # function requires an address.
        self.address = (
            address
            if address
            else cast(
                ChecksumAddress, "0x0000000000000000000000000000000000000000"
            )
        )

        try:
            # Initialize parent Contract class
            super().__init__(address=address)

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    # TODO: add events
    # events: ERC20ContractEvents

    functions: ERC20MintableContractFunctions

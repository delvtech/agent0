"""A web3.py Contract class for the ERC4626DataProvider contract."""
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


class ERC4626DataProviderBalanceOfContractFunction(ContractFunction):
    """ContractFunction for the balanceOf method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenId: int, account: str) -> "ERC4626DataProviderBalanceOfContractFunction":
        super().__call__(tokenId, account)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderBaseTokenContractFunction(ContractFunction):
    """ContractFunction for the baseToken method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC4626DataProviderBaseTokenContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderFactoryContractFunction(ContractFunction):
    """ContractFunction for the factory method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC4626DataProviderFactoryContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderGetCheckpointContractFunction(ContractFunction):
    """ContractFunction for the getCheckpoint method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _checkpointId: int) -> "ERC4626DataProviderGetCheckpointContractFunction":
        super().__call__(_checkpointId)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderGetMarketStateContractFunction(ContractFunction):
    """ContractFunction for the getMarketState method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC4626DataProviderGetMarketStateContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderGetPoolConfigContractFunction(ContractFunction):
    """ContractFunction for the getPoolConfig method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC4626DataProviderGetPoolConfigContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderGetPoolInfoContractFunction(ContractFunction):
    """ContractFunction for the getPoolInfo method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC4626DataProviderGetPoolInfoContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderGetUncollectedGovernanceFeesContractFunction(ContractFunction):
    """ContractFunction for the getUncollectedGovernanceFees method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC4626DataProviderGetUncollectedGovernanceFeesContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderGetWithdrawPoolContractFunction(ContractFunction):
    """ContractFunction for the getWithdrawPool method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC4626DataProviderGetWithdrawPoolContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderIsApprovedForAllContractFunction(ContractFunction):
    """ContractFunction for the isApprovedForAll method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, account: str, operator: str) -> "ERC4626DataProviderIsApprovedForAllContractFunction":
        super().__call__(account, operator)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderIsSweepableContractFunction(ContractFunction):
    """ContractFunction for the isSweepable method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _target: str) -> "ERC4626DataProviderIsSweepableContractFunction":
        super().__call__(_target)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderLinkerCodeHashContractFunction(ContractFunction):
    """ContractFunction for the linkerCodeHash method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC4626DataProviderLinkerCodeHashContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderLoadContractFunction(ContractFunction):
    """ContractFunction for the load method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _slots: list[int]) -> "ERC4626DataProviderLoadContractFunction":
        super().__call__(_slots)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderNameContractFunction(ContractFunction):
    """ContractFunction for the name method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenId: int) -> "ERC4626DataProviderNameContractFunction":
        super().__call__(tokenId)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderNoncesContractFunction(ContractFunction):
    """ContractFunction for the nonces method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, account: str) -> "ERC4626DataProviderNoncesContractFunction":
        super().__call__(account)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderPerTokenApprovalsContractFunction(ContractFunction):
    """ContractFunction for the perTokenApprovals method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, tokenId: int, account: str, spender: str
    ) -> "ERC4626DataProviderPerTokenApprovalsContractFunction":
        super().__call__(tokenId, account, spender)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderPoolContractFunction(ContractFunction):
    """ContractFunction for the pool method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC4626DataProviderPoolContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderQueryContractFunction(ContractFunction):
    """ContractFunction for the query method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, period: int) -> "ERC4626DataProviderQueryContractFunction":
        super().__call__(period)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderSymbolContractFunction(ContractFunction):
    """ContractFunction for the symbol method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenId: int) -> "ERC4626DataProviderSymbolContractFunction":
        super().__call__(tokenId)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderTotalSupplyContractFunction(ContractFunction):
    """ContractFunction for the totalSupply method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenId: int) -> "ERC4626DataProviderTotalSupplyContractFunction":
        super().__call__(tokenId)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626DataProviderContractFunctions(ContractFunctions):
    """ContractFunctions for the ERC4626DataProvider contract."""

    balanceOf: ERC4626DataProviderBalanceOfContractFunction

    baseToken: ERC4626DataProviderBaseTokenContractFunction

    factory: ERC4626DataProviderFactoryContractFunction

    getCheckpoint: ERC4626DataProviderGetCheckpointContractFunction

    getMarketState: ERC4626DataProviderGetMarketStateContractFunction

    getPoolConfig: ERC4626DataProviderGetPoolConfigContractFunction

    getPoolInfo: ERC4626DataProviderGetPoolInfoContractFunction

    getUncollectedGovernanceFees: ERC4626DataProviderGetUncollectedGovernanceFeesContractFunction

    getWithdrawPool: ERC4626DataProviderGetWithdrawPoolContractFunction

    isApprovedForAll: ERC4626DataProviderIsApprovedForAllContractFunction

    isSweepable: ERC4626DataProviderIsSweepableContractFunction

    linkerCodeHash: ERC4626DataProviderLinkerCodeHashContractFunction

    load: ERC4626DataProviderLoadContractFunction

    name: ERC4626DataProviderNameContractFunction

    nonces: ERC4626DataProviderNoncesContractFunction

    perTokenApprovals: ERC4626DataProviderPerTokenApprovalsContractFunction

    pool: ERC4626DataProviderPoolContractFunction

    query: ERC4626DataProviderQueryContractFunction

    symbol: ERC4626DataProviderSymbolContractFunction

    totalSupply: ERC4626DataProviderTotalSupplyContractFunction


class ERC4626DataProviderContract(Contract):
    """A web3.py Contract class for the ERC4626DataProvider contract."""

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

    functions: ERC4626DataProviderContractFunctions

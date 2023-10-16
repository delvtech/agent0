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


class ERC20MintableDOMAIN_SEPARATORContractFunction(ContractFunction):
    """ContractFunction for the DOMAIN_SEPARATOR method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC20MintableDOMAIN_SEPARATORContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableAllowanceContractFunction(ContractFunction):
    """ContractFunction for the allowance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: str, arg2: str) -> "ERC20MintableAllowanceContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableApproveContractFunction(ContractFunction):
    """ContractFunction for the approve method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, spender: str, amount: int) -> "ERC20MintableApproveContractFunction":
        super().__call__(spender, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableAuthorityContractFunction(ContractFunction):
    """ContractFunction for the authority method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC20MintableAuthorityContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableBalanceOfContractFunction(ContractFunction):
    """ContractFunction for the balanceOf method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: str) -> "ERC20MintableBalanceOfContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableBurnContractFunction(ContractFunction):
    """ContractFunction for the burn method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, amount: int, destination: str | None = None) -> "ERC20MintableBurnContractFunction":
        if all([destination is None]):
            super().__call__()
            return self

        else:
            super().__call__()
            return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableCanCallContractFunction(ContractFunction):
    """ContractFunction for the canCall method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, user: str, target: str, functionSig: bytes) -> "ERC20MintableCanCallContractFunction":
        super().__call__(user, target, functionSig)
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


class ERC20MintableDoesRoleHaveCapabilityContractFunction(ContractFunction):
    """ContractFunction for the doesRoleHaveCapability method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, role: int, functionSig: bytes) -> "ERC20MintableDoesRoleHaveCapabilityContractFunction":
        super().__call__(role, functionSig)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableDoesUserHaveRoleContractFunction(ContractFunction):
    """ContractFunction for the doesUserHaveRole method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, user: str, role: int) -> "ERC20MintableDoesUserHaveRoleContractFunction":
        super().__call__(user, role)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableGetRolesWithCapabilityContractFunction(ContractFunction):
    """ContractFunction for the getRolesWithCapability method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: bytes) -> "ERC20MintableGetRolesWithCapabilityContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableGetTargetCustomAuthorityContractFunction(ContractFunction):
    """ContractFunction for the getTargetCustomAuthority method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: str) -> "ERC20MintableGetTargetCustomAuthorityContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableGetUserRolesContractFunction(ContractFunction):
    """ContractFunction for the getUserRoles method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: str) -> "ERC20MintableGetUserRolesContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableIsCapabilityPublicContractFunction(ContractFunction):
    """ContractFunction for the isCapabilityPublic method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: bytes) -> "ERC20MintableIsCapabilityPublicContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableMintContractFunction(ContractFunction):
    """ContractFunction for the mint method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, amount: int, destination: str | None = None) -> "ERC20MintableMintContractFunction":
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


class ERC20MintableNoncesContractFunction(ContractFunction):
    """ContractFunction for the nonces method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: str) -> "ERC20MintableNoncesContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableOwnerContractFunction(ContractFunction):
    """ContractFunction for the owner method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC20MintableOwnerContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintablePermitContractFunction(ContractFunction):
    """ContractFunction for the permit method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        owner: str,
        spender: str,
        value: int,
        deadline: int,
        v: int,
        r: bytes,
        s: bytes,
    ) -> "ERC20MintablePermitContractFunction":
        super().__call__(owner, spender, value, deadline, v, r, s)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableSetAuthorityContractFunction(ContractFunction):
    """ContractFunction for the setAuthority method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, newAuthority: str) -> "ERC20MintableSetAuthorityContractFunction":
        super().__call__(newAuthority)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableSetPublicCapabilityContractFunction(ContractFunction):
    """ContractFunction for the setPublicCapability method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, functionSig: bytes, enabled: bool) -> "ERC20MintableSetPublicCapabilityContractFunction":
        super().__call__(functionSig, enabled)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableSetRoleCapabilityContractFunction(ContractFunction):
    """ContractFunction for the setRoleCapability method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, role: int, functionSig: bytes, enabled: bool
    ) -> "ERC20MintableSetRoleCapabilityContractFunction":
        super().__call__(role, functionSig, enabled)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableSetTargetCustomAuthorityContractFunction(ContractFunction):
    """ContractFunction for the setTargetCustomAuthority method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, target: str, customAuthority: str) -> "ERC20MintableSetTargetCustomAuthorityContractFunction":
        super().__call__(target, customAuthority)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableSetUserRoleContractFunction(ContractFunction):
    """ContractFunction for the setUserRole method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, user: str, role: int, enabled: bool) -> "ERC20MintableSetUserRoleContractFunction":
        super().__call__(user, role, enabled)
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

    def __call__(self, to: str, amount: int) -> "ERC20MintableTransferContractFunction":
        super().__call__(to, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableTransferFromContractFunction(ContractFunction):
    """ContractFunction for the transferFrom method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _from: str, to: str, amount: int) -> "ERC20MintableTransferFromContractFunction":
        super().__call__(_from, to, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableTransferOwnershipContractFunction(ContractFunction):
    """ContractFunction for the transferOwnership method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, newOwner: str) -> "ERC20MintableTransferOwnershipContractFunction":
        super().__call__(newOwner)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC20MintableContractFunctions(ContractFunctions):
    """ContractFunctions for the ERC20Mintable contract."""

    DOMAIN_SEPARATOR: ERC20MintableDOMAIN_SEPARATORContractFunction

    allowance: ERC20MintableAllowanceContractFunction

    approve: ERC20MintableApproveContractFunction

    authority: ERC20MintableAuthorityContractFunction

    balanceOf: ERC20MintableBalanceOfContractFunction

    burn: ERC20MintableBurnContractFunction

    canCall: ERC20MintableCanCallContractFunction

    decimals: ERC20MintableDecimalsContractFunction

    doesRoleHaveCapability: ERC20MintableDoesRoleHaveCapabilityContractFunction

    doesUserHaveRole: ERC20MintableDoesUserHaveRoleContractFunction

    getRolesWithCapability: ERC20MintableGetRolesWithCapabilityContractFunction

    getTargetCustomAuthority: ERC20MintableGetTargetCustomAuthorityContractFunction

    getUserRoles: ERC20MintableGetUserRolesContractFunction

    isCapabilityPublic: ERC20MintableIsCapabilityPublicContractFunction

    mint: ERC20MintableMintContractFunction

    name: ERC20MintableNameContractFunction

    nonces: ERC20MintableNoncesContractFunction

    owner: ERC20MintableOwnerContractFunction

    permit: ERC20MintablePermitContractFunction

    setAuthority: ERC20MintableSetAuthorityContractFunction

    setPublicCapability: ERC20MintableSetPublicCapabilityContractFunction

    setRoleCapability: ERC20MintableSetRoleCapabilityContractFunction

    setTargetCustomAuthority: ERC20MintableSetTargetCustomAuthorityContractFunction

    setUserRole: ERC20MintableSetUserRoleContractFunction

    symbol: ERC20MintableSymbolContractFunction

    totalSupply: ERC20MintableTotalSupplyContractFunction

    transfer: ERC20MintableTransferContractFunction

    transferFrom: ERC20MintableTransferFromContractFunction

    transferOwnership: ERC20MintableTransferOwnershipContractFunction


class ERC20MintableContract(Contract):
    """A web3.py Contract class for the ERC20Mintable contract."""

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

    functions: ERC20MintableContractFunctions

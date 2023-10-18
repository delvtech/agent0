"""A web3.py Contract class for the MockERC4626 contract."""
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


class MockERC4626DOMAIN_SEPARATORContractFunction(ContractFunction):
    """ContractFunction for the DOMAIN_SEPARATOR method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "MockERC4626DOMAIN_SEPARATORContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626AllowanceContractFunction(ContractFunction):
    """ContractFunction for the allowance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: str, arg2: str) -> "MockERC4626AllowanceContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626ApproveContractFunction(ContractFunction):
    """ContractFunction for the approve method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, spender: str, amount: int) -> "MockERC4626ApproveContractFunction":
        super().__call__(spender, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626AssetContractFunction(ContractFunction):
    """ContractFunction for the asset method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "MockERC4626AssetContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626AuthorityContractFunction(ContractFunction):
    """ContractFunction for the authority method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "MockERC4626AuthorityContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626BalanceOfContractFunction(ContractFunction):
    """ContractFunction for the balanceOf method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: str) -> "MockERC4626BalanceOfContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626CanCallContractFunction(ContractFunction):
    """ContractFunction for the canCall method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, user: str, target: str, functionSig: bytes) -> "MockERC4626CanCallContractFunction":
        super().__call__(user, target, functionSig)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626ConvertToAssetsContractFunction(ContractFunction):
    """ContractFunction for the convertToAssets method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, shares: int) -> "MockERC4626ConvertToAssetsContractFunction":
        super().__call__(shares)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626ConvertToSharesContractFunction(ContractFunction):
    """ContractFunction for the convertToShares method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, assets: int) -> "MockERC4626ConvertToSharesContractFunction":
        super().__call__(assets)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626DecimalsContractFunction(ContractFunction):
    """ContractFunction for the decimals method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "MockERC4626DecimalsContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626DepositContractFunction(ContractFunction):
    """ContractFunction for the deposit method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _assets: int, _receiver: str) -> "MockERC4626DepositContractFunction":
        super().__call__(_assets, _receiver)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626DoesRoleHaveCapabilityContractFunction(ContractFunction):
    """ContractFunction for the doesRoleHaveCapability method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, role: int, functionSig: bytes) -> "MockERC4626DoesRoleHaveCapabilityContractFunction":
        super().__call__(role, functionSig)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626DoesUserHaveRoleContractFunction(ContractFunction):
    """ContractFunction for the doesUserHaveRole method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, user: str, role: int) -> "MockERC4626DoesUserHaveRoleContractFunction":
        super().__call__(user, role)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626GetRateContractFunction(ContractFunction):
    """ContractFunction for the getRate method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "MockERC4626GetRateContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626GetRolesWithCapabilityContractFunction(ContractFunction):
    """ContractFunction for the getRolesWithCapability method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: bytes) -> "MockERC4626GetRolesWithCapabilityContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626GetTargetCustomAuthorityContractFunction(ContractFunction):
    """ContractFunction for the getTargetCustomAuthority method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: str) -> "MockERC4626GetTargetCustomAuthorityContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626GetUserRolesContractFunction(ContractFunction):
    """ContractFunction for the getUserRoles method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: str) -> "MockERC4626GetUserRolesContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626IsCapabilityPublicContractFunction(ContractFunction):
    """ContractFunction for the isCapabilityPublic method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: bytes) -> "MockERC4626IsCapabilityPublicContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626MaxDepositContractFunction(ContractFunction):
    """ContractFunction for the maxDeposit method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: str) -> "MockERC4626MaxDepositContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626MaxMintContractFunction(ContractFunction):
    """ContractFunction for the maxMint method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: str) -> "MockERC4626MaxMintContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626MaxRedeemContractFunction(ContractFunction):
    """ContractFunction for the maxRedeem method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, owner: str) -> "MockERC4626MaxRedeemContractFunction":
        super().__call__(owner)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626MaxWithdrawContractFunction(ContractFunction):
    """ContractFunction for the maxWithdraw method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, owner: str) -> "MockERC4626MaxWithdrawContractFunction":
        super().__call__(owner)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626MintContractFunction(ContractFunction):
    """ContractFunction for the mint method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _shares: int, _receiver: str) -> "MockERC4626MintContractFunction":
        super().__call__(_shares, _receiver)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626NameContractFunction(ContractFunction):
    """ContractFunction for the name method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "MockERC4626NameContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626NoncesContractFunction(ContractFunction):
    """ContractFunction for the nonces method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: str) -> "MockERC4626NoncesContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626OwnerContractFunction(ContractFunction):
    """ContractFunction for the owner method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "MockERC4626OwnerContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626PermitContractFunction(ContractFunction):
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
    ) -> "MockERC4626PermitContractFunction":
        super().__call__(owner, spender, value, deadline, v, r, s)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626PreviewDepositContractFunction(ContractFunction):
    """ContractFunction for the previewDeposit method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, assets: int) -> "MockERC4626PreviewDepositContractFunction":
        super().__call__(assets)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626PreviewMintContractFunction(ContractFunction):
    """ContractFunction for the previewMint method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, shares: int) -> "MockERC4626PreviewMintContractFunction":
        super().__call__(shares)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626PreviewRedeemContractFunction(ContractFunction):
    """ContractFunction for the previewRedeem method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, shares: int) -> "MockERC4626PreviewRedeemContractFunction":
        super().__call__(shares)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626PreviewWithdrawContractFunction(ContractFunction):
    """ContractFunction for the previewWithdraw method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, assets: int) -> "MockERC4626PreviewWithdrawContractFunction":
        super().__call__(assets)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626RedeemContractFunction(ContractFunction):
    """ContractFunction for the redeem method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _shares: int, _receiver: str, _owner: str) -> "MockERC4626RedeemContractFunction":
        super().__call__(_shares, _receiver, _owner)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626SetAuthorityContractFunction(ContractFunction):
    """ContractFunction for the setAuthority method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, newAuthority: str) -> "MockERC4626SetAuthorityContractFunction":
        super().__call__(newAuthority)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626SetPublicCapabilityContractFunction(ContractFunction):
    """ContractFunction for the setPublicCapability method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, functionSig: bytes, enabled: bool) -> "MockERC4626SetPublicCapabilityContractFunction":
        super().__call__(functionSig, enabled)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626SetRateContractFunction(ContractFunction):
    """ContractFunction for the setRate method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _rate_: int) -> "MockERC4626SetRateContractFunction":
        super().__call__(_rate_)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626SetRoleCapabilityContractFunction(ContractFunction):
    """ContractFunction for the setRoleCapability method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, role: int, functionSig: bytes, enabled: bool) -> "MockERC4626SetRoleCapabilityContractFunction":
        super().__call__(role, functionSig, enabled)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626SetTargetCustomAuthorityContractFunction(ContractFunction):
    """ContractFunction for the setTargetCustomAuthority method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, target: str, customAuthority: str) -> "MockERC4626SetTargetCustomAuthorityContractFunction":
        super().__call__(target, customAuthority)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626SetUserRoleContractFunction(ContractFunction):
    """ContractFunction for the setUserRole method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, user: str, role: int, enabled: bool) -> "MockERC4626SetUserRoleContractFunction":
        super().__call__(user, role, enabled)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626SymbolContractFunction(ContractFunction):
    """ContractFunction for the symbol method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "MockERC4626SymbolContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626TotalAssetsContractFunction(ContractFunction):
    """ContractFunction for the totalAssets method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "MockERC4626TotalAssetsContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626TotalSupplyContractFunction(ContractFunction):
    """ContractFunction for the totalSupply method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "MockERC4626TotalSupplyContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626TransferContractFunction(ContractFunction):
    """ContractFunction for the transfer method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, to: str, amount: int) -> "MockERC4626TransferContractFunction":
        super().__call__(to, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626TransferFromContractFunction(ContractFunction):
    """ContractFunction for the transferFrom method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _from: str, to: str, amount: int) -> "MockERC4626TransferFromContractFunction":
        super().__call__(_from, to, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626TransferOwnershipContractFunction(ContractFunction):
    """ContractFunction for the transferOwnership method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, newOwner: str) -> "MockERC4626TransferOwnershipContractFunction":
        super().__call__(newOwner)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626WithdrawContractFunction(ContractFunction):
    """ContractFunction for the withdraw method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _assets: int, _receiver: str, _owner: str) -> "MockERC4626WithdrawContractFunction":
        super().__call__(_assets, _receiver, _owner)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class MockERC4626ContractFunctions(ContractFunctions):
    """ContractFunctions for the MockERC4626 contract."""

    DOMAIN_SEPARATOR: MockERC4626DOMAIN_SEPARATORContractFunction

    allowance: MockERC4626AllowanceContractFunction

    approve: MockERC4626ApproveContractFunction

    asset: MockERC4626AssetContractFunction

    authority: MockERC4626AuthorityContractFunction

    balanceOf: MockERC4626BalanceOfContractFunction

    canCall: MockERC4626CanCallContractFunction

    convertToAssets: MockERC4626ConvertToAssetsContractFunction

    convertToShares: MockERC4626ConvertToSharesContractFunction

    decimals: MockERC4626DecimalsContractFunction

    deposit: MockERC4626DepositContractFunction

    doesRoleHaveCapability: MockERC4626DoesRoleHaveCapabilityContractFunction

    doesUserHaveRole: MockERC4626DoesUserHaveRoleContractFunction

    getRate: MockERC4626GetRateContractFunction

    getRolesWithCapability: MockERC4626GetRolesWithCapabilityContractFunction

    getTargetCustomAuthority: MockERC4626GetTargetCustomAuthorityContractFunction

    getUserRoles: MockERC4626GetUserRolesContractFunction

    isCapabilityPublic: MockERC4626IsCapabilityPublicContractFunction

    maxDeposit: MockERC4626MaxDepositContractFunction

    maxMint: MockERC4626MaxMintContractFunction

    maxRedeem: MockERC4626MaxRedeemContractFunction

    maxWithdraw: MockERC4626MaxWithdrawContractFunction

    mint: MockERC4626MintContractFunction

    name: MockERC4626NameContractFunction

    nonces: MockERC4626NoncesContractFunction

    owner: MockERC4626OwnerContractFunction

    permit: MockERC4626PermitContractFunction

    previewDeposit: MockERC4626PreviewDepositContractFunction

    previewMint: MockERC4626PreviewMintContractFunction

    previewRedeem: MockERC4626PreviewRedeemContractFunction

    previewWithdraw: MockERC4626PreviewWithdrawContractFunction

    redeem: MockERC4626RedeemContractFunction

    setAuthority: MockERC4626SetAuthorityContractFunction

    setPublicCapability: MockERC4626SetPublicCapabilityContractFunction

    setRate: MockERC4626SetRateContractFunction

    setRoleCapability: MockERC4626SetRoleCapabilityContractFunction

    setTargetCustomAuthority: MockERC4626SetTargetCustomAuthorityContractFunction

    setUserRole: MockERC4626SetUserRoleContractFunction

    symbol: MockERC4626SymbolContractFunction

    totalAssets: MockERC4626TotalAssetsContractFunction

    totalSupply: MockERC4626TotalSupplyContractFunction

    transfer: MockERC4626TransferContractFunction

    transferFrom: MockERC4626TransferFromContractFunction

    transferOwnership: MockERC4626TransferOwnershipContractFunction

    withdraw: MockERC4626WithdrawContractFunction


class MockERC4626Contract(Contract):
    """A web3.py Contract class for the MockERC4626 contract."""

    def __init__(self, address: ChecksumAddress | None = None, abi=Any) -> None:
        self.abi = abi  # type: ignore
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

    functions: MockERC4626ContractFunctions

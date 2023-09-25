"""A web3.py Contract class for the IHyperdrive contract."""
# super() call methods are generic, while our version adds values & types
# pylint: disable=arguments-differ
# contracts have PascalCase names
# pylint: disable=invalid-name
# contracts control how many attributes and arguments we have in generated code
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
# unable to determine which imports will be used in the generated code
# pylint: disable=unused-import
# we don't need else statement if the other conditionals all have return,
# but it's easier to generate
# pylint: disable=no-else-return
from __future__ import annotations

from typing import Any, cast

from eth_typing import ChecksumAddress
from web3.contract.contract import Contract, ContractFunction, ContractFunctions
from web3.exceptions import FallbackNotFound


class IHyperdriveDOMAIN_SEPARATORContractFunction(ContractFunction):
    """ContractFunction for the DOMAIN_SEPARATOR method."""

    def __call__(self) -> "IHyperdriveDOMAIN_SEPARATORContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveAddLiquidityContractFunction(ContractFunction):
    """ContractFunction for the addLiquidity method."""

    def __call__(
        self, _contribution: int, _minApr: int, _maxApr: int, _destination: str, _asUnderlying: bool
    ) -> "IHyperdriveAddLiquidityContractFunction":
        super().__call__(_contribution, _minApr, _maxApr, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveBalanceOfContractFunction(ContractFunction):
    """ContractFunction for the balanceOf method."""

    def __call__(self, tokenId: int, owner: str) -> "IHyperdriveBalanceOfContractFunction":
        super().__call__(tokenId, owner)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveBaseTokenContractFunction(ContractFunction):
    """ContractFunction for the baseToken method."""

    def __call__(self) -> "IHyperdriveBaseTokenContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveBatchTransferFromContractFunction(ContractFunction):
    """ContractFunction for the batchTransferFrom method."""

    def __call__(
        self, _from: str, to: str, ids: list[int], values: list[int]
    ) -> "IHyperdriveBatchTransferFromContractFunction":
        super().__call__(_from, to, ids, values)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveCheckpointContractFunction(ContractFunction):
    """ContractFunction for the checkpoint method."""

    def __call__(self, _checkpointTime: int) -> "IHyperdriveCheckpointContractFunction":
        super().__call__(_checkpointTime)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveCloseLongContractFunction(ContractFunction):
    """ContractFunction for the closeLong method."""

    def __call__(
        self, _maturityTime: int, _bondAmount: int, _minOutput: int, _destination: str, _asUnderlying: bool
    ) -> "IHyperdriveCloseLongContractFunction":
        super().__call__(_maturityTime, _bondAmount, _minOutput, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveCloseShortContractFunction(ContractFunction):
    """ContractFunction for the closeShort method."""

    def __call__(
        self, _maturityTime: int, _bondAmount: int, _minOutput: int, _destination: str, _asUnderlying: bool
    ) -> "IHyperdriveCloseShortContractFunction":
        super().__call__(_maturityTime, _bondAmount, _minOutput, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveCollectGovernanceFeeContractFunction(ContractFunction):
    """ContractFunction for the collectGovernanceFee method."""

    def __call__(self, asUnderlying: bool) -> "IHyperdriveCollectGovernanceFeeContractFunction":
        super().__call__(asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveFactoryContractFunction(ContractFunction):
    """ContractFunction for the factory method."""

    def __call__(self) -> "IHyperdriveFactoryContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveGetCheckpointContractFunction(ContractFunction):
    """ContractFunction for the getCheckpoint method."""

    def __call__(self, _checkpointId: int) -> "IHyperdriveGetCheckpointContractFunction":
        super().__call__(_checkpointId)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveGetMarketStateContractFunction(ContractFunction):
    """ContractFunction for the getMarketState method."""

    def __call__(self) -> "IHyperdriveGetMarketStateContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveGetPoolConfigContractFunction(ContractFunction):
    """ContractFunction for the getPoolConfig method."""

    def __call__(self) -> "IHyperdriveGetPoolConfigContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveGetPoolInfoContractFunction(ContractFunction):
    """ContractFunction for the getPoolInfo method."""

    def __call__(self) -> "IHyperdriveGetPoolInfoContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveGetUncollectedGovernanceFeesContractFunction(ContractFunction):
    """ContractFunction for the getUncollectedGovernanceFees method."""

    def __call__(self) -> "IHyperdriveGetUncollectedGovernanceFeesContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveGetWithdrawPoolContractFunction(ContractFunction):
    """ContractFunction for the getWithdrawPool method."""

    def __call__(self) -> "IHyperdriveGetWithdrawPoolContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveInitializeContractFunction(ContractFunction):
    """ContractFunction for the initialize method."""

    def __call__(
        self, _contribution: int, _apr: int, _destination: str, _asUnderlying: bool
    ) -> "IHyperdriveInitializeContractFunction":
        super().__call__(_contribution, _apr, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveIsApprovedForAllContractFunction(ContractFunction):
    """ContractFunction for the isApprovedForAll method."""

    def __call__(self, owner: str, spender: str) -> "IHyperdriveIsApprovedForAllContractFunction":
        super().__call__(owner, spender)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveLinkerCodeHashContractFunction(ContractFunction):
    """ContractFunction for the linkerCodeHash method."""

    def __call__(self) -> "IHyperdriveLinkerCodeHashContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveLoadContractFunction(ContractFunction):
    """ContractFunction for the load method."""

    def __call__(self, _slots: list[int]) -> "IHyperdriveLoadContractFunction":
        super().__call__(_slots)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveNameContractFunction(ContractFunction):
    """ContractFunction for the name method."""

    def __call__(self, _id: int) -> "IHyperdriveNameContractFunction":
        super().__call__(_id)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveNoncesContractFunction(ContractFunction):
    """ContractFunction for the nonces method."""

    def __call__(self, owner: str) -> "IHyperdriveNoncesContractFunction":
        super().__call__(owner)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveOpenLongContractFunction(ContractFunction):
    """ContractFunction for the openLong method."""

    def __call__(
        self, _baseAmount: int, _minOutput: int, _destination: str, _asUnderlying: bool
    ) -> "IHyperdriveOpenLongContractFunction":
        super().__call__(_baseAmount, _minOutput, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveOpenShortContractFunction(ContractFunction):
    """ContractFunction for the openShort method."""

    def __call__(
        self, _bondAmount: int, _maxDeposit: int, _destination: str, _asUnderlying: bool
    ) -> "IHyperdriveOpenShortContractFunction":
        super().__call__(_bondAmount, _maxDeposit, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdrivePauseContractFunction(ContractFunction):
    """ContractFunction for the pause method."""

    def __call__(self, status: bool) -> "IHyperdrivePauseContractFunction":
        super().__call__(status)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdrivePerTokenApprovalsContractFunction(ContractFunction):
    """ContractFunction for the perTokenApprovals method."""

    def __call__(self, tokenId: int, owner: str, spender: str) -> "IHyperdrivePerTokenApprovalsContractFunction":
        super().__call__(tokenId, owner, spender)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdrivePermitForAllContractFunction(ContractFunction):
    """ContractFunction for the permitForAll method."""

    def __call__(
        self, owner: str, spender: str, _approved: bool, deadline: int, v: int, r: bytes, s: bytes
    ) -> "IHyperdrivePermitForAllContractFunction":
        super().__call__(owner, spender, _approved, deadline, v, r, s)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveRedeemWithdrawalSharesContractFunction(ContractFunction):
    """ContractFunction for the redeemWithdrawalShares method."""

    def __call__(
        self, _shares: int, _minOutput: int, _destination: str, _asUnderlying: bool
    ) -> "IHyperdriveRedeemWithdrawalSharesContractFunction":
        super().__call__(_shares, _minOutput, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveRemoveLiquidityContractFunction(ContractFunction):
    """ContractFunction for the removeLiquidity method."""

    def __call__(
        self, _shares: int, _minOutput: int, _destination: str, _asUnderlying: bool
    ) -> "IHyperdriveRemoveLiquidityContractFunction":
        super().__call__(_shares, _minOutput, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveSetApprovalContractFunction(ContractFunction):
    """ContractFunction for the setApproval method."""

    def __call__(self, tokenID: int, operator: str, amount: int) -> "IHyperdriveSetApprovalContractFunction":
        super().__call__(tokenID, operator, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveSetApprovalBridgeContractFunction(ContractFunction):
    """ContractFunction for the setApprovalBridge method."""

    def __call__(
        self, tokenID: int, operator: str, amount: int, caller: str
    ) -> "IHyperdriveSetApprovalBridgeContractFunction":
        super().__call__(tokenID, operator, amount, caller)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveSetApprovalForAllContractFunction(ContractFunction):
    """ContractFunction for the setApprovalForAll method."""

    def __call__(self, operator: str, approved: bool) -> "IHyperdriveSetApprovalForAllContractFunction":
        super().__call__(operator, approved)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveSetGovernanceContractFunction(ContractFunction):
    """ContractFunction for the setGovernance method."""

    def __call__(self, who: str) -> "IHyperdriveSetGovernanceContractFunction":
        super().__call__(who)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveSetPauserContractFunction(ContractFunction):
    """ContractFunction for the setPauser method."""

    def __call__(self, who: str, status: bool) -> "IHyperdriveSetPauserContractFunction":
        super().__call__(who, status)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveSymbolContractFunction(ContractFunction):
    """ContractFunction for the symbol method."""

    def __call__(self, _id: int) -> "IHyperdriveSymbolContractFunction":
        super().__call__(_id)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveTotalSupplyContractFunction(ContractFunction):
    """ContractFunction for the totalSupply method."""

    def __call__(self, _id: int) -> "IHyperdriveTotalSupplyContractFunction":
        super().__call__(_id)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveTransferFromContractFunction(ContractFunction):
    """ContractFunction for the transferFrom method."""

    def __call__(self, tokenID: int, _from: str, to: str, amount: int) -> "IHyperdriveTransferFromContractFunction":
        super().__call__(tokenID, _from, to, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveTransferFromBridgeContractFunction(ContractFunction):
    """ContractFunction for the transferFromBridge method."""

    def __call__(
        self, tokenID: int, _from: str, to: str, amount: int, caller: str
    ) -> "IHyperdriveTransferFromBridgeContractFunction":
        super().__call__(tokenID, _from, to, amount, caller)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveContractFunctions(ContractFunctions):
    """ContractFunctions for the IHyperdrive contract."""

    DOMAIN_SEPARATOR: IHyperdriveDOMAIN_SEPARATORContractFunction

    addLiquidity: IHyperdriveAddLiquidityContractFunction

    balanceOf: IHyperdriveBalanceOfContractFunction

    baseToken: IHyperdriveBaseTokenContractFunction

    batchTransferFrom: IHyperdriveBatchTransferFromContractFunction

    checkpoint: IHyperdriveCheckpointContractFunction

    closeLong: IHyperdriveCloseLongContractFunction

    closeShort: IHyperdriveCloseShortContractFunction

    collectGovernanceFee: IHyperdriveCollectGovernanceFeeContractFunction

    factory: IHyperdriveFactoryContractFunction

    getCheckpoint: IHyperdriveGetCheckpointContractFunction

    getMarketState: IHyperdriveGetMarketStateContractFunction

    getPoolConfig: IHyperdriveGetPoolConfigContractFunction

    getPoolInfo: IHyperdriveGetPoolInfoContractFunction

    getUncollectedGovernanceFees: IHyperdriveGetUncollectedGovernanceFeesContractFunction

    getWithdrawPool: IHyperdriveGetWithdrawPoolContractFunction

    initialize: IHyperdriveInitializeContractFunction

    isApprovedForAll: IHyperdriveIsApprovedForAllContractFunction

    linkerCodeHash: IHyperdriveLinkerCodeHashContractFunction

    load: IHyperdriveLoadContractFunction

    name: IHyperdriveNameContractFunction

    nonces: IHyperdriveNoncesContractFunction

    openLong: IHyperdriveOpenLongContractFunction

    openShort: IHyperdriveOpenShortContractFunction

    pause: IHyperdrivePauseContractFunction

    perTokenApprovals: IHyperdrivePerTokenApprovalsContractFunction

    permitForAll: IHyperdrivePermitForAllContractFunction

    redeemWithdrawalShares: IHyperdriveRedeemWithdrawalSharesContractFunction

    removeLiquidity: IHyperdriveRemoveLiquidityContractFunction

    setApproval: IHyperdriveSetApprovalContractFunction

    setApprovalBridge: IHyperdriveSetApprovalBridgeContractFunction

    setApprovalForAll: IHyperdriveSetApprovalForAllContractFunction

    setGovernance: IHyperdriveSetGovernanceContractFunction

    setPauser: IHyperdriveSetPauserContractFunction

    symbol: IHyperdriveSymbolContractFunction

    totalSupply: IHyperdriveTotalSupplyContractFunction

    transferFrom: IHyperdriveTransferFromContractFunction

    transferFromBridge: IHyperdriveTransferFromBridgeContractFunction


class IHyperdriveContract(Contract):
    """A web3.py Contract class for the IHyperdrive contract."""

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

    functions: IHyperdriveContractFunctions

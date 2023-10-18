"""A web3.py Contract class for the IERC4626Hyperdrive contract."""
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


class IERC4626HyperdriveDOMAIN_SEPARATORContractFunction(ContractFunction):
    """ContractFunction for the DOMAIN_SEPARATOR method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveDOMAIN_SEPARATORContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveAddLiquidityContractFunction(ContractFunction):
    """ContractFunction for the addLiquidity method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _contribution: int,
        _minApr: int,
        _maxApr: int,
        _destination: str,
        _asUnderlying: bool,
    ) -> "IERC4626HyperdriveAddLiquidityContractFunction":
        super().__call__(_contribution, _minApr, _maxApr, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveBalanceOfContractFunction(ContractFunction):
    """ContractFunction for the balanceOf method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenId: int, owner: str) -> "IERC4626HyperdriveBalanceOfContractFunction":
        super().__call__(tokenId, owner)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveBaseTokenContractFunction(ContractFunction):
    """ContractFunction for the baseToken method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveBaseTokenContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveBatchTransferFromContractFunction(ContractFunction):
    """ContractFunction for the batchTransferFrom method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _from: str, to: str, ids: list[int], values: list[int]
    ) -> "IERC4626HyperdriveBatchTransferFromContractFunction":
        super().__call__(_from, to, ids, values)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveCheckpointContractFunction(ContractFunction):
    """ContractFunction for the checkpoint method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _checkpointTime: int) -> "IERC4626HyperdriveCheckpointContractFunction":
        super().__call__(_checkpointTime)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveCloseLongContractFunction(ContractFunction):
    """ContractFunction for the closeLong method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _maturityTime: int,
        _bondAmount: int,
        _minOutput: int,
        _destination: str,
        _asUnderlying: bool,
    ) -> "IERC4626HyperdriveCloseLongContractFunction":
        super().__call__(_maturityTime, _bondAmount, _minOutput, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveCloseShortContractFunction(ContractFunction):
    """ContractFunction for the closeShort method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _maturityTime: int,
        _bondAmount: int,
        _minOutput: int,
        _destination: str,
        _asUnderlying: bool,
    ) -> "IERC4626HyperdriveCloseShortContractFunction":
        super().__call__(_maturityTime, _bondAmount, _minOutput, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveCollectGovernanceFeeContractFunction(ContractFunction):
    """ContractFunction for the collectGovernanceFee method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, asUnderlying: bool) -> "IERC4626HyperdriveCollectGovernanceFeeContractFunction":
        super().__call__(asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveFactoryContractFunction(ContractFunction):
    """ContractFunction for the factory method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveFactoryContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveGetCheckpointContractFunction(ContractFunction):
    """ContractFunction for the getCheckpoint method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _checkpointId: int) -> "IERC4626HyperdriveGetCheckpointContractFunction":
        super().__call__(_checkpointId)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveGetMarketStateContractFunction(ContractFunction):
    """ContractFunction for the getMarketState method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveGetMarketStateContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveGetPoolConfigContractFunction(ContractFunction):
    """ContractFunction for the getPoolConfig method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveGetPoolConfigContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveGetPoolInfoContractFunction(ContractFunction):
    """ContractFunction for the getPoolInfo method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveGetPoolInfoContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveGetUncollectedGovernanceFeesContractFunction(ContractFunction):
    """ContractFunction for the getUncollectedGovernanceFees method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "IERC4626HyperdriveGetUncollectedGovernanceFeesContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveGetWithdrawPoolContractFunction(ContractFunction):
    """ContractFunction for the getWithdrawPool method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveGetWithdrawPoolContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveInitializeContractFunction(ContractFunction):
    """ContractFunction for the initialize method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _contribution: int,
        _apr: int,
        _destination: str,
        _asUnderlying: bool,
    ) -> "IERC4626HyperdriveInitializeContractFunction":
        super().__call__(_contribution, _apr, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveIsApprovedForAllContractFunction(ContractFunction):
    """ContractFunction for the isApprovedForAll method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, owner: str, spender: str) -> "IERC4626HyperdriveIsApprovedForAllContractFunction":
        super().__call__(owner, spender)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveIsSweepableContractFunction(ContractFunction):
    """ContractFunction for the isSweepable method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _target: str) -> "IERC4626HyperdriveIsSweepableContractFunction":
        super().__call__(_target)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveLinkerCodeHashContractFunction(ContractFunction):
    """ContractFunction for the linkerCodeHash method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveLinkerCodeHashContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveLoadContractFunction(ContractFunction):
    """ContractFunction for the load method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _slots: list[int]) -> "IERC4626HyperdriveLoadContractFunction":
        super().__call__(_slots)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveNameContractFunction(ContractFunction):
    """ContractFunction for the name method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _id: int) -> "IERC4626HyperdriveNameContractFunction":
        super().__call__(_id)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveNoncesContractFunction(ContractFunction):
    """ContractFunction for the nonces method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, owner: str) -> "IERC4626HyperdriveNoncesContractFunction":
        super().__call__(owner)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveOpenLongContractFunction(ContractFunction):
    """ContractFunction for the openLong method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _baseAmount: int,
        _minOutput: int,
        _minSharePrice: int,
        _destination: str,
        _asUnderlying: bool,
    ) -> "IERC4626HyperdriveOpenLongContractFunction":
        super().__call__(_baseAmount, _minOutput, _minSharePrice, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveOpenShortContractFunction(ContractFunction):
    """ContractFunction for the openShort method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _bondAmount: int,
        _maxDeposit: int,
        _minSharePrice: int,
        _destination: str,
        _asUnderlying: bool,
    ) -> "IERC4626HyperdriveOpenShortContractFunction":
        super().__call__(
            _bondAmount,
            _maxDeposit,
            _minSharePrice,
            _destination,
            _asUnderlying,
        )
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdrivePauseContractFunction(ContractFunction):
    """ContractFunction for the pause method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, status: bool) -> "IERC4626HyperdrivePauseContractFunction":
        super().__call__(status)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdrivePerTokenApprovalsContractFunction(ContractFunction):
    """ContractFunction for the perTokenApprovals method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenId: int, owner: str, spender: str) -> "IERC4626HyperdrivePerTokenApprovalsContractFunction":
        super().__call__(tokenId, owner, spender)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdrivePermitForAllContractFunction(ContractFunction):
    """ContractFunction for the permitForAll method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        owner: str,
        spender: str,
        _approved: bool,
        deadline: int,
        v: int,
        r: bytes,
        s: bytes,
    ) -> "IERC4626HyperdrivePermitForAllContractFunction":
        super().__call__(owner, spender, _approved, deadline, v, r, s)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdrivePoolContractFunction(ContractFunction):
    """ContractFunction for the pool method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdrivePoolContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveRedeemWithdrawalSharesContractFunction(ContractFunction):
    """ContractFunction for the redeemWithdrawalShares method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _shares: int,
        _minOutput: int,
        _destination: str,
        _asUnderlying: bool,
    ) -> "IERC4626HyperdriveRedeemWithdrawalSharesContractFunction":
        super().__call__(_shares, _minOutput, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveRemoveLiquidityContractFunction(ContractFunction):
    """ContractFunction for the removeLiquidity method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _shares: int,
        _minOutput: int,
        _destination: str,
        _asUnderlying: bool,
    ) -> "IERC4626HyperdriveRemoveLiquidityContractFunction":
        super().__call__(_shares, _minOutput, _destination, _asUnderlying)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveSetApprovalContractFunction(ContractFunction):
    """ContractFunction for the setApproval method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenID: int, operator: str, amount: int) -> "IERC4626HyperdriveSetApprovalContractFunction":
        super().__call__(tokenID, operator, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveSetApprovalBridgeContractFunction(ContractFunction):
    """ContractFunction for the setApprovalBridge method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, tokenID: int, operator: str, amount: int, caller: str
    ) -> "IERC4626HyperdriveSetApprovalBridgeContractFunction":
        super().__call__(tokenID, operator, amount, caller)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveSetApprovalForAllContractFunction(ContractFunction):
    """ContractFunction for the setApprovalForAll method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, operator: str, approved: bool) -> "IERC4626HyperdriveSetApprovalForAllContractFunction":
        super().__call__(operator, approved)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveSetGovernanceContractFunction(ContractFunction):
    """ContractFunction for the setGovernance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, who: str) -> "IERC4626HyperdriveSetGovernanceContractFunction":
        super().__call__(who)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveSetPauserContractFunction(ContractFunction):
    """ContractFunction for the setPauser method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, who: str, status: bool) -> "IERC4626HyperdriveSetPauserContractFunction":
        super().__call__(who, status)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveSweepContractFunction(ContractFunction):
    """ContractFunction for the sweep method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _target: str) -> "IERC4626HyperdriveSweepContractFunction":
        super().__call__(_target)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveSymbolContractFunction(ContractFunction):
    """ContractFunction for the symbol method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _id: int) -> "IERC4626HyperdriveSymbolContractFunction":
        super().__call__(_id)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveTotalSupplyContractFunction(ContractFunction):
    """ContractFunction for the totalSupply method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _id: int) -> "IERC4626HyperdriveTotalSupplyContractFunction":
        super().__call__(_id)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveTransferFromContractFunction(ContractFunction):
    """ContractFunction for the transferFrom method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, tokenID: int, _from: str, to: str, amount: int
    ) -> "IERC4626HyperdriveTransferFromContractFunction":
        super().__call__(tokenID, _from, to, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveTransferFromBridgeContractFunction(ContractFunction):
    """ContractFunction for the transferFromBridge method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, tokenID: int, _from: str, to: str, amount: int, caller: str
    ) -> "IERC4626HyperdriveTransferFromBridgeContractFunction":
        super().__call__(tokenID, _from, to, amount, caller)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IERC4626HyperdriveContractFunctions(ContractFunctions):
    """ContractFunctions for the IERC4626Hyperdrive contract."""

    DOMAIN_SEPARATOR: IERC4626HyperdriveDOMAIN_SEPARATORContractFunction

    addLiquidity: IERC4626HyperdriveAddLiquidityContractFunction

    balanceOf: IERC4626HyperdriveBalanceOfContractFunction

    baseToken: IERC4626HyperdriveBaseTokenContractFunction

    batchTransferFrom: IERC4626HyperdriveBatchTransferFromContractFunction

    checkpoint: IERC4626HyperdriveCheckpointContractFunction

    closeLong: IERC4626HyperdriveCloseLongContractFunction

    closeShort: IERC4626HyperdriveCloseShortContractFunction

    collectGovernanceFee: IERC4626HyperdriveCollectGovernanceFeeContractFunction

    factory: IERC4626HyperdriveFactoryContractFunction

    getCheckpoint: IERC4626HyperdriveGetCheckpointContractFunction

    getMarketState: IERC4626HyperdriveGetMarketStateContractFunction

    getPoolConfig: IERC4626HyperdriveGetPoolConfigContractFunction

    getPoolInfo: IERC4626HyperdriveGetPoolInfoContractFunction

    getUncollectedGovernanceFees: IERC4626HyperdriveGetUncollectedGovernanceFeesContractFunction

    getWithdrawPool: IERC4626HyperdriveGetWithdrawPoolContractFunction

    initialize: IERC4626HyperdriveInitializeContractFunction

    isApprovedForAll: IERC4626HyperdriveIsApprovedForAllContractFunction

    isSweepable: IERC4626HyperdriveIsSweepableContractFunction

    linkerCodeHash: IERC4626HyperdriveLinkerCodeHashContractFunction

    load: IERC4626HyperdriveLoadContractFunction

    name: IERC4626HyperdriveNameContractFunction

    nonces: IERC4626HyperdriveNoncesContractFunction

    openLong: IERC4626HyperdriveOpenLongContractFunction

    openShort: IERC4626HyperdriveOpenShortContractFunction

    pause: IERC4626HyperdrivePauseContractFunction

    perTokenApprovals: IERC4626HyperdrivePerTokenApprovalsContractFunction

    permitForAll: IERC4626HyperdrivePermitForAllContractFunction

    pool: IERC4626HyperdrivePoolContractFunction

    redeemWithdrawalShares: IERC4626HyperdriveRedeemWithdrawalSharesContractFunction

    removeLiquidity: IERC4626HyperdriveRemoveLiquidityContractFunction

    setApproval: IERC4626HyperdriveSetApprovalContractFunction

    setApprovalBridge: IERC4626HyperdriveSetApprovalBridgeContractFunction

    setApprovalForAll: IERC4626HyperdriveSetApprovalForAllContractFunction

    setGovernance: IERC4626HyperdriveSetGovernanceContractFunction

    setPauser: IERC4626HyperdriveSetPauserContractFunction

    sweep: IERC4626HyperdriveSweepContractFunction

    symbol: IERC4626HyperdriveSymbolContractFunction

    totalSupply: IERC4626HyperdriveTotalSupplyContractFunction

    transferFrom: IERC4626HyperdriveTransferFromContractFunction

    transferFromBridge: IERC4626HyperdriveTransferFromBridgeContractFunction


class IERC4626HyperdriveContract(Contract):
    """A web3.py Contract class for the IERC4626Hyperdrive contract."""

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

    functions: IERC4626HyperdriveContractFunctions

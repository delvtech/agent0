"""A web3.py Contract class for the IHyperdrive contract."""

# contracts have PascalCase names
# pylint: disable=invalid-name

# contracts control how many attributes and arguments we have in generated code
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments

# we don't need else statement if the other conditionals all have return,
# but it's easier to generate
# pylint: disable=no-else-return

# This file is bound to get very long depending on contract sizes.
# pylint: disable=too-many-lines

from __future__ import annotations
from typing import cast

from eth_typing import ChecksumAddress
from web3.types import ABI
from web3.contract.contract import Contract, ContractFunction, ContractFunctions
from web3.exceptions import FallbackNotFound


class IHyperdriveDOMAIN_SEPARATORContractFunction(ContractFunction):
    """ContractFunction for the DOMAIN_SEPARATOR method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IHyperdriveDOMAIN_SEPARATORContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveAddLiquidityContractFunction(ContractFunction):
    """ContractFunction for the addLiquidity method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _contribution: int, _minApr: int, _maxApr: int, _options: tuple
    ) -> "IHyperdriveAddLiquidityContractFunction":
        super().__call__(_contribution, _minApr, _maxApr, _options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveBalanceOfContractFunction(ContractFunction):
    """ContractFunction for the balanceOf method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenId: int, owner: str) -> "IHyperdriveBalanceOfContractFunction":
        super().__call__(tokenId, owner)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveBaseTokenContractFunction(ContractFunction):
    """ContractFunction for the baseToken method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IHyperdriveBaseTokenContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveBatchTransferFromContractFunction(ContractFunction):
    """ContractFunction for the batchTransferFrom method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _from: str, to: str, ids: list[int], values: list[int]
    ) -> "IHyperdriveBatchTransferFromContractFunction":
        super().__call__(_from, to, ids, values)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveCheckpointContractFunction(ContractFunction):
    """ContractFunction for the checkpoint method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _checkpointTime: int) -> "IHyperdriveCheckpointContractFunction":
        super().__call__(_checkpointTime)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveCloseLongContractFunction(ContractFunction):
    """ContractFunction for the closeLong method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _maturityTime: int,
        _bondAmount: int,
        _minOutput: int,
        _options: tuple,
    ) -> "IHyperdriveCloseLongContractFunction":
        super().__call__(_maturityTime, _bondAmount, _minOutput, _options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveCloseShortContractFunction(ContractFunction):
    """ContractFunction for the closeShort method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _maturityTime: int,
        _bondAmount: int,
        _minOutput: int,
        _options: tuple,
    ) -> "IHyperdriveCloseShortContractFunction":
        super().__call__(_maturityTime, _bondAmount, _minOutput, _options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveCollectGovernanceFeeContractFunction(ContractFunction):
    """ContractFunction for the collectGovernanceFee method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _options: tuple) -> "IHyperdriveCollectGovernanceFeeContractFunction":
        super().__call__(_options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveDataProviderContractFunction(ContractFunction):
    """ContractFunction for the dataProvider method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IHyperdriveDataProviderContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveFactoryContractFunction(ContractFunction):
    """ContractFunction for the factory method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IHyperdriveFactoryContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveGetCheckpointContractFunction(ContractFunction):
    """ContractFunction for the getCheckpoint method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _checkpointId: int) -> "IHyperdriveGetCheckpointContractFunction":
        super().__call__(_checkpointId)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveGetMarketStateContractFunction(ContractFunction):
    """ContractFunction for the getMarketState method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IHyperdriveGetMarketStateContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveGetPoolConfigContractFunction(ContractFunction):
    """ContractFunction for the getPoolConfig method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IHyperdriveGetPoolConfigContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveGetPoolInfoContractFunction(ContractFunction):
    """ContractFunction for the getPoolInfo method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IHyperdriveGetPoolInfoContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveGetUncollectedGovernanceFeesContractFunction(ContractFunction):
    """ContractFunction for the getUncollectedGovernanceFees method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "IHyperdriveGetUncollectedGovernanceFeesContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveGetWithdrawPoolContractFunction(ContractFunction):
    """ContractFunction for the getWithdrawPool method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IHyperdriveGetWithdrawPoolContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveInitializeContractFunction(ContractFunction):
    """ContractFunction for the initialize method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _contribution: int, _apr: int, _options: tuple) -> "IHyperdriveInitializeContractFunction":
        super().__call__(_contribution, _apr, _options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveIsApprovedForAllContractFunction(ContractFunction):
    """ContractFunction for the isApprovedForAll method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, owner: str, spender: str) -> "IHyperdriveIsApprovedForAllContractFunction":
        super().__call__(owner, spender)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveLinkerCodeHashContractFunction(ContractFunction):
    """ContractFunction for the linkerCodeHash method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IHyperdriveLinkerCodeHashContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveLoadContractFunction(ContractFunction):
    """ContractFunction for the load method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _slots: list[int]) -> "IHyperdriveLoadContractFunction":
        super().__call__(_slots)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveNameContractFunction(ContractFunction):
    """ContractFunction for the name method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _id: int) -> "IHyperdriveNameContractFunction":
        super().__call__(_id)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveNoncesContractFunction(ContractFunction):
    """ContractFunction for the nonces method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, owner: str) -> "IHyperdriveNoncesContractFunction":
        super().__call__(owner)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveOpenLongContractFunction(ContractFunction):
    """ContractFunction for the openLong method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _baseAmount: int,
        _minOutput: int,
        _minSharePrice: int,
        _options: tuple,
    ) -> "IHyperdriveOpenLongContractFunction":
        super().__call__(_baseAmount, _minOutput, _minSharePrice, _options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveOpenShortContractFunction(ContractFunction):
    """ContractFunction for the openShort method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _bondAmount: int,
        _maxDeposit: int,
        _minSharePrice: int,
        _options: tuple,
    ) -> "IHyperdriveOpenShortContractFunction":
        super().__call__(_bondAmount, _maxDeposit, _minSharePrice, _options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdrivePauseContractFunction(ContractFunction):
    """ContractFunction for the pause method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _status: bool) -> "IHyperdrivePauseContractFunction":
        super().__call__(_status)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdrivePerTokenApprovalsContractFunction(ContractFunction):
    """ContractFunction for the perTokenApprovals method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenId: int, owner: str, spender: str) -> "IHyperdrivePerTokenApprovalsContractFunction":
        super().__call__(tokenId, owner, spender)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdrivePermitForAllContractFunction(ContractFunction):
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
    ) -> "IHyperdrivePermitForAllContractFunction":
        super().__call__(owner, spender, _approved, deadline, v, r, s)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveRedeemWithdrawalSharesContractFunction(ContractFunction):
    """ContractFunction for the redeemWithdrawalShares method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _shares: int, _minOutput: int, _options: tuple
    ) -> "IHyperdriveRedeemWithdrawalSharesContractFunction":
        super().__call__(_shares, _minOutput, _options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveRemoveLiquidityContractFunction(ContractFunction):
    """ContractFunction for the removeLiquidity method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _shares: int, _minOutput: int, _options: tuple) -> "IHyperdriveRemoveLiquidityContractFunction":
        super().__call__(_shares, _minOutput, _options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveSetApprovalContractFunction(ContractFunction):
    """ContractFunction for the setApproval method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenID: int, operator: str, amount: int) -> "IHyperdriveSetApprovalContractFunction":
        super().__call__(tokenID, operator, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveSetApprovalBridgeContractFunction(ContractFunction):
    """ContractFunction for the setApprovalBridge method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, tokenID: int, operator: str, amount: int, caller: str
    ) -> "IHyperdriveSetApprovalBridgeContractFunction":
        super().__call__(tokenID, operator, amount, caller)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveSetApprovalForAllContractFunction(ContractFunction):
    """ContractFunction for the setApprovalForAll method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, operator: str, approved: bool) -> "IHyperdriveSetApprovalForAllContractFunction":
        super().__call__(operator, approved)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveSetGovernanceContractFunction(ContractFunction):
    """ContractFunction for the setGovernance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _who: str) -> "IHyperdriveSetGovernanceContractFunction":
        super().__call__(_who)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveSetPauserContractFunction(ContractFunction):
    """ContractFunction for the setPauser method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _who: str, _status: bool) -> "IHyperdriveSetPauserContractFunction":
        super().__call__(_who, _status)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveSymbolContractFunction(ContractFunction):
    """ContractFunction for the symbol method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _id: int) -> "IHyperdriveSymbolContractFunction":
        super().__call__(_id)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveTotalSupplyContractFunction(ContractFunction):
    """ContractFunction for the totalSupply method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _id: int) -> "IHyperdriveTotalSupplyContractFunction":
        super().__call__(_id)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveTransferFromContractFunction(ContractFunction):
    """ContractFunction for the transferFrom method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenID: int, _from: str, to: str, amount: int) -> "IHyperdriveTransferFromContractFunction":
        super().__call__(tokenID, _from, to, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class IHyperdriveTransferFromBridgeContractFunction(ContractFunction):
    """ContractFunction for the transferFromBridge method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

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

    dataProvider: IHyperdriveDataProviderContractFunction

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


ihyperdrive_abi: ABI = cast(
    ABI,
    [
        {"inputs": [], "name": "AlreadyClosed", "type": "error"},
        {"inputs": [], "name": "ApprovalFailed", "type": "error"},
        {
            "inputs": [],
            "name": "BaseBufferExceedsShareReserves",
            "type": "error",
        },
        {"inputs": [], "name": "BatchInputLengthMismatch", "type": "error"},
        {"inputs": [], "name": "BelowMinimumContribution", "type": "error"},
        {"inputs": [], "name": "BelowMinimumShareReserves", "type": "error"},
        {"inputs": [], "name": "BondMatured", "type": "error"},
        {"inputs": [], "name": "BondNotMatured", "type": "error"},
        {
            "inputs": [
                {
                    "internalType": "bytes4",
                    "name": "underlyingError",
                    "type": "bytes4",
                }
            ],
            "name": "CallFailed",
            "type": "error",
        },
        {"inputs": [], "name": "ExpiredDeadline", "type": "error"},
        {"inputs": [], "name": "FeeTooHigh", "type": "error"},
        {
            "inputs": [],
            "name": "FixedPointMath_InvalidExponent",
            "type": "error",
        },
        {"inputs": [], "name": "FixedPointMath_InvalidInput", "type": "error"},
        {"inputs": [], "name": "FixedPointMath_NegativeInput", "type": "error"},
        {
            "inputs": [],
            "name": "FixedPointMath_NegativeOrZeroInput",
            "type": "error",
        },
        {"inputs": [], "name": "InputLengthMismatch", "type": "error"},
        {"inputs": [], "name": "InsufficientPrice", "type": "error"},
        {"inputs": [], "name": "InvalidApr", "type": "error"},
        {"inputs": [], "name": "InvalidBaseToken", "type": "error"},
        {"inputs": [], "name": "InvalidCheckpointDuration", "type": "error"},
        {"inputs": [], "name": "InvalidCheckpointTime", "type": "error"},
        {"inputs": [], "name": "InvalidContribution", "type": "error"},
        {"inputs": [], "name": "InvalidERC20Bridge", "type": "error"},
        {"inputs": [], "name": "InvalidFeeAmounts", "type": "error"},
        {"inputs": [], "name": "InvalidFeeDestination", "type": "error"},
        {"inputs": [], "name": "InvalidForwarderAddress", "type": "error"},
        {"inputs": [], "name": "InvalidInitialSharePrice", "type": "error"},
        {"inputs": [], "name": "InvalidMaturityTime", "type": "error"},
        {"inputs": [], "name": "InvalidMinimumShareReserves", "type": "error"},
        {"inputs": [], "name": "InvalidPositionDuration", "type": "error"},
        {"inputs": [], "name": "InvalidShareReserves", "type": "error"},
        {"inputs": [], "name": "InvalidSignature", "type": "error"},
        {"inputs": [], "name": "InvalidTimestamp", "type": "error"},
        {"inputs": [], "name": "InvalidToken", "type": "error"},
        {"inputs": [], "name": "InvalidTradeSize", "type": "error"},
        {"inputs": [], "name": "MaxFeeTooHigh", "type": "error"},
        {"inputs": [], "name": "MinimumSharePrice", "type": "error"},
        {"inputs": [], "name": "MinimumTransactionAmount", "type": "error"},
        {"inputs": [], "name": "MintPercentTooHigh", "type": "error"},
        {"inputs": [], "name": "NegativeInterest", "type": "error"},
        {"inputs": [], "name": "NegativePresentValue", "type": "error"},
        {"inputs": [], "name": "NoAssetsToWithdraw", "type": "error"},
        {"inputs": [], "name": "NonPayableInitialization", "type": "error"},
        {"inputs": [], "name": "NotPayable", "type": "error"},
        {"inputs": [], "name": "OutputLimit", "type": "error"},
        {"inputs": [], "name": "Paused", "type": "error"},
        {"inputs": [], "name": "PoolAlreadyInitialized", "type": "error"},
        {"inputs": [], "name": "QueryOutOfRange", "type": "error"},
        {"inputs": [], "name": "RestrictedZeroAddress", "type": "error"},
        {
            "inputs": [{"internalType": "bytes", "name": "data", "type": "bytes"}],
            "name": "ReturnData",
            "type": "error",
        },
        {
            "inputs": [],
            "name": "ShareReservesDeltaExceedsBondReservesDelta",
            "type": "error",
        },
        {"inputs": [], "name": "TransferFailed", "type": "error"},
        {"inputs": [], "name": "Unauthorized", "type": "error"},
        {"inputs": [], "name": "UnexpectedAssetId", "type": "error"},
        {"inputs": [], "name": "UnexpectedSender", "type": "error"},
        {"inputs": [], "name": "UnexpectedSuccess", "type": "error"},
        {"inputs": [], "name": "UnsafeCastToInt128", "type": "error"},
        {"inputs": [], "name": "UnsafeCastToUint128", "type": "error"},
        {"inputs": [], "name": "UnsupportedToken", "type": "error"},
        {"inputs": [], "name": "ZeroLpTotalSupply", "type": "error"},
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "provider",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "lpAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "lpSharePrice",
                    "type": "uint256",
                },
            ],
            "name": "AddLiquidity",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "owner",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "spender",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "value",
                    "type": "uint256",
                },
            ],
            "name": "Approval",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "account",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "operator",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "bool",
                    "name": "approved",
                    "type": "bool",
                },
            ],
            "name": "ApprovalForAll",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "trader",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "uint256",
                    "name": "assetId",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "maturityTime",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "bondAmount",
                    "type": "uint256",
                },
            ],
            "name": "CloseLong",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "trader",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "uint256",
                    "name": "assetId",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "maturityTime",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "bondAmount",
                    "type": "uint256",
                },
            ],
            "name": "CloseShort",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "collector",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseFees",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
            ],
            "name": "CollectGovernanceFee",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "uint256",
                    "name": "checkpointTime",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "maturedShorts",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "maturedLongs",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "lpSharePrice",
                    "type": "uint256",
                },
            ],
            "name": "CreateCheckpoint",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "provider",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "lpAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "apr",
                    "type": "uint256",
                },
            ],
            "name": "Initialize",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "trader",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "uint256",
                    "name": "assetId",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "maturityTime",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "bondAmount",
                    "type": "uint256",
                },
            ],
            "name": "OpenLong",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "trader",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "uint256",
                    "name": "assetId",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "maturityTime",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "bondAmount",
                    "type": "uint256",
                },
            ],
            "name": "OpenShort",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "provider",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "withdrawalShareAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
            ],
            "name": "RedeemWithdrawalShares",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "provider",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "lpAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "withdrawalShareAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "lpSharePrice",
                    "type": "uint256",
                },
            ],
            "name": "RemoveLiquidity",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "operator",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "from",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "to",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "id",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "value",
                    "type": "uint256",
                },
            ],
            "name": "TransferSingle",
            "type": "event",
        },
        {
            "inputs": [],
            "name": "DOMAIN_SEPARATOR",
            "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_contribution",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minApr",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_maxApr",
                    "type": "uint256",
                },
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "addLiquidity",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "lpShares",
                    "type": "uint256",
                }
            ],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenId",
                    "type": "uint256",
                },
                {"internalType": "address", "name": "owner", "type": "address"},
            ],
            "name": "balanceOf",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "baseToken",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "from", "type": "address"},
                {"internalType": "address", "name": "to", "type": "address"},
                {
                    "internalType": "uint256[]",
                    "name": "ids",
                    "type": "uint256[]",
                },
                {
                    "internalType": "uint256[]",
                    "name": "values",
                    "type": "uint256[]",
                },
            ],
            "name": "batchTransferFrom",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_checkpointTime",
                    "type": "uint256",
                }
            ],
            "name": "checkpoint",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_maturityTime",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_bondAmount",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minOutput",
                    "type": "uint256",
                },
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "closeLong",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_maturityTime",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_bondAmount",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minOutput",
                    "type": "uint256",
                },
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "closeShort",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                }
            ],
            "name": "collectGovernanceFee",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "proceeds",
                    "type": "uint256",
                }
            ],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "dataProvider",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "factory",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_checkpointId",
                    "type": "uint256",
                }
            ],
            "name": "getCheckpoint",
            "outputs": [
                {
                    "components": [
                        {
                            "internalType": "uint128",
                            "name": "sharePrice",
                            "type": "uint128",
                        },
                        {
                            "internalType": "int128",
                            "name": "longExposure",
                            "type": "int128",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Checkpoint",
                    "name": "",
                    "type": "tuple",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getMarketState",
            "outputs": [
                {
                    "components": [
                        {
                            "internalType": "uint128",
                            "name": "shareReserves",
                            "type": "uint128",
                        },
                        {
                            "internalType": "uint128",
                            "name": "bondReserves",
                            "type": "uint128",
                        },
                        {
                            "internalType": "int128",
                            "name": "shareAdjustment",
                            "type": "int128",
                        },
                        {
                            "internalType": "uint128",
                            "name": "longExposure",
                            "type": "uint128",
                        },
                        {
                            "internalType": "uint128",
                            "name": "longsOutstanding",
                            "type": "uint128",
                        },
                        {
                            "internalType": "uint128",
                            "name": "shortsOutstanding",
                            "type": "uint128",
                        },
                        {
                            "internalType": "uint128",
                            "name": "longAverageMaturityTime",
                            "type": "uint128",
                        },
                        {
                            "internalType": "uint128",
                            "name": "shortAverageMaturityTime",
                            "type": "uint128",
                        },
                        {
                            "internalType": "bool",
                            "name": "isInitialized",
                            "type": "bool",
                        },
                        {
                            "internalType": "bool",
                            "name": "isPaused",
                            "type": "bool",
                        },
                    ],
                    "internalType": "struct IHyperdrive.MarketState",
                    "name": "",
                    "type": "tuple",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getPoolConfig",
            "outputs": [
                {
                    "components": [
                        {
                            "internalType": "contract IERC20",
                            "name": "baseToken",
                            "type": "address",
                        },
                        {
                            "internalType": "uint256",
                            "name": "initialSharePrice",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "minimumShareReserves",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "minimumTransactionAmount",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "positionDuration",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "checkpointDuration",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "timeStretch",
                            "type": "uint256",
                        },
                        {
                            "internalType": "address",
                            "name": "governance",
                            "type": "address",
                        },
                        {
                            "internalType": "address",
                            "name": "feeCollector",
                            "type": "address",
                        },
                        {
                            "components": [
                                {
                                    "internalType": "uint256",
                                    "name": "curve",
                                    "type": "uint256",
                                },
                                {
                                    "internalType": "uint256",
                                    "name": "flat",
                                    "type": "uint256",
                                },
                                {
                                    "internalType": "uint256",
                                    "name": "governance",
                                    "type": "uint256",
                                },
                            ],
                            "internalType": "struct IHyperdrive.Fees",
                            "name": "fees",
                            "type": "tuple",
                        },
                        {
                            "internalType": "uint256",
                            "name": "oracleSize",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "updateGap",
                            "type": "uint256",
                        },
                    ],
                    "internalType": "struct IHyperdrive.PoolConfig",
                    "name": "",
                    "type": "tuple",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getPoolInfo",
            "outputs": [
                {
                    "components": [
                        {
                            "internalType": "uint256",
                            "name": "shareReserves",
                            "type": "uint256",
                        },
                        {
                            "internalType": "int256",
                            "name": "shareAdjustment",
                            "type": "int256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "bondReserves",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "lpTotalSupply",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "sharePrice",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "longsOutstanding",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "longAverageMaturityTime",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "shortsOutstanding",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "shortAverageMaturityTime",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "withdrawalSharesReadyToWithdraw",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "withdrawalSharesProceeds",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "lpSharePrice",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "longExposure",
                            "type": "uint256",
                        },
                    ],
                    "internalType": "struct IHyperdrive.PoolInfo",
                    "name": "",
                    "type": "tuple",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getUncollectedGovernanceFees",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getWithdrawPool",
            "outputs": [
                {
                    "components": [
                        {
                            "internalType": "uint128",
                            "name": "readyToWithdraw",
                            "type": "uint128",
                        },
                        {
                            "internalType": "uint128",
                            "name": "proceeds",
                            "type": "uint128",
                        },
                    ],
                    "internalType": "struct IHyperdrive.WithdrawPool",
                    "name": "",
                    "type": "tuple",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_contribution",
                    "type": "uint256",
                },
                {"internalType": "uint256", "name": "_apr", "type": "uint256"},
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "initialize",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "lpShares",
                    "type": "uint256",
                }
            ],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "owner", "type": "address"},
                {
                    "internalType": "address",
                    "name": "spender",
                    "type": "address",
                },
            ],
            "name": "isApprovedForAll",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "linkerCodeHash",
            "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256[]",
                    "name": "_slots",
                    "type": "uint256[]",
                }
            ],
            "name": "load",
            "outputs": [{"internalType": "bytes32[]", "name": "", "type": "bytes32[]"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
            "name": "name",
            "outputs": [{"internalType": "string", "name": "", "type": "string"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
            "name": "nonces",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_baseAmount",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minOutput",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minSharePrice",
                    "type": "uint256",
                },
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "openLong",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "maturityTime",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "bondProceeds",
                    "type": "uint256",
                },
            ],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_bondAmount",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_maxDeposit",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minSharePrice",
                    "type": "uint256",
                },
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "openShort",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "maturityTime",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "traderDeposit",
                    "type": "uint256",
                },
            ],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "bool", "name": "_status", "type": "bool"}],
            "name": "pause",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenId",
                    "type": "uint256",
                },
                {"internalType": "address", "name": "owner", "type": "address"},
                {
                    "internalType": "address",
                    "name": "spender",
                    "type": "address",
                },
            ],
            "name": "perTokenApprovals",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "owner", "type": "address"},
                {
                    "internalType": "address",
                    "name": "spender",
                    "type": "address",
                },
                {"internalType": "bool", "name": "_approved", "type": "bool"},
                {
                    "internalType": "uint256",
                    "name": "deadline",
                    "type": "uint256",
                },
                {"internalType": "uint8", "name": "v", "type": "uint8"},
                {"internalType": "bytes32", "name": "r", "type": "bytes32"},
                {"internalType": "bytes32", "name": "s", "type": "bytes32"},
            ],
            "name": "permitForAll",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_shares",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minOutput",
                    "type": "uint256",
                },
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "redeemWithdrawalShares",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "proceeds",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "sharesRedeemed",
                    "type": "uint256",
                },
            ],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_shares",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minOutput",
                    "type": "uint256",
                },
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "removeLiquidity",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "baseProceeds",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "withdrawalShares",
                    "type": "uint256",
                },
            ],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenID",
                    "type": "uint256",
                },
                {
                    "internalType": "address",
                    "name": "operator",
                    "type": "address",
                },
                {
                    "internalType": "uint256",
                    "name": "amount",
                    "type": "uint256",
                },
            ],
            "name": "setApproval",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenID",
                    "type": "uint256",
                },
                {
                    "internalType": "address",
                    "name": "operator",
                    "type": "address",
                },
                {
                    "internalType": "uint256",
                    "name": "amount",
                    "type": "uint256",
                },
                {
                    "internalType": "address",
                    "name": "caller",
                    "type": "address",
                },
            ],
            "name": "setApprovalBridge",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "address",
                    "name": "operator",
                    "type": "address",
                },
                {"internalType": "bool", "name": "approved", "type": "bool"},
            ],
            "name": "setApprovalForAll",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "address", "name": "_who", "type": "address"}],
            "name": "setGovernance",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "_who", "type": "address"},
                {"internalType": "bool", "name": "_status", "type": "bool"},
            ],
            "name": "setPauser",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
            "name": "symbol",
            "outputs": [{"internalType": "string", "name": "", "type": "string"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
            "name": "totalSupply",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenID",
                    "type": "uint256",
                },
                {"internalType": "address", "name": "from", "type": "address"},
                {"internalType": "address", "name": "to", "type": "address"},
                {
                    "internalType": "uint256",
                    "name": "amount",
                    "type": "uint256",
                },
            ],
            "name": "transferFrom",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenID",
                    "type": "uint256",
                },
                {"internalType": "address", "name": "from", "type": "address"},
                {"internalType": "address", "name": "to", "type": "address"},
                {
                    "internalType": "uint256",
                    "name": "amount",
                    "type": "uint256",
                },
                {
                    "internalType": "address",
                    "name": "caller",
                    "type": "address",
                },
            ],
            "name": "transferFromBridge",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ],
)


class IHyperdriveContract(Contract):
    """A web3.py Contract class for the IHyperdrive contract."""

    abi: ABI = ihyperdrive_abi

    def __init__(self, address: ChecksumAddress | None = None) -> None:
        try:
            # Initialize parent Contract class
            super().__init__(address=address)

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    # TODO: add events
    # events: ERC20ContractEvents

    functions: IHyperdriveContractFunctions

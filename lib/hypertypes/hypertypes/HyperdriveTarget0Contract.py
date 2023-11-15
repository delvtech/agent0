"""A web3.py Contract class for the HyperdriveTarget0 contract."""

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


class HyperdriveTarget0BalanceOfContractFunction(ContractFunction):
    """ContractFunction for the balanceOf method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenId: int, account: str) -> "HyperdriveTarget0BalanceOfContractFunction":
        super().__call__(tokenId, account)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0BaseTokenContractFunction(ContractFunction):
    """ContractFunction for the baseToken method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "HyperdriveTarget0BaseTokenContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0BatchTransferFromContractFunction(ContractFunction):
    """ContractFunction for the batchTransferFrom method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _from: str, to: str, ids: list[int], values: list[int]
    ) -> "HyperdriveTarget0BatchTransferFromContractFunction":
        super().__call__(_from, to, ids, values)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0CollectGovernanceFeeContractFunction(ContractFunction):
    """ContractFunction for the collectGovernanceFee method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _options: tuple) -> "HyperdriveTarget0CollectGovernanceFeeContractFunction":
        super().__call__(_options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0GetCheckpointContractFunction(ContractFunction):
    """ContractFunction for the getCheckpoint method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _checkpointId: int) -> "HyperdriveTarget0GetCheckpointContractFunction":
        super().__call__(_checkpointId)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0GetMarketStateContractFunction(ContractFunction):
    """ContractFunction for the getMarketState method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "HyperdriveTarget0GetMarketStateContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0GetPoolConfigContractFunction(ContractFunction):
    """ContractFunction for the getPoolConfig method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "HyperdriveTarget0GetPoolConfigContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0GetPoolInfoContractFunction(ContractFunction):
    """ContractFunction for the getPoolInfo method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "HyperdriveTarget0GetPoolInfoContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0GetUncollectedGovernanceFeesContractFunction(ContractFunction):
    """ContractFunction for the getUncollectedGovernanceFees method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "HyperdriveTarget0GetUncollectedGovernanceFeesContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0GetWithdrawPoolContractFunction(ContractFunction):
    """ContractFunction for the getWithdrawPool method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "HyperdriveTarget0GetWithdrawPoolContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0IsApprovedForAllContractFunction(ContractFunction):
    """ContractFunction for the isApprovedForAll method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, account: str, operator: str) -> "HyperdriveTarget0IsApprovedForAllContractFunction":
        super().__call__(account, operator)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0LoadContractFunction(ContractFunction):
    """ContractFunction for the load method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _slots: list[int]) -> "HyperdriveTarget0LoadContractFunction":
        super().__call__(_slots)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0NameContractFunction(ContractFunction):
    """ContractFunction for the name method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenId: int) -> "HyperdriveTarget0NameContractFunction":
        super().__call__(tokenId)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0NoncesContractFunction(ContractFunction):
    """ContractFunction for the nonces method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, account: str) -> "HyperdriveTarget0NoncesContractFunction":
        super().__call__(account)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0PauseContractFunction(ContractFunction):
    """ContractFunction for the pause method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _status: bool) -> "HyperdriveTarget0PauseContractFunction":
        super().__call__(_status)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0PerTokenApprovalsContractFunction(ContractFunction):
    """ContractFunction for the perTokenApprovals method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, tokenId: int, account: str, spender: str
    ) -> "HyperdriveTarget0PerTokenApprovalsContractFunction":
        super().__call__(tokenId, account, spender)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0SetApprovalContractFunction(ContractFunction):
    """ContractFunction for the setApproval method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenID: int, operator: str, amount: int) -> "HyperdriveTarget0SetApprovalContractFunction":
        super().__call__(tokenID, operator, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0SetApprovalBridgeContractFunction(ContractFunction):
    """ContractFunction for the setApprovalBridge method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, tokenID: int, operator: str, amount: int, caller: str
    ) -> "HyperdriveTarget0SetApprovalBridgeContractFunction":
        super().__call__(tokenID, operator, amount, caller)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0SetApprovalForAllContractFunction(ContractFunction):
    """ContractFunction for the setApprovalForAll method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, operator: str, approved: bool) -> "HyperdriveTarget0SetApprovalForAllContractFunction":
        super().__call__(operator, approved)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0SetGovernanceContractFunction(ContractFunction):
    """ContractFunction for the setGovernance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _who: str) -> "HyperdriveTarget0SetGovernanceContractFunction":
        super().__call__(_who)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0SetPauserContractFunction(ContractFunction):
    """ContractFunction for the setPauser method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, who: str, status: bool) -> "HyperdriveTarget0SetPauserContractFunction":
        super().__call__(who, status)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0SymbolContractFunction(ContractFunction):
    """ContractFunction for the symbol method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenId: int) -> "HyperdriveTarget0SymbolContractFunction":
        super().__call__(tokenId)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0TotalSupplyContractFunction(ContractFunction):
    """ContractFunction for the totalSupply method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenId: int) -> "HyperdriveTarget0TotalSupplyContractFunction":
        super().__call__(tokenId)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0TransferFromContractFunction(ContractFunction):
    """ContractFunction for the transferFrom method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, tokenID: int, _from: str, to: str, amount: int
    ) -> "HyperdriveTarget0TransferFromContractFunction":
        super().__call__(tokenID, _from, to, amount)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0TransferFromBridgeContractFunction(ContractFunction):
    """ContractFunction for the transferFromBridge method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, tokenID: int, _from: str, to: str, amount: int, caller: str
    ) -> "HyperdriveTarget0TransferFromBridgeContractFunction":
        super().__call__(tokenID, _from, to, amount, caller)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget0ContractFunctions(ContractFunctions):
    """ContractFunctions for the HyperdriveTarget0 contract."""

    balanceOf: HyperdriveTarget0BalanceOfContractFunction

    baseToken: HyperdriveTarget0BaseTokenContractFunction

    batchTransferFrom: HyperdriveTarget0BatchTransferFromContractFunction

    collectGovernanceFee: HyperdriveTarget0CollectGovernanceFeeContractFunction

    getCheckpoint: HyperdriveTarget0GetCheckpointContractFunction

    getMarketState: HyperdriveTarget0GetMarketStateContractFunction

    getPoolConfig: HyperdriveTarget0GetPoolConfigContractFunction

    getPoolInfo: HyperdriveTarget0GetPoolInfoContractFunction

    getUncollectedGovernanceFees: HyperdriveTarget0GetUncollectedGovernanceFeesContractFunction

    getWithdrawPool: HyperdriveTarget0GetWithdrawPoolContractFunction

    isApprovedForAll: HyperdriveTarget0IsApprovedForAllContractFunction

    load: HyperdriveTarget0LoadContractFunction

    name: HyperdriveTarget0NameContractFunction

    nonces: HyperdriveTarget0NoncesContractFunction

    pause: HyperdriveTarget0PauseContractFunction

    perTokenApprovals: HyperdriveTarget0PerTokenApprovalsContractFunction

    setApproval: HyperdriveTarget0SetApprovalContractFunction

    setApprovalBridge: HyperdriveTarget0SetApprovalBridgeContractFunction

    setApprovalForAll: HyperdriveTarget0SetApprovalForAllContractFunction

    setGovernance: HyperdriveTarget0SetGovernanceContractFunction

    setPauser: HyperdriveTarget0SetPauserContractFunction

    symbol: HyperdriveTarget0SymbolContractFunction

    totalSupply: HyperdriveTarget0TotalSupplyContractFunction

    transferFrom: HyperdriveTarget0TransferFromContractFunction

    transferFromBridge: HyperdriveTarget0TransferFromBridgeContractFunction


hyperdrivetarget0_abi: ABI = cast(
    ABI,
    [
        {"inputs": [], "name": "BatchInputLengthMismatch", "type": "error"},
        {
            "inputs": [],
            "name": "FixedPointMath_InvalidExponent",
            "type": "error",
        },
        {"inputs": [], "name": "FixedPointMath_InvalidInput", "type": "error"},
        {"inputs": [], "name": "InvalidCheckpointDuration", "type": "error"},
        {"inputs": [], "name": "InvalidERC20Bridge", "type": "error"},
        {"inputs": [], "name": "InvalidFeeAmounts", "type": "error"},
        {"inputs": [], "name": "InvalidFeeDestination", "type": "error"},
        {"inputs": [], "name": "InvalidMinimumShareReserves", "type": "error"},
        {"inputs": [], "name": "InvalidPositionDuration", "type": "error"},
        {"inputs": [], "name": "InvalidTradeSize", "type": "error"},
        {"inputs": [], "name": "NegativePresentValue", "type": "error"},
        {"inputs": [], "name": "RestrictedZeroAddress", "type": "error"},
        {
            "inputs": [{"internalType": "bytes", "name": "data", "type": "bytes"}],
            "name": "ReturnData",
            "type": "error",
        },
        {"inputs": [], "name": "Unauthorized", "type": "error"},
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
                    "name": "fees",
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
                    "name": "newGovernance",
                    "type": "address",
                }
            ],
            "name": "GovernanceUpdated",
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
                    "name": "newPauser",
                    "type": "address",
                }
            ],
            "name": "PauserUpdated",
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
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenId",
                    "type": "uint256",
                },
                {
                    "internalType": "address",
                    "name": "account",
                    "type": "address",
                },
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
                            "name": "exposure",
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
                            "internalType": "address",
                            "name": "linkerFactory",
                            "type": "address",
                        },
                        {
                            "internalType": "bytes32",
                            "name": "linkerCodeHash",
                            "type": "bytes32",
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
                            "name": "precisionThreshold",
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
                    "internalType": "address",
                    "name": "account",
                    "type": "address",
                },
                {
                    "internalType": "address",
                    "name": "operator",
                    "type": "address",
                },
            ],
            "name": "isApprovedForAll",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
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
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenId",
                    "type": "uint256",
                }
            ],
            "name": "name",
            "outputs": [{"internalType": "string", "name": "", "type": "string"}],
            "stateMutability": "pure",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "address",
                    "name": "account",
                    "type": "address",
                }
            ],
            "name": "nonces",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
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
                {
                    "internalType": "address",
                    "name": "account",
                    "type": "address",
                },
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
                {"internalType": "address", "name": "who", "type": "address"},
                {"internalType": "bool", "name": "status", "type": "bool"},
            ],
            "name": "setPauser",
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
                }
            ],
            "name": "symbol",
            "outputs": [{"internalType": "string", "name": "", "type": "string"}],
            "stateMutability": "pure",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenId",
                    "type": "uint256",
                }
            ],
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


class HyperdriveTarget0Contract(Contract):
    """A web3.py Contract class for the HyperdriveTarget0 contract."""

    abi: ABI = hyperdrivetarget0_abi

    def __init__(self, address: ChecksumAddress | None = None) -> None:
        try:
            # Initialize parent Contract class
            super().__init__(address=address)

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    # TODO: add events
    # events: ERC20ContractEvents

    functions: HyperdriveTarget0ContractFunctions

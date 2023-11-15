"""A web3.py Contract class for the HyperdriveTarget1 contract."""

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


class HyperdriveTarget1AddLiquidityContractFunction(ContractFunction):
    """ContractFunction for the addLiquidity method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _contribution: int, _minApr: int, _maxApr: int, _options: tuple
    ) -> "HyperdriveTarget1AddLiquidityContractFunction":
        super().__call__(_contribution, _minApr, _maxApr, _options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget1CheckpointContractFunction(ContractFunction):
    """ContractFunction for the checkpoint method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _checkpointTime: int) -> "HyperdriveTarget1CheckpointContractFunction":
        super().__call__(_checkpointTime)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget1CloseLongContractFunction(ContractFunction):
    """ContractFunction for the closeLong method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _maturityTime: int,
        _bondAmount: int,
        _minOutput: int,
        _options: tuple,
    ) -> "HyperdriveTarget1CloseLongContractFunction":
        super().__call__(_maturityTime, _bondAmount, _minOutput, _options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget1CloseShortContractFunction(ContractFunction):
    """ContractFunction for the closeShort method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _maturityTime: int,
        _bondAmount: int,
        _minOutput: int,
        _options: tuple,
    ) -> "HyperdriveTarget1CloseShortContractFunction":
        super().__call__(_maturityTime, _bondAmount, _minOutput, _options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget1InitializeContractFunction(ContractFunction):
    """ContractFunction for the initialize method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _contribution: int, _apr: int, _options: tuple) -> "HyperdriveTarget1InitializeContractFunction":
        super().__call__(_contribution, _apr, _options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget1RedeemWithdrawalSharesContractFunction(ContractFunction):
    """ContractFunction for the redeemWithdrawalShares method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _withdrawalShares: int, _minOutputPerShare: int, _options: tuple
    ) -> "HyperdriveTarget1RedeemWithdrawalSharesContractFunction":
        super().__call__(_withdrawalShares, _minOutputPerShare, _options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget1RemoveLiquidityContractFunction(ContractFunction):
    """ContractFunction for the removeLiquidity method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _lpShares: int, _minOutput: int, _options: tuple
    ) -> "HyperdriveTarget1RemoveLiquidityContractFunction":
        super().__call__(_lpShares, _minOutput, _options)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class HyperdriveTarget1ContractFunctions(ContractFunctions):
    """ContractFunctions for the HyperdriveTarget1 contract."""

    addLiquidity: HyperdriveTarget1AddLiquidityContractFunction

    checkpoint: HyperdriveTarget1CheckpointContractFunction

    closeLong: HyperdriveTarget1CloseLongContractFunction

    closeShort: HyperdriveTarget1CloseShortContractFunction

    initialize: HyperdriveTarget1InitializeContractFunction

    redeemWithdrawalShares: HyperdriveTarget1RedeemWithdrawalSharesContractFunction

    removeLiquidity: HyperdriveTarget1RemoveLiquidityContractFunction


hyperdrivetarget1_abi: ABI = cast(
    ABI,
    [
        {"inputs": [], "name": "BelowMinimumContribution", "type": "error"},
        {
            "inputs": [],
            "name": "FixedPointMath_InvalidExponent",
            "type": "error",
        },
        {"inputs": [], "name": "FixedPointMath_InvalidInput", "type": "error"},
        {"inputs": [], "name": "InvalidApr", "type": "error"},
        {"inputs": [], "name": "InvalidCheckpointDuration", "type": "error"},
        {"inputs": [], "name": "InvalidCheckpointTime", "type": "error"},
        {"inputs": [], "name": "InvalidFeeAmounts", "type": "error"},
        {"inputs": [], "name": "InvalidMinimumShareReserves", "type": "error"},
        {"inputs": [], "name": "InvalidPositionDuration", "type": "error"},
        {"inputs": [], "name": "InvalidShareReserves", "type": "error"},
        {"inputs": [], "name": "InvalidTimestamp", "type": "error"},
        {"inputs": [], "name": "InvalidTradeSize", "type": "error"},
        {"inputs": [], "name": "MinimumTransactionAmount", "type": "error"},
        {"inputs": [], "name": "NegativeInterest", "type": "error"},
        {"inputs": [], "name": "NegativePresentValue", "type": "error"},
        {"inputs": [], "name": "OutputLimit", "type": "error"},
        {"inputs": [], "name": "Paused", "type": "error"},
        {"inputs": [], "name": "PoolAlreadyInitialized", "type": "error"},
        {"inputs": [], "name": "UnsafeCastToInt128", "type": "error"},
        {"inputs": [], "name": "UnsafeCastToUint128", "type": "error"},
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
                {
                    "internalType": "uint256",
                    "name": "_withdrawalShares",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minOutputPerShare",
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
                {"internalType": "uint256", "name": "", "type": "uint256"},
                {"internalType": "uint256", "name": "", "type": "uint256"},
            ],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_lpShares",
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
                {"internalType": "uint256", "name": "", "type": "uint256"},
                {"internalType": "uint256", "name": "", "type": "uint256"},
            ],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ],
)


class HyperdriveTarget1Contract(Contract):
    """A web3.py Contract class for the HyperdriveTarget1 contract."""

    abi: ABI = hyperdrivetarget1_abi

    def __init__(self, address: ChecksumAddress | None = None) -> None:
        try:
            # Initialize parent Contract class
            super().__init__(address=address)

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    # TODO: add events
    # events: ERC20ContractEvents

    functions: HyperdriveTarget1ContractFunctions

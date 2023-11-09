"""A web3.py Contract class for the ERC4626DataProvider contract."""

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

    def __call__(
        self,
    ) -> "ERC4626DataProviderGetUncollectedGovernanceFeesContractFunction":
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


erc4626dataprovider_abi: ABI = cast(
    ABI,
    [
        {
            "inputs": [
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
                    "name": "_config",
                    "type": "tuple",
                },
                {
                    "internalType": "bytes32",
                    "name": "_linkerCodeHash_",
                    "type": "bytes32",
                },
                {
                    "internalType": "address",
                    "name": "_factory_",
                    "type": "address",
                },
                {
                    "internalType": "contract IERC4626",
                    "name": "_pool_",
                    "type": "address",
                },
            ],
            "stateMutability": "nonpayable",
            "type": "constructor",
        },
        {
            "inputs": [],
            "name": "FixedPointMath_InvalidExponent",
            "type": "error",
        },
        {"inputs": [], "name": "FixedPointMath_InvalidInput", "type": "error"},
        {"inputs": [], "name": "InvalidCheckpointDuration", "type": "error"},
        {"inputs": [], "name": "InvalidFeeAmounts", "type": "error"},
        {"inputs": [], "name": "InvalidMinimumShareReserves", "type": "error"},
        {"inputs": [], "name": "InvalidPositionDuration", "type": "error"},
        {"inputs": [], "name": "InvalidTradeSize", "type": "error"},
        {"inputs": [], "name": "NegativePresentValue", "type": "error"},
        {"inputs": [], "name": "QueryOutOfRange", "type": "error"},
        {
            "inputs": [{"internalType": "bytes", "name": "data", "type": "bytes"}],
            "name": "ReturnData",
            "type": "error",
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
                    "internalType": "address",
                    "name": "_target",
                    "type": "address",
                }
            ],
            "name": "isSweepable",
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
            "inputs": [],
            "name": "pool",
            "outputs": [
                {
                    "internalType": "contract IERC4626",
                    "name": "",
                    "type": "address",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "period", "type": "uint256"}],
            "name": "query",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
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
    ],
)


class ERC4626DataProviderContract(Contract):
    """A web3.py Contract class for the ERC4626DataProvider contract."""

    abi: ABI = erc4626dataprovider_abi

    def __init__(self, address: ChecksumAddress | None = None) -> None:
        try:
            # Initialize parent Contract class
            super().__init__(address=address)

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    # TODO: add events
    # events: ERC20ContractEvents

    functions: ERC4626DataProviderContractFunctions

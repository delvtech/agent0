"""A web3.py Contract class for the ERC4626HyperdriveFactory contract."""

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


class ERC4626HyperdriveFactoryDeployAndInitializeContractFunction(ContractFunction):
    """ContractFunction for the deployAndInitialize method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _config: tuple,
        arg2: list[bytes],
        _contribution: int,
        _apr: int,
        _initializeExtraData: bytes,
    ) -> "ERC4626HyperdriveFactoryDeployAndInitializeContractFunction":
        super().__call__(_config, _contribution, _apr, _initializeExtraData)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryFeeCollectorContractFunction(ContractFunction):
    """ContractFunction for the feeCollector method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryFeeCollectorContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryFeesContractFunction(ContractFunction):
    """ContractFunction for the fees method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC4626HyperdriveFactoryFeesContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryGetDefaultPausersContractFunction(ContractFunction):
    """ContractFunction for the getDefaultPausers method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryGetDefaultPausersContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryGetSweepTargetsContractFunction(ContractFunction):
    """ContractFunction for the getSweepTargets method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryGetSweepTargetsContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryGovernanceContractFunction(ContractFunction):
    """ContractFunction for the governance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC4626HyperdriveFactoryGovernanceContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryHyperdriveDeployerContractFunction(ContractFunction):
    """ContractFunction for the hyperdriveDeployer method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryHyperdriveDeployerContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryHyperdriveGovernanceContractFunction(ContractFunction):
    """ContractFunction for the hyperdriveGovernance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryHyperdriveGovernanceContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryIsOfficialContractFunction(ContractFunction):
    """ContractFunction for the isOfficial method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, instance: str) -> "ERC4626HyperdriveFactoryIsOfficialContractFunction":
        super().__call__(instance)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryLinkerCodeHashContractFunction(ContractFunction):
    """ContractFunction for the linkerCodeHash method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryLinkerCodeHashContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryLinkerFactoryContractFunction(ContractFunction):
    """ContractFunction for the linkerFactory method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryLinkerFactoryContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryUpdateDefaultPausersContractFunction(ContractFunction):
    """ContractFunction for the updateDefaultPausers method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _defaultPausers_: list[str]) -> "ERC4626HyperdriveFactoryUpdateDefaultPausersContractFunction":
        super().__call__(_defaultPausers_)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryUpdateFeeCollectorContractFunction(ContractFunction):
    """ContractFunction for the updateFeeCollector method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _feeCollector: str) -> "ERC4626HyperdriveFactoryUpdateFeeCollectorContractFunction":
        super().__call__(_feeCollector)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryUpdateFeesContractFunction(ContractFunction):
    """ContractFunction for the updateFees method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _fees: tuple) -> "ERC4626HyperdriveFactoryUpdateFeesContractFunction":
        super().__call__(_fees)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryUpdateGovernanceContractFunction(ContractFunction):
    """ContractFunction for the updateGovernance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _governance: str) -> "ERC4626HyperdriveFactoryUpdateGovernanceContractFunction":
        super().__call__(_governance)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryUpdateHyperdriveGovernanceContractFunction(ContractFunction):
    """ContractFunction for the updateHyperdriveGovernance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _hyperdriveGovernance: str
    ) -> "ERC4626HyperdriveFactoryUpdateHyperdriveGovernanceContractFunction":
        super().__call__(_hyperdriveGovernance)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryUpdateImplementationContractFunction(ContractFunction):
    """ContractFunction for the updateImplementation method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, newDeployer: str) -> "ERC4626HyperdriveFactoryUpdateImplementationContractFunction":
        super().__call__(newDeployer)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryUpdateLinkerCodeHashContractFunction(ContractFunction):
    """ContractFunction for the updateLinkerCodeHash method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _linkerCodeHash: bytes) -> "ERC4626HyperdriveFactoryUpdateLinkerCodeHashContractFunction":
        super().__call__(_linkerCodeHash)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryUpdateLinkerFactoryContractFunction(ContractFunction):
    """ContractFunction for the updateLinkerFactory method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _linkerFactory: str) -> "ERC4626HyperdriveFactoryUpdateLinkerFactoryContractFunction":
        super().__call__(_linkerFactory)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryUpdateSweepTargetsContractFunction(ContractFunction):
    """ContractFunction for the updateSweepTargets method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _sweepTargets_: list[str]) -> "ERC4626HyperdriveFactoryUpdateSweepTargetsContractFunction":
        super().__call__(_sweepTargets_)
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryVersionCounterContractFunction(ContractFunction):
    """ContractFunction for the versionCounter method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryVersionCounterContractFunction":
        super().__call__()
        return self

    # TODO: add call def so we can get return types for the calls
    # def call()


class ERC4626HyperdriveFactoryContractFunctions(ContractFunctions):
    """ContractFunctions for the ERC4626HyperdriveFactory contract."""

    deployAndInitialize: ERC4626HyperdriveFactoryDeployAndInitializeContractFunction

    feeCollector: ERC4626HyperdriveFactoryFeeCollectorContractFunction

    fees: ERC4626HyperdriveFactoryFeesContractFunction

    getDefaultPausers: ERC4626HyperdriveFactoryGetDefaultPausersContractFunction

    getSweepTargets: ERC4626HyperdriveFactoryGetSweepTargetsContractFunction

    governance: ERC4626HyperdriveFactoryGovernanceContractFunction

    hyperdriveDeployer: ERC4626HyperdriveFactoryHyperdriveDeployerContractFunction

    hyperdriveGovernance: ERC4626HyperdriveFactoryHyperdriveGovernanceContractFunction

    isOfficial: ERC4626HyperdriveFactoryIsOfficialContractFunction

    linkerCodeHash: ERC4626HyperdriveFactoryLinkerCodeHashContractFunction

    linkerFactory: ERC4626HyperdriveFactoryLinkerFactoryContractFunction

    updateDefaultPausers: ERC4626HyperdriveFactoryUpdateDefaultPausersContractFunction

    updateFeeCollector: ERC4626HyperdriveFactoryUpdateFeeCollectorContractFunction

    updateFees: ERC4626HyperdriveFactoryUpdateFeesContractFunction

    updateGovernance: ERC4626HyperdriveFactoryUpdateGovernanceContractFunction

    updateHyperdriveGovernance: ERC4626HyperdriveFactoryUpdateHyperdriveGovernanceContractFunction

    updateImplementation: ERC4626HyperdriveFactoryUpdateImplementationContractFunction

    updateLinkerCodeHash: ERC4626HyperdriveFactoryUpdateLinkerCodeHashContractFunction

    updateLinkerFactory: ERC4626HyperdriveFactoryUpdateLinkerFactoryContractFunction

    updateSweepTargets: ERC4626HyperdriveFactoryUpdateSweepTargetsContractFunction

    versionCounter: ERC4626HyperdriveFactoryVersionCounterContractFunction


erc4626hyperdrivefactory_abi: ABI = cast(
    ABI,
    [
        {
            "inputs": [
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "governance",
                            "type": "address",
                        },
                        {
                            "internalType": "address",
                            "name": "hyperdriveGovernance",
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
                            "name": "maxFees",
                            "type": "tuple",
                        },
                        {
                            "internalType": "address[]",
                            "name": "defaultPausers",
                            "type": "address[]",
                        },
                    ],
                    "internalType": "struct HyperdriveFactory.FactoryConfig",
                    "name": "_factoryConfig",
                    "type": "tuple",
                },
                {
                    "internalType": "contract IHyperdriveDeployer",
                    "name": "_deployer",
                    "type": "address",
                },
                {
                    "internalType": "address",
                    "name": "_linkerFactory",
                    "type": "address",
                },
                {
                    "internalType": "bytes32",
                    "name": "_linkerCodeHash",
                    "type": "bytes32",
                },
                {
                    "internalType": "contract IERC4626",
                    "name": "_pool",
                    "type": "address",
                },
                {
                    "internalType": "address[]",
                    "name": "_sweepTargets_",
                    "type": "address[]",
                },
            ],
            "stateMutability": "nonpayable",
            "type": "constructor",
        },
        {"inputs": [], "name": "ApprovalFailed", "type": "error"},
        {"inputs": [], "name": "FeeTooHigh", "type": "error"},
        {"inputs": [], "name": "MaxFeeTooHigh", "type": "error"},
        {"inputs": [], "name": "NonPayableInitialization", "type": "error"},
        {"inputs": [], "name": "Unauthorized", "type": "error"},
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "uint256",
                    "name": "version",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "address",
                    "name": "hyperdrive",
                    "type": "address",
                },
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
                    "indexed": False,
                    "internalType": "struct IHyperdrive.PoolConfig",
                    "name": "config",
                    "type": "tuple",
                },
                {
                    "indexed": False,
                    "internalType": "address",
                    "name": "linkerFactory",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "bytes32",
                    "name": "linkerCodeHash",
                    "type": "bytes32",
                },
                {
                    "indexed": False,
                    "internalType": "bytes32[]",
                    "name": "extraData",
                    "type": "bytes32[]",
                },
            ],
            "name": "Deployed",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "newFeeCollector",
                    "type": "address",
                }
            ],
            "name": "FeeCollectorUpdated",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "governance",
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
                    "name": "hyperdriveGovernance",
                    "type": "address",
                }
            ],
            "name": "HyperdriveGovernanceUpdated",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "newDeployer",
                    "type": "address",
                }
            ],
            "name": "ImplementationUpdated",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "bytes32",
                    "name": "newCodeHash",
                    "type": "bytes32",
                }
            ],
            "name": "LinkerCodeHashUpdated",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "newLinkerFactory",
                    "type": "address",
                }
            ],
            "name": "LinkerFactoryUpdated",
            "type": "event",
        },
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
                {"internalType": "bytes32[]", "name": "", "type": "bytes32[]"},
                {
                    "internalType": "uint256",
                    "name": "_contribution",
                    "type": "uint256",
                },
                {"internalType": "uint256", "name": "_apr", "type": "uint256"},
                {
                    "internalType": "bytes",
                    "name": "_initializeExtraData",
                    "type": "bytes",
                },
            ],
            "name": "deployAndInitialize",
            "outputs": [
                {
                    "internalType": "contract IHyperdrive",
                    "name": "",
                    "type": "address",
                }
            ],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "feeCollector",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "fees",
            "outputs": [
                {"internalType": "uint256", "name": "curve", "type": "uint256"},
                {"internalType": "uint256", "name": "flat", "type": "uint256"},
                {
                    "internalType": "uint256",
                    "name": "governance",
                    "type": "uint256",
                },
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getDefaultPausers",
            "outputs": [{"internalType": "address[]", "name": "", "type": "address[]"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getSweepTargets",
            "outputs": [{"internalType": "address[]", "name": "", "type": "address[]"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "governance",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "hyperdriveDeployer",
            "outputs": [
                {
                    "internalType": "contract IHyperdriveDeployer",
                    "name": "",
                    "type": "address",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "hyperdriveGovernance",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "address",
                    "name": "instance",
                    "type": "address",
                }
            ],
            "name": "isOfficial",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "version",
                    "type": "uint256",
                }
            ],
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
            "inputs": [],
            "name": "linkerFactory",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "address[]",
                    "name": "_defaultPausers_",
                    "type": "address[]",
                }
            ],
            "name": "updateDefaultPausers",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "address",
                    "name": "_feeCollector",
                    "type": "address",
                }
            ],
            "name": "updateFeeCollector",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
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
                    "name": "_fees",
                    "type": "tuple",
                }
            ],
            "name": "updateFees",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "address",
                    "name": "_governance",
                    "type": "address",
                }
            ],
            "name": "updateGovernance",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "address",
                    "name": "_hyperdriveGovernance",
                    "type": "address",
                }
            ],
            "name": "updateHyperdriveGovernance",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "contract IHyperdriveDeployer",
                    "name": "newDeployer",
                    "type": "address",
                }
            ],
            "name": "updateImplementation",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "bytes32",
                    "name": "_linkerCodeHash",
                    "type": "bytes32",
                }
            ],
            "name": "updateLinkerCodeHash",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "address",
                    "name": "_linkerFactory",
                    "type": "address",
                }
            ],
            "name": "updateLinkerFactory",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "address[]",
                    "name": "_sweepTargets_",
                    "type": "address[]",
                }
            ],
            "name": "updateSweepTargets",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "versionCounter",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
    ],
)


class ERC4626HyperdriveFactoryContract(Contract):
    """A web3.py Contract class for the ERC4626HyperdriveFactory contract."""

    abi: ABI = erc4626hyperdrivefactory_abi

    def __init__(self, address: ChecksumAddress | None = None) -> None:
        try:
            # Initialize parent Contract class
            super().__init__(address=address)

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    # TODO: add events
    # events: ERC20ContractEvents

    functions: ERC4626HyperdriveFactoryContractFunctions

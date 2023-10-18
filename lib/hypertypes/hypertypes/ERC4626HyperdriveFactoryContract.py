"""A web3.py Contract class for the ERC4626HyperdriveFactory contract."""
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


class ERC4626HyperdriveFactoryDeployAndInitializeContractFunction(ContractFunction):
    """ContractFunction for the deployAndInitialize method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _config: tuple, arg2: list[bytes], _contribution: int, _apr: int
    ) -> "ERC4626HyperdriveFactoryDeployAndInitializeContractFunction":
        super().__call__(_config, _contribution, _apr)
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


class ERC4626HyperdriveFactoryContract(Contract):
    """A web3.py Contract class for the ERC4626HyperdriveFactory contract."""

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

    functions: ERC4626HyperdriveFactoryContractFunctions

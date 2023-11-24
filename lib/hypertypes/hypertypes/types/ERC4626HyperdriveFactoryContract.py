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

from dataclasses import fields, is_dataclass
from typing import Any, Tuple, Type, TypeVar, cast

from eth_typing import ChecksumAddress, HexStr
from hexbytes import HexBytes
from typing_extensions import Self
from web3 import Web3
from web3.contract.contract import Contract, ContractFunction, ContractFunctions
from web3.exceptions import FallbackNotFound
from web3.types import ABI, BlockIdentifier, CallOverride, TxParams

from .ERC4626HyperdriveFactoryTypes import FactoryConfig, Fees, PoolConfig

T = TypeVar("T")

structs = {
    "Fees": Fees,
    "FactoryConfig": FactoryConfig,
    "PoolConfig": PoolConfig,
}


def tuple_to_dataclass(cls: type[T], tuple_data: Any | Tuple[Any, ...]) -> T:
    """Converts a tuple (including nested tuples) to a dataclass instance.  If cls is not a dataclass,
    then the data will just be passed through this function.

    Arguments
    ---------
    cls: type[T]
        The dataclass type to which the tuple data is to be converted.
    tuple_data: Any | Tuple[Any, ...]
        A tuple (or nested tuple) of values to convert into a dataclass instance.

    Returns
    -------
    T
        Either an instance of cls populated with data from tuple_data or tuple_data itself.
    """
    if not is_dataclass(cls):
        return cast(T, tuple_data)

    field_types = {field.name: field.type for field in fields(cls)}
    field_values = {}

    for (field_name, field_type), value in zip(field_types.items(), tuple_data):
        field_type = structs.get(field_type, field_type)
        if is_dataclass(field_type):
            # Recursively convert nested tuples to nested dataclasses
            field_values[field_name] = tuple_to_dataclass(field_type, value)
        elif isinstance(value, tuple) and not getattr(field_type, "_name", None) == "Tuple":
            # If it's a tuple and the field is not intended to be a tuple, assume it's a nested dataclass
            field_values[field_name] = tuple_to_dataclass(field_type, value)
        else:
            # Otherwise, set the primitive value directly
            field_values[field_name] = value

    return cls(**field_values)


class ERC4626HyperdriveFactoryDeployAndInitializeContractFunction(ContractFunction):
    """ContractFunction for the deployAndInitialize method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _config: PoolConfig,
        _contribution: int,
        _apr: int,
        _initializeExtraData: bytes,
        arg5: list[bytes],
        _pool: str,
    ) -> "ERC4626HyperdriveFactoryDeployAndInitializeContractFunction":
        clone = super().__call__(_config, _contribution, _apr, _initializeExtraData, arg5, _pool)
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """Returns str"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = str

        return cast(str, self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryFeeCollectorContractFunction(ContractFunction):
    """ContractFunction for the feeCollector method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryFeeCollectorContractFunction":
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """Returns str"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = str

        return cast(str, self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryFeesContractFunction(ContractFunction):
    """ContractFunction for the fees method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC4626HyperdriveFactoryFeesContractFunction":
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> tuple[int, int, int]:
        """Returns (int, int, int)"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = [int, int, int]

        return cast(tuple[int, int, int], self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryGetDefaultPausersContractFunction(ContractFunction):
    """ContractFunction for the getDefaultPausers method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryGetDefaultPausersContractFunction":
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> list[str]:
        """Returns list[str]"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = list[str]

        return cast(list[str], self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryGetInstanceAtIndexContractFunction(ContractFunction):
    """ContractFunction for the getInstanceAtIndex method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, index: int) -> "ERC4626HyperdriveFactoryGetInstanceAtIndexContractFunction":
        clone = super().__call__(index)
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """Returns str"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = str

        return cast(str, self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryGetInstancesInRangeContractFunction(ContractFunction):
    """ContractFunction for the getInstancesInRange method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, startIndex: int, endIndex: int) -> "ERC4626HyperdriveFactoryGetInstancesInRangeContractFunction":
        clone = super().__call__(startIndex, endIndex)
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> list[str]:
        """Returns list[str]"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = list[str]

        return cast(list[str], self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryGetNumberOfInstancesContractFunction(ContractFunction):
    """ContractFunction for the getNumberOfInstances method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryGetNumberOfInstancesContractFunction":
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> int:
        """Returns int"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = int

        return cast(int, self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryGetSweepTargetsContractFunction(ContractFunction):
    """ContractFunction for the getSweepTargets method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryGetSweepTargetsContractFunction":
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> list[str]:
        """Returns list[str]"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = list[str]

        return cast(list[str], self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryGovernanceContractFunction(ContractFunction):
    """ContractFunction for the governance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "ERC4626HyperdriveFactoryGovernanceContractFunction":
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """Returns str"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = str

        return cast(str, self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryHyperdriveDeployerContractFunction(ContractFunction):
    """ContractFunction for the hyperdriveDeployer method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryHyperdriveDeployerContractFunction":
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """Returns str"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = str

        return cast(str, self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryHyperdriveGovernanceContractFunction(ContractFunction):
    """ContractFunction for the hyperdriveGovernance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryHyperdriveGovernanceContractFunction":
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """Returns str"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = str

        return cast(str, self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryIsInstanceContractFunction(ContractFunction):
    """ContractFunction for the isInstance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, arg1: str) -> "ERC4626HyperdriveFactoryIsInstanceContractFunction":
        clone = super().__call__(arg1)
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> bool:
        """Returns bool"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = bool

        return cast(bool, self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryIsOfficialContractFunction(ContractFunction):
    """ContractFunction for the isOfficial method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, instance: str) -> "ERC4626HyperdriveFactoryIsOfficialContractFunction":
        clone = super().__call__(instance)
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> int:
        """Returns int"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = int

        return cast(int, self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryLinkerCodeHashContractFunction(ContractFunction):
    """ContractFunction for the linkerCodeHash method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryLinkerCodeHashContractFunction":
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> bytes:
        """Returns bytes"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = bytes

        return cast(bytes, self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryLinkerFactoryContractFunction(ContractFunction):
    """ContractFunction for the linkerFactory method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryLinkerFactoryContractFunction":
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """Returns str"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = str

        return cast(str, self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryTarget0DeployerContractFunction(ContractFunction):
    """ContractFunction for the target0Deployer method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryTarget0DeployerContractFunction":
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """Returns str"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = str

        return cast(str, self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryTarget1DeployerContractFunction(ContractFunction):
    """ContractFunction for the target1Deployer method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryTarget1DeployerContractFunction":
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """Returns str"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = str

        return cast(str, self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryUpdateDefaultPausersContractFunction(ContractFunction):
    """ContractFunction for the updateDefaultPausers method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _defaultPausers_: list[str]) -> "ERC4626HyperdriveFactoryUpdateDefaultPausersContractFunction":
        clone = super().__call__(_defaultPausers_)
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> None:
        """No return value"""
        super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryUpdateFeeCollectorContractFunction(ContractFunction):
    """ContractFunction for the updateFeeCollector method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _feeCollector: str) -> "ERC4626HyperdriveFactoryUpdateFeeCollectorContractFunction":
        clone = super().__call__(_feeCollector)
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> None:
        """No return value"""
        super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryUpdateFeesContractFunction(ContractFunction):
    """ContractFunction for the updateFees method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _fees: Fees) -> "ERC4626HyperdriveFactoryUpdateFeesContractFunction":
        clone = super().__call__(_fees)
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> None:
        """No return value"""
        super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryUpdateGovernanceContractFunction(ContractFunction):
    """ContractFunction for the updateGovernance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _governance: str) -> "ERC4626HyperdriveFactoryUpdateGovernanceContractFunction":
        clone = super().__call__(_governance)
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> None:
        """No return value"""
        super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryUpdateHyperdriveGovernanceContractFunction(ContractFunction):
    """ContractFunction for the updateHyperdriveGovernance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _hyperdriveGovernance: str
    ) -> "ERC4626HyperdriveFactoryUpdateHyperdriveGovernanceContractFunction":
        clone = super().__call__(_hyperdriveGovernance)
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> None:
        """No return value"""
        super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryUpdateImplementationContractFunction(ContractFunction):
    """ContractFunction for the updateImplementation method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, newDeployer: str) -> "ERC4626HyperdriveFactoryUpdateImplementationContractFunction":
        clone = super().__call__(newDeployer)
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> None:
        """No return value"""
        super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryUpdateLinkerCodeHashContractFunction(ContractFunction):
    """ContractFunction for the updateLinkerCodeHash method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _linkerCodeHash: bytes) -> "ERC4626HyperdriveFactoryUpdateLinkerCodeHashContractFunction":
        clone = super().__call__(_linkerCodeHash)
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> None:
        """No return value"""
        super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryUpdateLinkerFactoryContractFunction(ContractFunction):
    """ContractFunction for the updateLinkerFactory method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _linkerFactory: str) -> "ERC4626HyperdriveFactoryUpdateLinkerFactoryContractFunction":
        clone = super().__call__(_linkerFactory)
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> None:
        """No return value"""
        super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryUpdateSweepTargetsContractFunction(ContractFunction):
    """ContractFunction for the updateSweepTargets method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, __sweepTargets: list[str]) -> "ERC4626HyperdriveFactoryUpdateSweepTargetsContractFunction":
        clone = super().__call__(__sweepTargets)
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> None:
        """No return value"""
        super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryVersionCounterContractFunction(ContractFunction):
    """ContractFunction for the versionCounter method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "ERC4626HyperdriveFactoryVersionCounterContractFunction":
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> int:
        """Returns int"""
        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        # Define the expected return types from the smart contract call
        return_types = int

        return cast(int, self._call(return_types, raw_values))

    def _call(self, return_types, raw_values):
        # cover case of multiple return values
        if isinstance(return_types, list):
            # Ensure raw_values is a tuple for consistency
            if not isinstance(raw_values, list):
                raw_values = (raw_values,)

            # Convert the tuple to the dataclass instance using the utility function
            converted_values = tuple(
                (tuple_to_dataclass(return_type, value) for return_type, value in zip(return_types, raw_values))
            )

            return converted_values

        # cover case of single return value
        converted_value = tuple_to_dataclass(return_types, raw_values)
        return converted_value


class ERC4626HyperdriveFactoryContractFunctions(ContractFunctions):
    """ContractFunctions for the ERC4626HyperdriveFactory contract."""

    deployAndInitialize: ERC4626HyperdriveFactoryDeployAndInitializeContractFunction

    feeCollector: ERC4626HyperdriveFactoryFeeCollectorContractFunction

    fees: ERC4626HyperdriveFactoryFeesContractFunction

    getDefaultPausers: ERC4626HyperdriveFactoryGetDefaultPausersContractFunction

    getInstanceAtIndex: ERC4626HyperdriveFactoryGetInstanceAtIndexContractFunction

    getInstancesInRange: ERC4626HyperdriveFactoryGetInstancesInRangeContractFunction

    getNumberOfInstances: ERC4626HyperdriveFactoryGetNumberOfInstancesContractFunction

    getSweepTargets: ERC4626HyperdriveFactoryGetSweepTargetsContractFunction

    governance: ERC4626HyperdriveFactoryGovernanceContractFunction

    hyperdriveDeployer: ERC4626HyperdriveFactoryHyperdriveDeployerContractFunction

    hyperdriveGovernance: ERC4626HyperdriveFactoryHyperdriveGovernanceContractFunction

    isInstance: ERC4626HyperdriveFactoryIsInstanceContractFunction

    isOfficial: ERC4626HyperdriveFactoryIsOfficialContractFunction

    linkerCodeHash: ERC4626HyperdriveFactoryLinkerCodeHashContractFunction

    linkerFactory: ERC4626HyperdriveFactoryLinkerFactoryContractFunction

    target0Deployer: ERC4626HyperdriveFactoryTarget0DeployerContractFunction

    target1Deployer: ERC4626HyperdriveFactoryTarget1DeployerContractFunction

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

    def __init__(
        self,
        abi: ABI,
        w3: "Web3",
        address: ChecksumAddress | None = None,
        decode_tuples: bool | None = False,
    ) -> None:
        super().__init__(abi, w3, address, decode_tuples)
        self.deployAndInitialize = ERC4626HyperdriveFactoryDeployAndInitializeContractFunction.factory(
            "deployAndInitialize",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="deployAndInitialize",
        )
        self.feeCollector = ERC4626HyperdriveFactoryFeeCollectorContractFunction.factory(
            "feeCollector",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="feeCollector",
        )
        self.fees = ERC4626HyperdriveFactoryFeesContractFunction.factory(
            "fees",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="fees",
        )
        self.getDefaultPausers = ERC4626HyperdriveFactoryGetDefaultPausersContractFunction.factory(
            "getDefaultPausers",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="getDefaultPausers",
        )
        self.getInstanceAtIndex = ERC4626HyperdriveFactoryGetInstanceAtIndexContractFunction.factory(
            "getInstanceAtIndex",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="getInstanceAtIndex",
        )
        self.getInstancesInRange = ERC4626HyperdriveFactoryGetInstancesInRangeContractFunction.factory(
            "getInstancesInRange",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="getInstancesInRange",
        )
        self.getNumberOfInstances = ERC4626HyperdriveFactoryGetNumberOfInstancesContractFunction.factory(
            "getNumberOfInstances",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="getNumberOfInstances",
        )
        self.getSweepTargets = ERC4626HyperdriveFactoryGetSweepTargetsContractFunction.factory(
            "getSweepTargets",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="getSweepTargets",
        )
        self.governance = ERC4626HyperdriveFactoryGovernanceContractFunction.factory(
            "governance",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="governance",
        )
        self.hyperdriveDeployer = ERC4626HyperdriveFactoryHyperdriveDeployerContractFunction.factory(
            "hyperdriveDeployer",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="hyperdriveDeployer",
        )
        self.hyperdriveGovernance = ERC4626HyperdriveFactoryHyperdriveGovernanceContractFunction.factory(
            "hyperdriveGovernance",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="hyperdriveGovernance",
        )
        self.isInstance = ERC4626HyperdriveFactoryIsInstanceContractFunction.factory(
            "isInstance",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="isInstance",
        )
        self.isOfficial = ERC4626HyperdriveFactoryIsOfficialContractFunction.factory(
            "isOfficial",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="isOfficial",
        )
        self.linkerCodeHash = ERC4626HyperdriveFactoryLinkerCodeHashContractFunction.factory(
            "linkerCodeHash",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="linkerCodeHash",
        )
        self.linkerFactory = ERC4626HyperdriveFactoryLinkerFactoryContractFunction.factory(
            "linkerFactory",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="linkerFactory",
        )
        self.target0Deployer = ERC4626HyperdriveFactoryTarget0DeployerContractFunction.factory(
            "target0Deployer",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="target0Deployer",
        )
        self.target1Deployer = ERC4626HyperdriveFactoryTarget1DeployerContractFunction.factory(
            "target1Deployer",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="target1Deployer",
        )
        self.updateDefaultPausers = ERC4626HyperdriveFactoryUpdateDefaultPausersContractFunction.factory(
            "updateDefaultPausers",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="updateDefaultPausers",
        )
        self.updateFeeCollector = ERC4626HyperdriveFactoryUpdateFeeCollectorContractFunction.factory(
            "updateFeeCollector",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="updateFeeCollector",
        )
        self.updateFees = ERC4626HyperdriveFactoryUpdateFeesContractFunction.factory(
            "updateFees",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="updateFees",
        )
        self.updateGovernance = ERC4626HyperdriveFactoryUpdateGovernanceContractFunction.factory(
            "updateGovernance",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="updateGovernance",
        )
        self.updateHyperdriveGovernance = ERC4626HyperdriveFactoryUpdateHyperdriveGovernanceContractFunction.factory(
            "updateHyperdriveGovernance",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="updateHyperdriveGovernance",
        )
        self.updateImplementation = ERC4626HyperdriveFactoryUpdateImplementationContractFunction.factory(
            "updateImplementation",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="updateImplementation",
        )
        self.updateLinkerCodeHash = ERC4626HyperdriveFactoryUpdateLinkerCodeHashContractFunction.factory(
            "updateLinkerCodeHash",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="updateLinkerCodeHash",
        )
        self.updateLinkerFactory = ERC4626HyperdriveFactoryUpdateLinkerFactoryContractFunction.factory(
            "updateLinkerFactory",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="updateLinkerFactory",
        )
        self.updateSweepTargets = ERC4626HyperdriveFactoryUpdateSweepTargetsContractFunction.factory(
            "updateSweepTargets",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="updateSweepTargets",
        )
        self.versionCounter = ERC4626HyperdriveFactoryVersionCounterContractFunction.factory(
            "versionCounter",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="versionCounter",
        )


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
                            "internalType": "address[]",
                            "name": "defaultPausers",
                            "type": "address[]",
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
                            "internalType": "contract IHyperdriveDeployer",
                            "name": "hyperdriveDeployer",
                            "type": "address",
                        },
                        {
                            "internalType": "contract IHyperdriveTargetDeployer",
                            "name": "target0Deployer",
                            "type": "address",
                        },
                        {
                            "internalType": "contract IHyperdriveTargetDeployer",
                            "name": "target1Deployer",
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
                    ],
                    "internalType": "struct HyperdriveFactory.FactoryConfig",
                    "name": "_factoryConfig",
                    "type": "tuple",
                },
                {
                    "internalType": "address[]",
                    "name": "__sweepTargets",
                    "type": "address[]",
                },
            ],
            "stateMutability": "nonpayable",
            "type": "constructor",
        },
        {"inputs": [], "name": "ApprovalFailed", "type": "error"},
        {"inputs": [], "name": "EndIndexTooLarge", "type": "error"},
        {"inputs": [], "name": "FeeTooHigh", "type": "error"},
        {"inputs": [], "name": "InvalidIndexes", "type": "error"},
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
                    "indexed": False,
                    "internalType": "struct IHyperdrive.PoolConfig",
                    "name": "config",
                    "type": "tuple",
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
                    "name": "newLinkerCodeHash",
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
                    "name": "_config",
                    "type": "tuple",
                },
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
                {"internalType": "bytes32[]", "name": "", "type": "bytes32[]"},
                {"internalType": "address", "name": "_pool", "type": "address"},
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
            "inputs": [{"internalType": "uint256", "name": "index", "type": "uint256"}],
            "name": "getInstanceAtIndex",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "startIndex",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "endIndex",
                    "type": "uint256",
                },
            ],
            "name": "getInstancesInRange",
            "outputs": [
                {
                    "internalType": "address[]",
                    "name": "range",
                    "type": "address[]",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getNumberOfInstances",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
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
            "inputs": [{"internalType": "address", "name": "", "type": "address"}],
            "name": "isInstance",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
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
            "inputs": [],
            "name": "target0Deployer",
            "outputs": [
                {
                    "internalType": "contract IHyperdriveTargetDeployer",
                    "name": "",
                    "type": "address",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "target1Deployer",
            "outputs": [
                {
                    "internalType": "contract IHyperdriveTargetDeployer",
                    "name": "",
                    "type": "address",
                }
            ],
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
                    "name": "__sweepTargets",
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
# pylint: disable=line-too-long
erc4626hyperdrivefactory_bytecode = HexStr(
    "0x60e0604052600180553480156200001557600080fd5b5060405162001f0538038062001f058339810160408190526200003891620003fc565b60a08083018051516080819052815160200151909252516040015160c0528290670de0b6b3a76400001080620000775750670de0b6b3a764000060a051115b806200008c5750670de0b6b3a764000060c051115b15620000ab5760405163a3932d2d60e01b815260040160405180910390fd5b6080805190820151511180620000ca575060a051816080015160200151115b80620000df575060c051816080015160400151115b15620000fe5760405163cd4e616760e01b815260040160405180910390fd5b60808101518051600955602080820151600a55604091820151600b558251600080546001600160a01b039283166001600160a01b03199182161790915582850151600680549184169183169190911790556060850151600c80549190931691161790559082015180516200017792600d92019062000200565b5060c0810151600380546001600160a01b039283166001600160a01b03199182161790915560e083015160048054918416918316919091179055610100830151600580549184169183169190911790556101208301516007805491909316911617905561014001516008558051620001f790601090602084019062000200565b5050506200055a565b82805482825590600052602060002090810192821562000258579160200282015b828111156200025857825182546001600160a01b0319166001600160a01b0390911617825560209092019160019091019062000221565b50620002669291506200026a565b5090565b5b808211156200026657600081556001016200026b565b634e487b7160e01b600052604160045260246000fd5b60405161016081016001600160401b0381118282101715620002bd57620002bd62000281565b60405290565b6001600160a01b0381168114620002d957600080fd5b50565b8051620002e981620002c3565b919050565b600082601f8301126200030057600080fd5b815160206001600160401b03808311156200031f576200031f62000281565b8260051b604051601f19603f8301168101818110848211171562000347576200034762000281565b6040529384528581018301938381019250878511156200036657600080fd5b83870191505b84821015620003925781516200038281620002c3565b835291830191908301906200036c565b979650505050505050565b600060608284031215620003b057600080fd5b604051606081016001600160401b0381118282101715620003d557620003d562000281565b80604052508091508251815260208301516020820152604083015160408201525092915050565b600080604083850312156200041057600080fd5b82516001600160401b03808211156200042857600080fd5b908401906101e082870312156200043e57600080fd5b6200044862000297565b6200045383620002dc565b81526200046360208401620002dc565b60208201526040830151828111156200047b57600080fd5b6200048988828601620002ee565b6040830152506200049d60608401620002dc565b6060820152620004b187608085016200039d565b6080820152620004c58760e085016200039d565b60a0820152610140620004da818501620002dc565b60c0830152620004ee6101608501620002dc565b60e0830152620005026101808501620002dc565b610100830152620005176101a08501620002dc565b6101208301526101c084015181830152508094505060208501519150808211156200054157600080fd5b506200055085828601620002ee565b9150509250929050565b60805160a05160c05161197b6200058a600039600061076a0152600061073c01526000610712015261197b6000f3fe60806040526004361061019c5760003560e01c806399623bb1116100ec578063c415b95c1161008a578063daac24da11610064578063daac24da146104c6578063dd2b8fbb146104e6578063dd6d30c114610506578063e33315551461051c57600080fd5b8063c415b95c14610470578063c905a4b514610490578063d2c35ce8146104a657600080fd5b8063a085fa30116100c6578063a085fa30146103f0578063ab71905f14610410578063b256126314610430578063bc30e7a11461045057600080fd5b806399623bb1146103765780639af1d35a146103965780639af25262146103d057600080fd5b80636b44e6be1161015957806377b81aac1161013357806377b81aac146102f25780637f7c5a7d1461031f578063852297851461034157806394ad46d91461036157600080fd5b80636b44e6be146102735780636e95d67c146102b35780637613b08c146102d257600080fd5b8063025b22bc146101a157806303a5aa92146101c357806309b9075f146102005780630a4bc38d146102205780634fbfee77146102335780635aa6e67514610253575b600080fd5b3480156101ad57600080fd5b506101c16101bc3660046111c3565b61053c565b005b3480156101cf57600080fd5b506003546101e3906001600160a01b031681565b6040516001600160a01b0390911681526020015b60405180910390f35b34801561020c57600080fd5b506101c161021b3660046111e7565b6105cb565b6101e361022e366004611429565b610606565b34801561023f57600080fd5b506101c161024e36600461157d565b610689565b34801561025f57600080fd5b506000546101e3906001600160a01b031681565b34801561027f57600080fd5b506102a361028e3660046111c3565b600f6020526000908152604090205460ff1681565b60405190151581526020016101f7565b3480156102bf57600080fd5b50600e545b6040519081526020016101f7565b3480156102de57600080fd5b506101c16102ed366004611596565b6106e6565b3480156102fe57600080fd5b506102c461030d3660046111c3565b60026020526000908152604090205481565b34801561032b57600080fd5b506103346107c4565b6040516101f791906115ae565b34801561034d57600080fd5b506101c161035c3660046111c3565b610826565b34801561036d57600080fd5b506103346108ad565b34801561038257600080fd5b506007546101e3906001600160a01b031681565b3480156103a257600080fd5b50600954600a54600b546103b592919083565b604080519384526020840192909252908201526060016101f7565b3480156103dc57600080fd5b506101c16103eb3660046111e7565b61090d565b3480156103fc57600080fd5b506005546101e3906001600160a01b031681565b34801561041c57600080fd5b506004546101e3906001600160a01b031681565b34801561043c57600080fd5b506101c161044b3660046111c3565b610943565b34801561045c57600080fd5b5061033461046b3660046115fb565b6109b5565b34801561047c57600080fd5b50600c546101e3906001600160a01b031681565b34801561049c57600080fd5b506102c460085481565b3480156104b257600080fd5b506101c16104c13660046111c3565b610ad1565b3480156104d257600080fd5b506101e36104e136600461157d565b610b45565b3480156104f257600080fd5b506101c16105013660046111c3565b610b75565b34801561051257600080fd5b506102c460015481565b34801561052857600080fd5b506006546101e3906001600160a01b031681565b6000546001600160a01b03163314610566576040516282b42960e81b815260040160405180910390fd5b6001600160a01b03811661057957600080fd5b600380546001600160a01b0319166001600160a01b03831690811790915560018054810190556040517f310ba5f1d2ed074b51e2eccd052a47ae9ab7c6b800d1fca3db3999d6a592ca0390600090a250565b6000546001600160a01b031633146105f5576040516282b42960e81b815260040160405180910390fd5b61060160108383611133565b505050565b600080601080548060200260200160405190810160405280929190818152602001828054801561065f57602002820191906000526020600020905b81546001600160a01b03168152600190910190602001808311610641575b505050505090506060819050600061067b8a8a8a8a868a610be9565b9a9950505050505050505050565b6000546001600160a01b031633146106b3576040516282b42960e81b815260040160405180910390fd5b600881905560405181907f395a61259037298d1c4cd4bf177b64ad5995d38a9394573fcd9060d649314ad090600090a250565b6000546001600160a01b03163314610710576040516282b42960e81b815260040160405180910390fd5b7f00000000000000000000000000000000000000000000000000000000000000008135118061076257507f00000000000000000000000000000000000000000000000000000000000000008160200135115b8061079057507f00000000000000000000000000000000000000000000000000000000000000008160400135115b156107ae5760405163cd4e616760e01b815260040160405180910390fd5b80356009556020810135600a5560400135600b55565b6060600d80548060200260200160405190810160405280929190818152602001828054801561081c57602002820191906000526020600020905b81546001600160a01b031681526001909101906020018083116107fe575b5050505050905090565b6000546001600160a01b03163314610850576040516282b42960e81b815260040160405180910390fd5b6001600160a01b03811661086357600080fd5b600780546001600160a01b0319166001600160a01b0383169081179091556040517f03aa5b0fb65014eea89fda04a7bc11742014881f3c078f2c75b7226ce10d941890600090a250565b6060601080548060200260200160405190810160405280929190818152602001828054801561081c576020028201919060005260206000209081546001600160a01b031681526001909101906020018083116107fe575050505050905090565b6000546001600160a01b03163314610937576040516282b42960e81b815260040160405180910390fd5b610601600d8383611133565b6000546001600160a01b0316331461096d576040516282b42960e81b815260040160405180910390fd5b600080546001600160a01b0319166001600160a01b038316908117825560405190917f9d3e522e1e47a2f6009739342b9cc7b252a1888154e843ab55ee1c81745795ab91a250565b6060818311156109d857604051633b2735ab60e11b815260040160405180910390fd5b600e548211156109fb5760405163e0f7becb60e01b815260040160405180910390fd5b610a058383611633565b610a1090600161164c565b67ffffffffffffffff811115610a2857610a2861125c565b604051908082528060200260200182016040528015610a51578160200160208202803683370190505b509050825b828111610aca57600e8181548110610a7057610a7061165f565b6000918252602090912001546001600160a01b031682610a908684611633565b81518110610aa057610aa061165f565b6001600160a01b039092166020928302919091019091015280610ac281611675565b915050610a56565b5092915050565b6000546001600160a01b03163314610afb576040516282b42960e81b815260040160405180910390fd5b600c80546001600160a01b0319166001600160a01b0383169081179091556040517fe5693914d19c789bdee50a362998c0bc8d035a835f9871da5d51152f0582c34f90600090a250565b6000600e8281548110610b5a57610b5a61165f565b6000918252602090912001546001600160a01b031692915050565b6000546001600160a01b03163314610b9f576040516282b42960e81b815260040160405180910390fd5b600680546001600160a01b0319166001600160a01b0383169081179091556040517ff3e07b4bb4394f2ff320bd1dd151551dff304d5e948b401d8558b228482c97d890600090a250565b60003415610c0a57604051638fbc3bd960e01b815260040160405180910390fd5b6007546001600160a01b039081166020808a01919091526008546040808b0191909152600c5483166101608b0152306101408b015280516060810182526009548152600a5492810192909252600b54828201526101808a01919091526003546004805492516228eec760e61b815260009492831693637a77fb8f938d93911691630a3bb1c091610ca09185918c918c910161179e565b6020604051808303816000875af1158015610cbf573d6000803e3d6000fd5b505050506040513d601f19601f82011682018060405250810190610ce391906117da565b6005546040516228eec760e61b81526001600160a01b0390911690630a3bb1c090610d16908f908c908c9060040161179e565b6020604051808303816000875af1158015610d35573d6000803e3d6000fd5b505050506040513d601f19601f82011682018060405250810190610d5991906117da565b88886040518663ffffffff1660e01b8152600401610d7b9594939291906117f7565b6020604051808303816000875af1158015610d9a573d6000803e3d6000fd5b505050506040513d601f19601f82011682018060405250810190610dbe91906117da565b6001546001600160a01b03808316600090815260026020526040908190208390556006549091166101408c015251919250907f182eef5a11a432f42fc4cfb3fc11289cdb0179382ff5f41dc9ec327c4a2d364490610e219084908c90899061184b565b60405180910390a2600e805460018082019092557fbb7b4a454dc3493923482f07822329ed19e8244eff582cc204f8554c3620c3fd0180546001600160a01b0319166001600160a01b038481169182179092556000908152600f602052604090819020805460ff1916909317909255895191516323b872dd60e01b8152336004820152306024820152604481018a90529116906323b872dd906064016020604051808303816000875af1158015610edc573d6000803e3d6000fd5b505050506040513d601f19601f82011682018060405250810190610f009190611886565b50875160405163095ea7b360e01b81526001600160a01b03838116600483015260001960248301529091169063095ea7b3906044016020604051808303816000875af1158015610f54573d6000803e3d6000fd5b505050506040513d601f19601f82011682018060405250810190610f789190611886565b610f95576040516340b27c2160e11b815260040160405180910390fd5b60408051606081018252338152600160208201528082018790529051631df417fd60e21b81526001600160a01b038316916377d05ff491610fdd918b918b91906004016118a8565b6020604051808303816000875af1158015610ffc573d6000803e3d6000fd5b505050506040513d601f19601f82011682018060405250810190611020919061192c565b5060005b600d548110156110c757816001600160a01b0316637180c8ca600d83815481106110505761105061165f565b60009182526020909120015460405160e083901b6001600160e01b03191681526001600160a01b03909116600482015260016024820152604401600060405180830381600087803b1580156110a457600080fd5b505af11580156110b8573d6000803e3d6000fd5b50505050806001019050611024565b5060065460405163ab033ea960e01b81526001600160a01b0391821660048201529082169063ab033ea990602401600060405180830381600087803b15801561110f57600080fd5b505af1158015611123573d6000803e3d6000fd5b50929a9950505050505050505050565b828054828255906000526020600020908101928215611186579160200282015b828111156111865781546001600160a01b0319166001600160a01b03843516178255602090920191600190910190611153565b50611192929150611196565b5090565b5b808211156111925760008155600101611197565b6001600160a01b03811681146111c057600080fd5b50565b6000602082840312156111d557600080fd5b81356111e0816111ab565b9392505050565b600080602083850312156111fa57600080fd5b823567ffffffffffffffff8082111561121257600080fd5b818501915085601f83011261122657600080fd5b81358181111561123557600080fd5b8660208260051b850101111561124a57600080fd5b60209290920196919550909350505050565b634e487b7160e01b600052604160045260246000fd5b6040516101a0810167ffffffffffffffff811182821017156112965761129661125c565b60405290565b604051601f8201601f1916810167ffffffffffffffff811182821017156112c5576112c561125c565b604052919050565b80356112d8816111ab565b919050565b6000606082840312156112ef57600080fd5b6040516060810181811067ffffffffffffffff821117156113125761131261125c565b80604052508091508235815260208301356020820152604083013560408201525092915050565b600082601f83011261134a57600080fd5b813567ffffffffffffffff8111156113645761136461125c565b611377601f8201601f191660200161129c565b81815284602083860101111561138c57600080fd5b816020850160208301376000918101602001919091529392505050565b600082601f8301126113ba57600080fd5b8135602067ffffffffffffffff8211156113d6576113d661125c565b8160051b6113e582820161129c565b92835284810182019282810190878511156113ff57600080fd5b83870192505b8483101561141e57823582529183019190830190611405565b979650505050505050565b60008060008060008086880361028081121561144457600080fd5b6101e08082121561145457600080fd5b61145c611272565b9150611467896112cd565b825261147560208a016112cd565b602083015260408901356040830152606089013560608301526080890135608083015260a089013560a083015260c089013560c083015260e089013560e0830152610100808a01358184015250610120808a013581840152506101406114dc818b016112cd565b908301526101606114ee8a82016112cd565b908301526101806115018b8b83016112dd565b908301529096508701359450610200870135935061022087013567ffffffffffffffff8082111561153157600080fd5b61153d8a838b01611339565b945061024089013591508082111561155457600080fd5b5061156189828a016113a9565b92505061157161026088016112cd565b90509295509295509295565b60006020828403121561158f57600080fd5b5035919050565b6000606082840312156115a857600080fd5b50919050565b6020808252825182820181905260009190848201906040850190845b818110156115ef5783516001600160a01b0316835292840192918401916001016115ca565b50909695505050505050565b6000806040838503121561160e57600080fd5b50508035926020909101359150565b634e487b7160e01b600052601160045260246000fd5b818103818111156116465761164661161d565b92915050565b808201808211156116465761164661161d565b634e487b7160e01b600052603260045260246000fd5b6000600182016116875761168761161d565b5060010190565b80516001600160a01b0316825260208101516116b560208401826001600160a01b03169052565b5060408101516040830152606081015160608301526080810151608083015260a081015160a083015260c081015160c083015260e081015160e083015261010080820151818401525061012080820151818401525061014080820151611725828501826001600160a01b03169052565b5050610160818101516001600160a01b0316908301526101809081015180519183019190915260208101516101a0830152604001516101c090910152565b600081518084526020808501945080840160005b8381101561179357815187529582019590820190600101611777565b509495945050505050565b60006102206117ad838761168e565b806101e08401526117c081840186611763565b91505060018060a01b038316610200830152949350505050565b6000602082840312156117ec57600080fd5b81516111e0816111ab565b6000610260611806838961168e565b6001600160a01b038781166101e0850152868116610200850152610220840182905261183482850187611763565b925080851661024085015250509695505050505050565b6001600160a01b03841681526000610220611869602084018661168e565b8061020084015261187c81840185611763565b9695505050505050565b60006020828403121561189857600080fd5b815180151581146111e057600080fd5b8381526000602084818401526060604084015260018060a01b03845116606084015280840151151560808401526040840151606060a085015280518060c086015260005b818110156119085782810184015186820160e0015283016118ec565b50600060e0828701015260e0601f19601f8301168601019350505050949350505050565b60006020828403121561193e57600080fd5b505191905056fea264697066735822122035905b3ee113527e119859b41def9d5e3fc2e9294a605f2b1e41046a200f9bff64736f6c63430008130033"
)


class ERC4626HyperdriveFactoryContract(Contract):
    """A web3.py Contract class for the ERC4626HyperdriveFactory contract."""

    abi: ABI = erc4626hyperdrivefactory_abi
    bytecode: bytes = HexBytes(erc4626hyperdrivefactory_bytecode)

    def __init__(self, address: ChecksumAddress | None = None) -> None:
        try:
            # Initialize parent Contract class
            super().__init__(address=address)
            self.functions = ERC4626HyperdriveFactoryContractFunctions(erc4626hyperdrivefactory_abi, self.w3, address)

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    # TODO: add events
    # events: ERC20ContractEvents

    functions: ERC4626HyperdriveFactoryContractFunctions

    @classmethod
    def factory(cls, w3: Web3, class_name: str | None = None, **kwargs: Any) -> Type[Self]:
        contract = super().factory(w3, class_name, **kwargs)
        contract.functions = ERC4626HyperdriveFactoryContractFunctions(erc4626hyperdrivefactory_abi, w3, None)

        return contract

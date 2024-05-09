"""Dataclasses for all structs in the HyperdriveFactory contract.

DO NOT EDIT.  This file was generated by pypechain.  See documentation at
https://github.com/delvtech/pypechain """

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

from dataclasses import dataclass

from web3.types import ABIEvent, ABIEventParams

from . import IHyperdriveTypes as IHyperdrive


@dataclass
class FactoryConfig:
    """FactoryConfig struct."""

    governance: str
    hyperdriveGovernance: str
    defaultPausers: list[str]
    feeCollector: str
    sweepCollector: str
    checkpointDurationResolution: int
    minCheckpointDuration: int
    maxCheckpointDuration: int
    minPositionDuration: int
    maxPositionDuration: int
    minCircuitBreakerDelta: int
    maxCircuitBreakerDelta: int
    minFixedAPR: int
    maxFixedAPR: int
    minTimeStretchAPR: int
    maxTimeStretchAPR: int
    minFees: IHyperdrive.Fees
    maxFees: IHyperdrive.Fees
    linkerFactory: str
    linkerCodeHash: bytes


CheckpointDurationResolutionUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="newCheckpointDurationResolution", type="uint256"),
    ],
    name="CheckpointDurationResolutionUpdated",
    type="event",
)

DefaultPausersUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="newDefaultPausers", type="address[]"),
    ],
    name="DefaultPausersUpdated",
    type="event",
)

Deployed = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=True, name="deployerCoordinator", type="address"),
        ABIEventParams(indexed=False, name="hyperdrive", type="address"),
        ABIEventParams(indexed=False, name="config", type="tuple"),
        ABIEventParams(indexed=False, name="extraData", type="bytes"),
    ],
    name="Deployed",
    type="event",
)

DeployerCoordinatorAdded = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=True, name="deployerCoordinator", type="address"),
    ],
    name="DeployerCoordinatorAdded",
    type="event",
)

DeployerCoordinatorRemoved = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=True, name="deployerCoordinator", type="address"),
    ],
    name="DeployerCoordinatorRemoved",
    type="event",
)

FeeCollectorUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=True, name="newFeeCollector", type="address"),
    ],
    name="FeeCollectorUpdated",
    type="event",
)

GovernanceUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=True, name="governance", type="address"),
    ],
    name="GovernanceUpdated",
    type="event",
)

HyperdriveGovernanceUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=True, name="hyperdriveGovernance", type="address"),
    ],
    name="HyperdriveGovernanceUpdated",
    type="event",
)

LinkerCodeHashUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=True, name="newLinkerCodeHash", type="bytes32"),
    ],
    name="LinkerCodeHashUpdated",
    type="event",
)

LinkerFactoryUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=True, name="newLinkerFactory", type="address"),
    ],
    name="LinkerFactoryUpdated",
    type="event",
)

MaxCheckpointDurationUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="newMaxCheckpointDuration", type="uint256"),
    ],
    name="MaxCheckpointDurationUpdated",
    type="event",
)

MaxCircuitBreakerDeltaUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="newMaxCircuitBreakerDelta", type="uint256"),
    ],
    name="MaxCircuitBreakerDeltaUpdated",
    type="event",
)

MaxFeesUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="newMaxFees", type="tuple"),
    ],
    name="MaxFeesUpdated",
    type="event",
)

MaxFixedAPRUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="newMaxFixedAPR", type="uint256"),
    ],
    name="MaxFixedAPRUpdated",
    type="event",
)

MaxPositionDurationUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="newMaxPositionDuration", type="uint256"),
    ],
    name="MaxPositionDurationUpdated",
    type="event",
)

MaxTimeStretchAPRUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="newMaxTimeStretchAPR", type="uint256"),
    ],
    name="MaxTimeStretchAPRUpdated",
    type="event",
)

MinCheckpointDurationUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="newMinCheckpointDuration", type="uint256"),
    ],
    name="MinCheckpointDurationUpdated",
    type="event",
)

MinCircuitBreakerDeltaUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="newMinCircuitBreakerDelta", type="uint256"),
    ],
    name="MinCircuitBreakerDeltaUpdated",
    type="event",
)

MinFeesUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="newMinFees", type="tuple"),
    ],
    name="MinFeesUpdated",
    type="event",
)

MinFixedAPRUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="newMinFixedAPR", type="uint256"),
    ],
    name="MinFixedAPRUpdated",
    type="event",
)

MinPositionDurationUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="newMinPositionDuration", type="uint256"),
    ],
    name="MinPositionDurationUpdated",
    type="event",
)

MinTimeStretchAPRUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="newMinTimeStretchAPR", type="uint256"),
    ],
    name="MinTimeStretchAPRUpdated",
    type="event",
)

SweepCollectorUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=True, name="newSweepCollector", type="address"),
    ],
    name="SweepCollectorUpdated",
    type="event",
)


@dataclass
class ErrorInfo:
    """Custom contract error information."""

    name: str
    selector: str
    signature: str
    inputs: list[ErrorParams]


@dataclass
class ErrorParams:
    """Parameter info for custom contract errors."""

    name: str
    solidity_type: str
    python_type: str


DeployerCoordinatorAlreadyAddedError = ErrorInfo(
    inputs=[],
    name="DeployerCoordinatorAlreadyAdded",
    selector="0xbd34634f",
    signature="DeployerCoordinatorAlreadyAdded()",
)

DeployerCoordinatorIndexMismatchError = ErrorInfo(
    inputs=[],
    name="DeployerCoordinatorIndexMismatch",
    selector="0x3c9c032c",
    signature="DeployerCoordinatorIndexMismatch()",
)

DeployerCoordinatorNotAddedError = ErrorInfo(
    inputs=[],
    name="DeployerCoordinatorNotAdded",
    selector="0x4bf121ab",
    signature="DeployerCoordinatorNotAdded()",
)

EndIndexTooLargeError = ErrorInfo(
    inputs=[],
    name="EndIndexTooLarge",
    selector="0xe0f7becb",
    signature="EndIndexTooLarge()",
)

InvalidCheckpointDurationError = ErrorInfo(
    inputs=[],
    name="InvalidCheckpointDuration",
    selector="0x5428734d",
    signature="InvalidCheckpointDuration()",
)

InvalidCheckpointDurationResolutionError = ErrorInfo(
    inputs=[],
    name="InvalidCheckpointDurationResolution",
    selector="0x8dbae0a8",
    signature="InvalidCheckpointDurationResolution()",
)

InvalidCircuitBreakerDeltaError = ErrorInfo(
    inputs=[],
    name="InvalidCircuitBreakerDelta",
    selector="0xef9bc65f",
    signature="InvalidCircuitBreakerDelta()",
)

InvalidDeployConfigError = ErrorInfo(
    inputs=[],
    name="InvalidDeployConfig",
    selector="0xe8c02dd7",
    signature="InvalidDeployConfig()",
)

InvalidDeployerCoordinatorError = ErrorInfo(
    inputs=[],
    name="InvalidDeployerCoordinator",
    selector="0x6e623f0f",
    signature="InvalidDeployerCoordinator()",
)

InvalidFeesError = ErrorInfo(
    inputs=[],
    name="InvalidFees",
    selector="0x2d8768f9",
    signature="InvalidFees()",
)

InvalidFixedAPRError = ErrorInfo(
    inputs=[],
    name="InvalidFixedAPR",
    selector="0x30554de1",
    signature="InvalidFixedAPR()",
)

InvalidIndexesError = ErrorInfo(
    inputs=[],
    name="InvalidIndexes",
    selector="0x764e6b56",
    signature="InvalidIndexes()",
)

InvalidMaxCheckpointDurationError = ErrorInfo(
    inputs=[],
    name="InvalidMaxCheckpointDuration",
    selector="0xf9c0959d",
    signature="InvalidMaxCheckpointDuration()",
)

InvalidMaxCircuitBreakerDeltaError = ErrorInfo(
    inputs=[],
    name="InvalidMaxCircuitBreakerDelta",
    selector="0xfdb80c26",
    signature="InvalidMaxCircuitBreakerDelta()",
)

InvalidMaxFeesError = ErrorInfo(
    inputs=[],
    name="InvalidMaxFees",
    selector="0x2c20e3f6",
    signature="InvalidMaxFees()",
)

InvalidMaxFixedAPRError = ErrorInfo(
    inputs=[],
    name="InvalidMaxFixedAPR",
    selector="0x673edec0",
    signature="InvalidMaxFixedAPR()",
)

InvalidMaxPositionDurationError = ErrorInfo(
    inputs=[],
    name="InvalidMaxPositionDuration",
    selector="0xcfb699cb",
    signature="InvalidMaxPositionDuration()",
)

InvalidMaxTimeStretchAPRError = ErrorInfo(
    inputs=[],
    name="InvalidMaxTimeStretchAPR",
    selector="0xa35539d0",
    signature="InvalidMaxTimeStretchAPR()",
)

InvalidMinCheckpointDurationError = ErrorInfo(
    inputs=[],
    name="InvalidMinCheckpointDuration",
    selector="0x0433acc6",
    signature="InvalidMinCheckpointDuration()",
)

InvalidMinCircuitBreakerDeltaError = ErrorInfo(
    inputs=[],
    name="InvalidMinCircuitBreakerDelta",
    selector="0x28a2d9a9",
    signature="InvalidMinCircuitBreakerDelta()",
)

InvalidMinFeesError = ErrorInfo(
    inputs=[],
    name="InvalidMinFees",
    selector="0x15b05a8f",
    signature="InvalidMinFees()",
)

InvalidMinFixedAPRError = ErrorInfo(
    inputs=[],
    name="InvalidMinFixedAPR",
    selector="0x1670f797",
    signature="InvalidMinFixedAPR()",
)

InvalidMinPositionDurationError = ErrorInfo(
    inputs=[],
    name="InvalidMinPositionDuration",
    selector="0x600f5a02",
    signature="InvalidMinPositionDuration()",
)

InvalidMinTimeStretchAPRError = ErrorInfo(
    inputs=[],
    name="InvalidMinTimeStretchAPR",
    selector="0x5a8f6557",
    signature="InvalidMinTimeStretchAPR()",
)

InvalidPositionDurationError = ErrorInfo(
    inputs=[],
    name="InvalidPositionDuration",
    selector="0x4a7fff9e",
    signature="InvalidPositionDuration()",
)

InvalidTimeStretchAPRError = ErrorInfo(
    inputs=[],
    name="InvalidTimeStretchAPR",
    selector="0x83ebdfb7",
    signature="InvalidTimeStretchAPR()",
)

LnInvalidInputError = ErrorInfo(
    inputs=[],
    name="LnInvalidInput",
    selector="0xe61b4975",
    signature="LnInvalidInput()",
)

ReceiveLockedError = ErrorInfo(
    inputs=[],
    name="ReceiveLocked",
    selector="0x5563ada8",
    signature="ReceiveLocked()",
)

TransferFailedError = ErrorInfo(
    inputs=[],
    name="TransferFailed",
    selector="0x90b8ec18",
    signature="TransferFailed()",
)

UnauthorizedError = ErrorInfo(
    inputs=[],
    name="Unauthorized",
    selector="0x82b42900",
    signature="Unauthorized()",
)

UnsafeCastToInt256Error = ErrorInfo(
    inputs=[],
    name="UnsafeCastToInt256",
    selector="0x72dd4e02",
    signature="UnsafeCastToInt256()",
)

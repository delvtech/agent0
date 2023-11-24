"""Dataclasses for all structs in the ERC4626HyperdriveFactory contract."""
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


@dataclass
class Fees:
    """Fees struct."""

    curve: int
    flat: int
    governance: int


@dataclass
class FactoryConfig:
    """FactoryConfig struct."""

    governance: str
    hyperdriveGovernance: str
    defaultPausers: list[str]
    feeCollector: str
    fees: Fees
    maxFees: Fees
    hyperdriveDeployer: str
    target0Deployer: str
    target1Deployer: str
    linkerFactory: str
    linkerCodeHash: bytes


@dataclass
class PoolConfig:
    """PoolConfig struct."""

    baseToken: str
    linkerFactory: str
    linkerCodeHash: bytes
    initialSharePrice: int
    minimumShareReserves: int
    minimumTransactionAmount: int
    precisionThreshold: int
    positionDuration: int
    checkpointDuration: int
    timeStretch: int
    governance: str
    feeCollector: str
    fees: Fees


Deployed = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=True, name="version", type="uint256"),
        ABIEventParams(indexed=False, name="hyperdrive", type="address"),
        ABIEventParams(indexed=False, name="config", type="tuple"),
        ABIEventParams(indexed=False, name="extraData", type="bytes32[]"),
    ],
    name="Deployed",
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

ImplementationUpdated = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=True, name="newDeployer", type="address"),
    ],
    name="ImplementationUpdated",
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

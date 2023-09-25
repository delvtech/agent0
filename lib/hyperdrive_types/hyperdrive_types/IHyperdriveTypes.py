"""Dataclasses for all structs in the IHyperdrive contract."""
# super() call methods are generic, while our version adds values & types
# pylint: disable=arguments-differ
# contracts have PascalCase names
# pylint: disable=invalid-name
# unable to control how many instance attributes we have in generated code
# pylint: disable=too-many-instance-attributes
from __future__ import annotations

from dataclasses import dataclass

from web3.types import ABIEvent, ABIEventParams


@dataclass
class Checkpoint:
    """Checkpoint struct."""

    sharePrice: int
    longSharePrice: int
    longExposure: int


@dataclass
class MarketState:
    """MarketState struct."""

    shareReserves: int
    bondReserves: int
    longsOutstanding: int
    shortsOutstanding: int
    longAverageMaturityTime: int
    longOpenSharePrice: int
    shortAverageMaturityTime: int
    longExposure: int
    isInitialized: bool
    isPaused: bool


@dataclass
class Fees:
    """Fees struct."""

    curve: int
    flat: int
    governance: int


@dataclass
class PoolConfig:
    """PoolConfig struct."""

    baseToken: str
    initialSharePrice: int
    minimumShareReserves: int
    positionDuration: int
    checkpointDuration: int
    timeStretch: int
    governance: str
    feeCollector: str
    Fees: Fees
    oracleSize: int
    updateGap: int


@dataclass
class PoolInfo:
    """PoolInfo struct."""

    shareReserves: int
    bondReserves: int
    lpTotalSupply: int
    sharePrice: int
    longsOutstanding: int
    longAverageMaturityTime: int
    shortsOutstanding: int
    shortAverageMaturityTime: int
    withdrawalSharesReadyToWithdraw: int
    withdrawalSharesProceeds: int
    lpSharePrice: int
    longExposure: int


@dataclass
class WithdrawPool:
    """WithdrawPool struct."""

    readyToWithdraw: int
    proceeds: int


AddLiquidity = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="baseAmount", type="uint256"),
    ],
    name="AddLiquidity",
    type="event",
)

Approval = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="value", type="uint256"),
    ],
    name="Approval",
    type="event",
)

ApprovalForAll = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="approved", type="bool"),
    ],
    name="ApprovalForAll",
    type="event",
)

CloseLong = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="bondAmount", type="uint256"),
    ],
    name="CloseLong",
    type="event",
)

CloseShort = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="bondAmount", type="uint256"),
    ],
    name="CloseShort",
    type="event",
)

Initialize = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="apr", type="uint256"),
    ],
    name="Initialize",
    type="event",
)

OpenLong = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="bondAmount", type="uint256"),
    ],
    name="OpenLong",
    type="event",
)

OpenShort = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="bondAmount", type="uint256"),
    ],
    name="OpenShort",
    type="event",
)

RedeemWithdrawalShares = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="baseAmount", type="uint256"),
    ],
    name="RedeemWithdrawalShares",
    type="event",
)

RemoveLiquidity = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="withdrawalShareAmount", type="uint256"),
    ],
    name="RemoveLiquidity",
    type="event",
)

TransferSingle = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="value", type="uint256"),
    ],
    name="TransferSingle",
    type="event",
)

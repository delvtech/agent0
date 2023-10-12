"""Dataclasses for all structs in the ERC4626DataProvider contract."""
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


@dataclass
class Checkpoint:
    """Checkpoint struct."""

    sharePrice: int
    longExposure: int


@dataclass
class MarketState:
    """MarketState struct."""

    shareReserves: int
    bondReserves: int
    shareAdjustment: int
    longExposure: int
    longsOutstanding: int
    shortsOutstanding: int
    longAverageMaturityTime: int
    shortAverageMaturityTime: int
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
    minimumTransactionAmount: int
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
    shareAdjustment: int
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

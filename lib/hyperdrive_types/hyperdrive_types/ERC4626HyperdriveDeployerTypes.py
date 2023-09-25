# pylint: disable=invalid-name
"""Dataclasses for all structs in the ERC4626HyperdriveDeployer contract."""
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

# pylint: disable=invalid-name
"""Dataclasses for all structs in the ERC4626HyperdriveDeployer contract."""

from web3.types import ABIEvent, ABIEventParams

from dataclasses import dataclass


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

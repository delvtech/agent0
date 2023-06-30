"""Pool info struct retured from hyperdrive contract"""
from __future__ import annotations

from dataclasses import dataclass

from fixedpointmath import FixedPoint


@dataclass
class PoolInfo:
    """Pool info struct returned from hyperdrive contract"""

    # solidity returns things in camelCase.  Keeping the formatting to indicate the source.
    # pylint: disable=invalid-name
    # this is what is returned from the contract, no choice here
    # pylint: disable=too-many-instance-attributes

    timestamp: int
    blockNumber: int
    shareReserves: FixedPoint | None = None
    bondReserves: FixedPoint | None = None
    lpTotalSupply: FixedPoint | None = None
    sharePrice: FixedPoint | None = None
    longsOutstanding: FixedPoint | None = None
    longAverageMaturityTime: FixedPoint | None = None
    shortsOutstanding: FixedPoint | None = None
    shortAverageMaturityTime: FixedPoint | None = None
    shortBaseVolume: FixedPoint | None = None
    withdrawalSharesReadyToWithdraw: FixedPoint | None = None
    withdrawalSharesProceeds: FixedPoint | None = None

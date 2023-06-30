"""Pool info struct retured from hyperdrive contract"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PoolInfo:
    """Pool info struct returned from hyperdrive contract"""

    # solidity returns things in camelCase.  Keeping the formatting to indicate the source.
    # pylint: disable=invalid-name
    # this is what is returned from the contract, no choice here
    # pylint: disable=too-many-instance-attributes

    shareReserves: int | None = None
    bondReserves: int | None = None
    lpTotalSupply: int | None = None
    sharePrice: int | None = None
    longsOutstanding: int | None = None
    longAverageMaturityTime: int | None = None
    shortsOutstanding: int | None = None
    shortAverageMaturityTime: int | None = None
    shortBaseVolume: int | None = None
    withdrawalSharesReadyToWithdraw: int | None = None
    withdrawalSharesProceeds: int | None = None
    timestamp: int | None = None
    blockNumber: int | None = None

"""Pool info struct retured from hyperdrive contract"""
from dataclasses import dataclass

# solidity returns things in camelCase.  Keeping the formatting to indicate the source.
# pylint: disable=invalid-name


@dataclass
class PoolInfo:
    """Pool info struct returned from hyperdrive contract"""

    shareReserves: int = 0
    bondReserves: int = 0
    lpTotalSupply: int = 0
    sharePrice: int = 0
    longsOutstanding: int = 0
    longAverageMaturityTime: int = 0
    shortsOutstanding: int = 0
    shortAverageMaturityTime: int = 0
    shortBaseVolume: int = 0
    withdrawalSharesReadyToWithdraw: int = 0
    withdrawalSharesProceeds: int = 0
    timestamp: int = 0
    blockNumber: int = 0

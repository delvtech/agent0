"""Functions for storing Hyperdrive state."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from fixedpointmath import FixedPoint

from .fees import Fees


@dataclass
class PoolConfig:
    """PoolConfig struct."""

    base_token: str
    linker_factory: str
    linker_code_hash: bytes
    initial_share_price: FixedPoint
    minimum_share_reserves: FixedPoint
    minimum_transaction_amount: FixedPoint
    precision_threshold: int
    position_duration: int
    checkpoint_duration: int
    time_stretch: FixedPoint
    governance: str
    fee_collector: str
    # TODO: Pyright:
    # Declaration "fees" is obscured by a declaration of the same name here but not elsewhere
    fees: Fees | Sequence  # type: ignore

    def __post_init__(self):
        if isinstance(self.fees, Sequence):
            self.fees: Fees = Fees(*self.fees)

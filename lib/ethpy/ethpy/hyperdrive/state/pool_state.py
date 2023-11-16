"""Functions for storing Hyperdrive state."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fixedpointmath import FixedPoint
from web3.types import BlockData

from ..api._block_getters import _get_block_number, _get_block_time
from .checkpoint import Checkpoint
from .conversions import (
    dataclass_to_dict,
    fixedpoint_checkpoint_to_hypertypes,
    fixedpoint_pool_config_to_hypertypes,
    fixedpoint_pool_info_to_hypertypes,
)
from .pool_config import PoolConfig
from .pool_info import PoolInfo


@dataclass
class PoolState:
    r"""A collection of stateful variables for deployed Hyperdrive and Yield contracts."""
    block: BlockData
    pool_config: PoolConfig
    pool_info: PoolInfo
    checkpoint: Checkpoint
    variable_rate: FixedPoint
    vault_shares: FixedPoint
    total_supply_withdrawal_shares: FixedPoint

    def __post_init__(self):
        self.block_number = _get_block_number(self.block)
        self.block_time = _get_block_time(self.block)

    @property
    def contract_pool_info(self) -> dict[str, Any]:
        """Get the pool_info property."""
        return dataclass_to_dict(fixedpoint_pool_info_to_hypertypes(self.pool_info))

    @property
    def contract_pool_config(self) -> dict[str, Any]:
        """Get the pool_config property."""
        return dataclass_to_dict(fixedpoint_pool_config_to_hypertypes(self.pool_config))

    @property
    def contract_checkpoint(self) -> dict[str, Any]:
        """Get the checkpoint property."""
        return dataclass_to_dict(fixedpoint_checkpoint_to_hypertypes(self.checkpoint))

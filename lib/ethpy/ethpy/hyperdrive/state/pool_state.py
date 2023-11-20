"""Functions for storing Hyperdrive state."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fixedpointmath import FixedPoint
from web3.types import BlockData

from .....hypertypes.hypertypes.utilities.conversions import (
    fixedpoint_checkpoint_to_hypertypes,
    fixedpoint_pool_config_to_hypertypes,
    fixedpoint_pool_info_to_hypertypes,
)
from .checkpoint import Checkpoint
from .conversions import dataclass_to_dict
from .pool_config import PoolConfig
from .pool_info import PoolInfo

# pylint: disable=too-many-instance-attributes


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
        ## TODO: Get these using the api getter functions without creating a circular import
        # Get the block number
        block_number = self.block.get("number", None)
        if block_number is None:
            raise AssertionError("The provided block has no number")
        self.block_number = block_number
        # Get the block timestamp
        block_timestamp = self.block.get("timestamp", None)
        if block_timestamp is None:
            raise AssertionError("The provided block has no timestamp")
        self.block_time = block_timestamp

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

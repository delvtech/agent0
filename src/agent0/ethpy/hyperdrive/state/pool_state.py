"""Functions for storing Hyperdrive state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fixedpointmath import FixedPoint
from web3.types import BlockData

from agent0.hypertypes.fixedpoint_types import CheckpointFP, PoolConfigFP, PoolInfoFP
from agent0.hypertypes.utilities.conversions import (
    dataclass_to_dict,
    fixedpoint_to_checkpoint,
    fixedpoint_to_pool_config,
    fixedpoint_to_pool_info,
)

# pylint: disable=too-many-instance-attributes


@dataclass
class PoolState:
    r"""A collection of stateful variables for deployed Hyperdrive and Yield contracts."""

    block: BlockData
    pool_config: PoolConfigFP
    pool_info: PoolInfoFP
    checkpoint_time: int
    checkpoint: CheckpointFP
    exposure: FixedPoint
    # TODO we may want to remove this from pool state and have users explicitly
    # retrieve variable rate via a function
    variable_rate: FixedPoint | None
    vault_shares: FixedPoint
    total_supply_withdrawal_shares: FixedPoint
    hyperdrive_base_balance: FixedPoint
    hyperdrive_eth_balance: FixedPoint
    gov_fees_accrued: FixedPoint

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
    def pool_info_to_dict(self) -> dict[str, Any]:
        """Get the pool_info property."""
        return dataclass_to_dict(fixedpoint_to_pool_info(self.pool_info))

    @property
    def pool_config_to_dict(self) -> dict[str, Any]:
        """Get the pool_config property."""
        return dataclass_to_dict(fixedpoint_to_pool_config(self.pool_config))

    @property
    def checkpoint_to_dict(self) -> dict[str, Any]:
        """Get the checkpoint property."""
        return dataclass_to_dict(fixedpoint_to_checkpoint(self.checkpoint))

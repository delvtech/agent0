"""Functions for storing Hyperdrive state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fixedpointmath import FixedPoint
from hyperdrivetypes import CheckpointFP, PoolConfigFP, PoolInfoFP
from web3.types import BlockData

from agent0.utils.conversions import dataclass_to_dict

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
        return dataclass_to_dict(self.pool_info.to_pypechain())

    @property
    def pool_config_to_dict(self) -> dict[str, Any]:
        """Get the pool_config property."""
        return dataclass_to_dict(self.pool_config.to_pypechain())

    @property
    def checkpoint_to_dict(self) -> dict[str, Any]:
        """Get the checkpoint property."""
        return dataclass_to_dict(self.checkpoint.to_pypechain())

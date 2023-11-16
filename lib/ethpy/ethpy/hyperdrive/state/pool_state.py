"""Functions for storing Hyperdrive state."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fixedpointmath import FixedPoint
from web3.types import BlockData

from ..api._block_getters import _get_block_number, _get_block_time
from .checkpoint import Checkpoint
from .conversions import (
    convert_hyperdrive_checkpoint_types,
    convert_hyperdrive_pool_config_types,
    convert_hyperdrive_pool_info_types,
    dataclass_to_dict,
)
from .pool_config import PoolConfig
from .pool_info import PoolInfo


@dataclass
class PoolState:
    r"""A collection of stateful variables for deployed Hyperdrive and Yield contracts."""
    block: BlockData
    contract_pool_config: dict[str, Any]
    contract_pool_info: dict[str, Any]
    contract_checkpoint: dict[str, int]
    variable_rate: FixedPoint
    vault_shares: FixedPoint
    total_supply_withdrawal_shares: FixedPoint

    def __post_init__(self):
        self.block_number = _get_block_number(self.block)
        self.block_time = _get_block_time(self.block)

    @property
    def pool_info(self) -> PoolInfo:
        """Get the pool_info property."""
        return convert_hyperdrive_pool_info_types(self.contract_pool_info)

    @pool_info.setter
    def pool_info(self, value: PoolInfo) -> None:
        """Set the pool_info property."""
        self.contract_pool_info = dataclass_to_dict(value)

    @property
    def pool_config(self) -> PoolConfig:
        """Get the pool_config property."""
        return convert_hyperdrive_pool_config_types(self.contract_pool_config)

    @pool_config.setter
    def pool_config(self, value: PoolConfig) -> None:
        """Set the pool_config property."""
        self.contract_pool_config = dataclass_to_dict(value)

    @property
    def checkpoint(self) -> PoolConfig:
        """Get the checkpoint property."""
        return convert_hyperdrive_checkpoint_types(self.contract_checkpoint)

    @checkpoint.setter
    def checkpoint(self, value: Checkpoint) -> None:
        """Set the checkpoint property."""
        self.contract_checkpoint = dataclass_to_dict(value)

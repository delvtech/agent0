"""Functions for storing Hyperdrive state."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fixedpointmath import FixedPoint
from web3.types import BlockData

from ..api._block_getters import _get_block_number, _get_block_time
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
        self._pool_config = convert_hyperdrive_pool_config_types(self.contract_pool_config)
        self._pool_info = convert_hyperdrive_pool_info_types(self.contract_pool_info)
        self.checkpoint = convert_hyperdrive_checkpoint_types(self.contract_checkpoint)

    @property
    def pool_info(self) -> PoolInfo:
        """Get the pool_info property."""
        return self._pool_info

    @pool_info.setter
    def pool_info(self, value: PoolInfo) -> None:
        """Set the pool_info property."""
        self._pool_info = value
        self.contract_pool_info = dataclass_to_dict(self._pool_info)

    @property
    def pool_config(self) -> PoolConfig:
        """Get the pool_config property."""
        return self._pool_config

    @pool_config.setter
    def pool_config(self, value: PoolConfig) -> None:
        """Set the pool_config property."""
        self._pool_config = value
        self.contract_pool_config = dataclass_to_dict(self._pool_config)

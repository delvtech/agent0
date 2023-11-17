"""Tests for hyperdrive/state/conversions.py"""
from __future__ import annotations

from typing import cast

from eth_typing import URI
from ethpy import EthConfig
from ethpy.base.transactions import smart_contract_read
from ethpy.hyperdrive.addresses import HyperdriveAddresses
from ethpy.hyperdrive.api import HyperdriveInterface
from ethpy.hyperdrive.deploy import DeployedHyperdrivePool
from hypertypes.IHyperdriveTypes import Checkpoint as HtCheckpoint
from hypertypes.IHyperdriveTypes import PoolConfig as HtPoolConfig
from hypertypes.IHyperdriveTypes import PoolInfo as HtPoolInfo
from web3 import HTTPProvider

from .conversions import (
    contract_checkpoint_to_hypertypes,
    contract_pool_config_to_hypertypes,
    contract_pool_info_to_hypertypes,
)


class TestHyperdriveInterface:
    """Tests for the HyperdriveInterface api class."""

    def test_contract_pool_config_to_hypertypes(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Test the type conversion from a smart contract read call to Pypechain output."""
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses
        eth_config = EthConfig(artifacts_uri="not used", rpc_uri=rpc_uri, abi_dir=abi_dir)
        hyperdrive = HyperdriveInterface(eth_config, addresses=hyperdrive_contract_addresses)
        pool_config = smart_contract_read(hyperdrive.hyperdrive_contract, "getPoolConfig")
        hypertypes_pool_config = contract_pool_config_to_hypertypes(pool_config)
        assert isinstance(hypertypes_pool_config, HtPoolConfig)

    def test_contract_pool_info_to_hypertypes(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Test the type conversion from a smart contract read call to Pypechain output."""
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses
        eth_config = EthConfig(artifacts_uri="not used", rpc_uri=rpc_uri, abi_dir=abi_dir)
        hyperdrive = HyperdriveInterface(eth_config, addresses=hyperdrive_contract_addresses)
        pool_info = smart_contract_read(hyperdrive.hyperdrive_contract, "getPoolInfo")
        hypertypes_pool_info = contract_pool_info_to_hypertypes(pool_info)
        assert isinstance(hypertypes_pool_info, HtPoolInfo)

    def test_contract_checkpoint_to_hypertypes(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Test the type conversion from a smart contract read call to Pypechain output."""
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses
        eth_config = EthConfig(artifacts_uri="not used", rpc_uri=rpc_uri, abi_dir=abi_dir)
        hyperdrive = HyperdriveInterface(eth_config, addresses=hyperdrive_contract_addresses)
        block_timestamp = hyperdrive.get_block_timestamp(hyperdrive.get_current_block())
        checkpoint = smart_contract_read(hyperdrive.hyperdrive_contract, "getCheckpoint", block_timestamp)
        hypertypes_checkpoint = contract_checkpoint_to_hypertypes(checkpoint)
        assert isinstance(hypertypes_checkpoint, HtCheckpoint)

"""Tests for hyperdrive/api.py"""
from __future__ import annotations

from typing import cast

from eth_typing import URI
from ethpy import EthConfig
from ethpy.hyperdrive.addresses import HyperdriveAddresses
from ethpy.hyperdrive.deploy import DeployedHyperdrivePool
from fixedpointmath import FixedPoint
from hypertypes.types import Checkpoint, PoolConfig
from hypertypes.utilities.conversions import (
    checkpoint_to_fixedpoint,
    pool_config_to_fixedpoint,
    pool_info_to_fixedpoint,
)
from web3 import HTTPProvider

from .api import HyperdriveInterface


class TestHyperdriveInterface:
    """Tests for the HyperdriveInterface api class."""

    def test_pool_config(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Checks that the Hyperdrive pool_config matches what is returned from the smart contract.

        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses
        eth_config = EthConfig(artifacts_uri="not used", rpc_uri=rpc_uri, abi_dir=abi_dir)
        hyperdrive = HyperdriveInterface(eth_config, addresses=hyperdrive_contract_addresses)
        # TODO: remove cast when pypechain consolidates dataclasses.
        pool_config = cast(PoolConfig, hyperdrive.hyperdrive_contract.functions.getPoolConfig().call())
        assert pool_config_to_fixedpoint(pool_config) == hyperdrive.current_pool_state.pool_config

    def test_pool_info(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Checks that the Hyperdrive pool_info matches what is returned from the smart contract.

        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses
        eth_config = EthConfig(artifacts_uri="not used", rpc_uri=rpc_uri, abi_dir=abi_dir)
        hyperdrive = HyperdriveInterface(eth_config, addresses=hyperdrive_contract_addresses)
        pool_info = hyperdrive.hyperdrive_contract.functions.getPoolInfo().call()
        assert pool_info_to_fixedpoint(pool_info) == hyperdrive.current_pool_state.pool_info

    def test_checkpoint(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Checks that the Hyperdrive checkpoint matches what is returned from the smart contract.

        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses
        eth_config = EthConfig(artifacts_uri="not used", rpc_uri=rpc_uri, abi_dir=abi_dir)
        hyperdrive = HyperdriveInterface(eth_config, addresses=hyperdrive_contract_addresses)
        checkpoint_id = hyperdrive.calc_checkpoint_id(block_timestamp=hyperdrive.current_pool_state.block_time)
        # TODO: remove cast when pypechain consolidates dataclasses.
        checkpoint = cast(Checkpoint, hyperdrive.hyperdrive_contract.functions.getCheckpoint(checkpoint_id).call())
        print(f"{checkpoint=}")
        assert checkpoint_to_fixedpoint(checkpoint) == hyperdrive.current_pool_state.checkpoint

    def test_spot_price_and_fixed_rate(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Checks that the Hyperdrive spot price and fixed rate match computing it by hand.

        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses
        hyperdrive = HyperdriveInterface(
            eth_config=EthConfig(
                artifacts_uri="not used",
                rpc_uri=rpc_uri,
                abi_dir="./packages/hyperdrive/src/abis",
            ),
            addresses=hyperdrive_contract_addresses,
        )
        # get pool config variables
        pool_config = hyperdrive.current_pool_state.pool_config
        init_share_price: FixedPoint = pool_config.initial_share_price
        time_stretch: FixedPoint = pool_config.time_stretch
        # get pool info variables
        pool_info = hyperdrive.current_pool_state.pool_info
        share_reserves: FixedPoint = pool_info.share_reserves
        bond_reserves: FixedPoint = pool_info.bond_reserves
        # test spot price
        spot_price = ((init_share_price * share_reserves) / bond_reserves) ** time_stretch
        assert abs(spot_price - hyperdrive.calc_spot_price()) <= FixedPoint(scaled_value=1)
        # test fixed rate (rounding issues can cause it to be off by 1e-18)
        # TODO: This should be exact up to 1e-18, but is not
        fixed_rate = (FixedPoint(1) - spot_price) / (spot_price * hyperdrive.calc_position_duration_in_years())
        assert abs(fixed_rate - hyperdrive.calc_fixed_rate()) <= FixedPoint(scaled_value=100)

    def test_misc(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Placeholder for additional tests.

        These are only verifying that the attributes exist and functions can be called.
        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses
        eth_config = EthConfig(artifacts_uri="not used", rpc_uri=rpc_uri, abi_dir=abi_dir)
        hyperdrive = HyperdriveInterface(eth_config, addresses=hyperdrive_contract_addresses)
        _ = hyperdrive.current_pool_state
        _ = hyperdrive.current_pool_state.variable_rate
        _ = hyperdrive.current_pool_state.vault_shares
        _ = hyperdrive.calc_open_long(FixedPoint(100))
        _ = hyperdrive.calc_open_short(FixedPoint(100))
        _ = hyperdrive.calc_bonds_given_shares_and_rate(FixedPoint(0.05))
        _ = hyperdrive.calc_max_long(FixedPoint(1000))
        _ = hyperdrive.calc_max_short(FixedPoint(1000))
        # TODO: need an agent address to mock up trades

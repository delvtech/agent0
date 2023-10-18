"""Tests for hyperdrive/api.py"""
from __future__ import annotations

from typing import cast

from eth_typing import URI
from ethpy import EthConfig
from ethpy.base.transactions import smart_contract_read
from fixedpointmath import FixedPoint
from web3 import HTTPProvider

from .addresses import HyperdriveAddresses
from .api import HyperdriveInterface
from .deploy import DeployedHyperdrivePool


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
        pool_config = smart_contract_read(hyperdrive.hyperdrive_contract, "getPoolConfig")
        assert pool_config == hyperdrive._contract_pool_config  # pylint: disable=protected-access

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
        pool_info = smart_contract_read(hyperdrive.hyperdrive_contract, "getPoolInfo")
        assert pool_info == hyperdrive._contract_pool_info  # pylint: disable=protected-access

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
        checkpoint = smart_contract_read(
            hyperdrive.hyperdrive_contract, "getCheckpoint", hyperdrive.current_block_number
        )
        assert checkpoint == hyperdrive._contract_latest_checkpoint  # pylint: disable=protected-access

    def test_spot_price_and_fixed_rate(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Checks that the Hyperdrive spot price and fixed rate matche computing it by hand.

        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses
        hyperdrive = HyperdriveInterface(
            eth_config=EthConfig(artifacts_uri="not used", rpc_uri=rpc_uri, abi_dir="./packages/hyperdrive/src/abis"),
            addresses=hyperdrive_contract_addresses,
        )
        # get pool config variables
        pool_config = hyperdrive.pool_config
        init_share_price: FixedPoint = pool_config["initialSharePrice"]
        time_stretch: FixedPoint = pool_config["timeStretch"]
        # get pool info variables
        pool_info = hyperdrive.pool_info
        share_reserves: FixedPoint = pool_info["shareReserves"]
        bond_reserves: FixedPoint = pool_info["bondReserves"]
        # test spot price
        # TODO: This should be exact up to 1e-18, but is not
        spot_price = ((init_share_price * share_reserves) / bond_reserves) ** time_stretch
        assert abs(spot_price - hyperdrive.spot_price) <= FixedPoint(scaled_value=1)
        # test fixed rate (rounding issues can cause it to be off by 1e-18)
        # TODO: This should be exact up to 1e-18, but is not
        fixed_rate = (FixedPoint(1) - spot_price) / (spot_price * hyperdrive.position_duration_in_years)
        assert abs(fixed_rate - hyperdrive.fixed_rate) <= FixedPoint(scaled_value=100)

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
        _ = hyperdrive.pool_config
        _ = hyperdrive.pool_info
        _ = hyperdrive.latest_checkpoint
        _ = hyperdrive.current_block
        _ = hyperdrive.current_block_number
        _ = hyperdrive.current_block_time
        _ = hyperdrive.variable_rate
        _ = hyperdrive.vault_shares
        _ = hyperdrive.get_max_long(FixedPoint(1000))
        _ = hyperdrive.get_max_short(FixedPoint(1000))
        # TODO: need an agent address to mock up trades

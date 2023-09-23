"""Tests for hyperdrive/api.py"""
from __future__ import annotations

from typing import cast

import pytest
from eth_typing import URI
from ethpy.base.transactions import smart_contract_read
from ethpy.hyperdrive.addresses import HyperdriveAddresses
from ethpy.hyperdrive.api import HyperdriveInterface
from ethpy.test_fixtures.local_chain import LocalHyperdriveChain
from fixedpointmath import FixedPoint
from web3 import HTTPProvider


@pytest.mark.skip(reason="Can't test this until we update the IHyperdrive.json ABI")
class TestHyperdriveInterface:
    """Tests for the HyperdriveInterface api class."""

    def test_pool_config(self, local_hyperdrive_chain: LocalHyperdriveChain):
        """Checks that the Hyperdrive pool_config matches what is returned from the smart contract.

        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_chain.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_chain.hyperdrive_contract_addresses
        hyperdrive = HyperdriveInterface(artifacts=hyperdrive_contract_addresses, rpc_uri=rpc_uri, abi_dir=abi_dir)
        pool_config = smart_contract_read(hyperdrive.hyperdrive_contract, "getPoolConfig")
        assert pool_config == hyperdrive._contract_pool_config  # pylint: disable=protected-access

    def test_pool_info(self, local_hyperdrive_chain: LocalHyperdriveChain):
        """Checks that the Hyperdrive pool_info matches what is returned from the smart contract.

        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_chain.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_chain.hyperdrive_contract_addresses
        hyperdrive = HyperdriveInterface(artifacts=hyperdrive_contract_addresses, rpc_uri=rpc_uri, abi_dir=abi_dir)
        pool_info = smart_contract_read(hyperdrive.hyperdrive_contract, "getPoolInfo")
        assert pool_info == hyperdrive._contract_pool_info  # pylint: disable=protected-access

    def test_checkpoint(self, local_hyperdrive_chain: LocalHyperdriveChain):
        """Checks that the Hyperdrive checkpoint matches what is returned from the smart contract.

        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_chain.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_chain.hyperdrive_contract_addresses
        hyperdrive = HyperdriveInterface(artifacts=hyperdrive_contract_addresses, rpc_uri=rpc_uri, abi_dir=abi_dir)
        checkpoint = smart_contract_read(
            hyperdrive.hyperdrive_contract, "getCheckpoint", hyperdrive.current_block_number
        )
        assert checkpoint == hyperdrive._contract_latest_checkpoint  # pylint: disable=protected-access

    def test_misc(self, local_hyperdrive_chain: LocalHyperdriveChain):
        """Placeholder for additional tests.

        These are only verifying that the attributes exist and functions can be called.
        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_chain.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_chain.hyperdrive_contract_addresses
        hyperdrive = HyperdriveInterface(artifacts=hyperdrive_contract_addresses, rpc_uri=rpc_uri, abi_dir=abi_dir)
        _ = hyperdrive.pool_config
        _ = hyperdrive.pool_info
        _ = hyperdrive.latest_checkpoint
        _ = hyperdrive.current_block
        _ = hyperdrive.current_block_number
        _ = hyperdrive.current_block_time
        _ = hyperdrive.spot_price
        _ = hyperdrive.get_max_long(FixedPoint(1000))
        _ = hyperdrive.get_max_short(FixedPoint(1000))
        # TODO: need an agent address to mock up trades

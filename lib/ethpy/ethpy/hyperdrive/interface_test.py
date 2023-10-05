"""Tests for hyperdrive/api.py"""
from __future__ import annotations

from typing import cast

from eth_typing import URI
from ethpy import EthConfig
from ethpy.base.transactions import smart_contract_read
from ethpy.hyperdrive.addresses import HyperdriveAddresses
from ethpy.test_fixtures.local_chain import LocalHyperdriveChain
from web3 import HTTPProvider

from .get_web3_and_hyperdrive_contracts import get_web3_and_hyperdrive_contracts

# pylint: disable=too-many-locals


class TestHyperdriveInterface:
    """Tests for the low-level hyperdrive interface functions."""

    def test_get_pool_config(self, local_hyperdrive_chain: LocalHyperdriveChain):
        """Checks that the Hyperdrive smart contract function getPoolConfig works.

        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_chain.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_chain.hyperdrive_contract_addresses
        eth_config = EthConfig(artifacts_uri="not used", rpc_uri=rpc_uri, abi_dir=abi_dir)
        _, _, hyperdrive_contract = get_web3_and_hyperdrive_contracts(eth_config, hyperdrive_contract_addresses)
        pool_config = smart_contract_read(hyperdrive_contract, "getPoolConfig")
        assert pool_config is not None

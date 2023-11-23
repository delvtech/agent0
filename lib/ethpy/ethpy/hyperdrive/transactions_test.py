"""Tests for hyperdrive/api.py"""
from __future__ import annotations

from typing import cast

from eth_typing import URI
from ethpy import EthConfig
from web3 import HTTPProvider

from .addresses import HyperdriveAddresses
from .deploy import DeployedHyperdrivePool
from .get_web3_and_hyperdrive_contracts import get_web3_and_hyperdrive_contracts

# pylint: disable=too-many-locals


class TestHyperdriveInterface:
    """Tests for the low-level hyperdrive interface functions."""

    def test_get_pool_config(self, local_hyperdrive_pool: DeployedHyperdrivePool):
        """Checks that the Hyperdrive smart contract function getPoolConfig works.

        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_pool.hyperdrive_contract_addresses
        eth_config = EthConfig(artifacts_uri="not used", rpc_uri=rpc_uri, abi_dir=abi_dir)
        contracts = get_web3_and_hyperdrive_contracts(eth_config, hyperdrive_contract_addresses)
        pool_config = contracts.hyperdrive_contract.functions.getPoolConfig().call()
        assert pool_config is not None

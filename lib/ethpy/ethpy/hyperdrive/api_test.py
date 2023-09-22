"""Tests for hyperdrive/api.py"""
from __future__ import annotations

from typing import cast

from eth_account.signers.local import LocalAccount
from eth_typing import URI
from ethpy.base.transactions import smart_contract_read
from ethpy.hyperdrive.addresses import HyperdriveAddresses
from ethpy.hyperdrive.api import HyperdriveInterface
from ethpy.test_fixtures.local_chain import LocalHyperdriveChain
from web3 import HTTPProvider


class TestHyperdriveInterface:
    """Tests for the HyperdriveInterface api class."""

    def test_pool_config(
        self,
        local_hyperdrive_chain: LocalHyperdriveChain,
    ):
        """Checks that the Hyperdrive pool_config matches what is returned from the smart contract.

        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_chain.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        deploy_account: LocalAccount = local_hyperdrive_chain.deploy_account
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_chain.hyperdrive_contract_addresses
        hyperdrive = HyperdriveInterface(artifacts=hyperdrive_contract_addresses, rpc_uri=rpc_uri, abi_dir=abi_dir)
        pool_config = smart_contract_read(hyperdrive.hyperdrive_contract, "getPoolConfig")
        assert pool_config == hyperdrive._contract_pool_config  # pylint: disable=protected-access

    def test_pool_info(
        self,
        local_hyperdrive_chain: LocalHyperdriveChain,
    ):
        """Checks that the Hyperdrive pool_info matches what is returned from the smart contract.

        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_chain.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        abi_dir = "./packages/hyperdrive/src/abis"
        deploy_account: LocalAccount = local_hyperdrive_chain.deploy_account
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_chain.hyperdrive_contract_addresses
        hyperdrive = HyperdriveInterface(artifacts=hyperdrive_contract_addresses, rpc_uri=rpc_uri, abi_dir=abi_dir)
        pool_info = smart_contract_read(hyperdrive.hyperdrive_contract, "getPoolInfo")
        assert pool_info == hyperdrive._contract_pool_info  # pylint: disable=protected-access

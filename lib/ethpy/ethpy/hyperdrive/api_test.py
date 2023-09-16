"""Tests for hyperdrive/api.py"""
from __future__ import annotations

from typing import cast

from eth_account.signers.local import LocalAccount
from eth_typing import URI
from ethpy import EthConfig
from ethpy.base.transactions import smart_contract_read
from ethpy.hyperdrive.addresses import HyperdriveAddresses
from ethpy.hyperdrive.api import HyperdriveInterface
from ethpy.test_fixtures import local_chain, local_hyperdrive_chain  # pylint: disable=unused-import, ungrouped-imports
from ethpy.test_fixtures.local_chain import LocalHyperdriveChain
from web3 import HTTPProvider


class TestHyperdriveInterface:
    """Tests for the HyperdriveInterface api class."""

    def test_hyperdrive_interface(
        self,
        local_hyperdrive_chain: LocalHyperdriveChain,
    ):
        """Runs the entire pipeline and checks the database at the end.
        All arguments are fixtures.
        """
        uri: URI | None = cast(HTTPProvider, local_hyperdrive_chain.web3.provider).endpoint_uri
        rpc_uri = uri if uri else URI("http://localhost:8545")
        deploy_account: LocalAccount = local_hyperdrive_chain.deploy_account
        hyperdrive_contract_addresses: HyperdriveAddresses = local_hyperdrive_chain.hyperdrive_contract_addresses
        eth_config = EthConfig(artifacts_uri="http://localhost:8080", rpc_uri=rpc_uri)  # using default abi dir
        hyperdrive = HyperdriveInterface(eth_config)
        pool_config = smart_contract_read(hyperdrive.hyperdrive_contract, "getPoolConfig")
        assert pool_config == hyperdrive.pool_config

"""Helper function for getting web3 and contracts."""
from __future__ import annotations

import os
from typing import NamedTuple

from hypertypes.types import ERC20MintableContract, IERC4626HyperdriveContract, MockERC4626Contract
from web3 import Web3

from ethpy import EthConfig
from ethpy.base import initialize_web3_with_http_provider

from .addresses import HyperdriveAddresses, fetch_hyperdrive_address_from_uri


class GetWeb3AndHyperdriveContractsReturnValue(NamedTuple):
    """Return values for get_web3_and_hyperdrive_contracts"""

    w3: Web3
    base_token_contract: ERC20MintableContract
    yield_contract: MockERC4626Contract
    hyperdrive_contract: IERC4626HyperdriveContract


def get_web3_and_hyperdrive_contracts(
    eth_config: EthConfig, contract_addresses: HyperdriveAddresses | None = None
) -> GetWeb3AndHyperdriveContractsReturnValue:
    """Get the web3 container and the ERC20Base and Hyperdrive contracts.

    Arguments
    ---------
    eth_config: EthConfig
        Configuration for URIs to the rpc and artifacts.
    contract_addresses: HyperdriveAddresses | None
        Configuration for defining various contract addresses.
        Will query eth_config artifacts for addresses by default

    Returns
    -------
    tuple[Web3, Contract, Contract]
        A tuple containing:
            - The web3 container
            - The base token contract
            - The yield contract
            - The hyperdrive contract
    """
    # Initialize contract addresses if none
    if contract_addresses is None:
        contract_addresses = fetch_hyperdrive_address_from_uri(os.path.join(eth_config.artifacts_uri, "addresses.json"))

    # point to chain env
    web3 = initialize_web3_with_http_provider(eth_config.rpc_uri, reset_provider=False)

    # setup contracts
    base_token_contract: ERC20MintableContract = ERC20MintableContract.factory(w3=web3)(
        address=web3.to_checksum_address(contract_addresses.base_token)
    )
    hyperdrive_contract: IERC4626HyperdriveContract = IERC4626HyperdriveContract.factory(w3=web3)(
        address=web3.to_checksum_address(contract_addresses.mock_hyperdrive)
    )
    yield_address = hyperdrive_contract.functions.pool().call()
    yield_contract: MockERC4626Contract = MockERC4626Contract.factory(w3=web3)(
        address=web3.to_checksum_address(yield_address)
    )

    return GetWeb3AndHyperdriveContractsReturnValue(
        w3=web3,
        base_token_contract=base_token_contract,
        yield_contract=yield_contract,
        hyperdrive_contract=hyperdrive_contract,
    )

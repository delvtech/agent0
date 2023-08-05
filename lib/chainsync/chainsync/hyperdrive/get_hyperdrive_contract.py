"""Hyperdrive contract given some ABIs"""
from eth_utils import address
from ethpy.hyperdrive import HyperdriveAddresses
from web3 import Web3
from web3.contract.contract import Contract


def get_hyperdrive_contract(web3: Web3, abis: dict, addresses: HyperdriveAddresses) -> Contract:
    """Get the hyperdrive contract given abis.

    Arguments
    ---------
    web3: Web3
        web3 provider object
    abis: dict
        A dictionary that contains all abis keyed by the abi name, returned from `load_all_abis`
    addresses: HyperdriveAddressesJson
        The block number to query from the chain

    Returns
    -------
    Contract
        The contract object returned from the query
    """
    if "IHyperdrive" not in abis:
        raise AssertionError("IHyperdrive ABI was not provided")
    state_abi = abis["IHyperdrive"]
    # get contract instance of hyperdrive
    hyperdrive_contract: Contract = web3.eth.contract(
        address=address.to_checksum_address(addresses.mock_hyperdrive), abi=state_abi
    )
    return hyperdrive_contract

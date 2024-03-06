"""Helper function for deploying contracts using web3."""

from __future__ import annotations

from typing import Any

from eth_typing import ChecksumAddress
from web3 import Web3
from web3.contract.contract import Contract


def deploy_contract(
    web3: Web3, abi: list[Any], bytecode: str, deploy_account_addr: ChecksumAddress, args: list[Any] | None = None
) -> tuple[ChecksumAddress, Contract]:
    """Deploys a contract given the abi and the bytecode, and returns the web3 contract object along with the address.

    Note this function is blocking until the tx receipt returns, indicating a successful deployment

    Arguments
    ---------
    web3: Web3
        web3 provider object.
    abi: list[Any]
        The contract abi.
    bytecode: str
        The contract bytecode.
    deploy_account_addr: ChecksumAddress
        The address of the account that's deploying the contract.
    args: list[Any] | None:
        List of arguments to pass to the contract constructor.
        Pass None or an empty list if the function has no arguments.

    Returns
    -------
    tuple[ChecksumAddress, Contract]
        The deployed contract address and Contract object.

    """
    if args is None:
        args = []
    contract = web3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = contract.constructor(*args).transact({"from": deploy_account_addr})
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    if tx_receipt["contractAddress"] is not None:
        contract_addr = tx_receipt["contractAddress"]
        contract = web3.eth.contract(address=contract_addr, abi=abi)
        return contract_addr, contract
    raise AssertionError("Deploying contract didn't return contract address")

"""Helper function for deploying contracts using web3."""

from __future__ import annotations

from typing import Any

from web3 import Web3
from web3.contract.contract import Contract


def deploy_contract(
    web3: Web3, abi: list[Any], bytecode: str, deploy_addr: str, args: list | None = None, return_contract: bool = False
) -> str | tuple[str, Contract]:
    """Deploys a contract given the abi and the bytecode.

    Note this function is blocking until the tx receipt returns, indicating a successful deployment

    Arguments
    ---------
    web3: Web3
        web3 provider object
    abi:
        The wallet address to use for query
    block_number: BlockNumber
        The block number to query
    token_id: int | None
        The given token id. If none, assuming we're calling base contract

    Returns
    -------
    Decimal | None
        The amount token_id in wallet_addr. None if failed

    """
    if args is None:
        args = []
    contract = web3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = contract.constructor(*args).transact({"from": deploy_addr})
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    if tx_receipt["contractAddress"] is not None:
        contract_addr = tx_receipt["contractAddress"]
        if return_contract:
            contract = web3.eth.contract(address=contract_addr, abi=abi)
            return contract_addr, contract
        return contract_addr
    raise AssertionError("Deploying contract didn't return contract address")

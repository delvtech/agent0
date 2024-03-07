"""Functions for interfacing with the anvil or ethereum RPC endpoint"""

from __future__ import annotations

from web3 import Web3
from web3.types import RPCEndpoint, RPCResponse


def set_anvil_account_balance(web3: Web3, account_address: str, amount_wei: int) -> RPCResponse:
    """Set the eth balance of the the account using the web3 provider.

    Arguments
    ---------
    web3: Web3
        The instantiated web3 provider.
    account_address: str
        The address of the account to fund.
    amount_wei: int
        Amount_wei to fund, in wei.

    Returns
    -------
    RPCResponse
        success can be checked by inspecting `rpc_response.error`
    """
    if not web3.is_checksum_address(account_address):
        raise ValueError(f"argument {account_address=} must be a checksum address")
    params = [account_address, hex(amount_wei)]  # account, amount
    rpc_response = web3.provider.make_request(method=RPCEndpoint("anvil_setBalance"), params=params)
    return rpc_response


def get_account_balance(web3: Web3, account_address: str) -> int | None:
    """Get the balance for an account deployed on the web3 provider.

    Arguments
    ---------
    web3: Web3
        The instantiated web3 provider.
    account_address: str
        The address of the account to fund.

    Returns
    -------
    int | None
        The balance of the account in wei, or None if the rpc call failed.
    """
    if not web3.is_checksum_address(account_address):
        raise ValueError(f"argument {account_address=} must be a checksum address")
    rpc_response = web3.provider.make_request(method=RPCEndpoint("eth_getBalance"), params=[account_address, "latest"])
    hex_result = rpc_response.get("result")
    if hex_result is not None:
        return int(hex_result, base=16)  # cast hex to int
    return None

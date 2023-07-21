"""Functions for interfacing with the anvil or ethereum RPC endpoint"""
from __future__ import annotations

from web3 import Web3
from web3.types import RPCEndpoint, RPCResponse


def set_anvil_account_balance(web3: Web3, account_address: str, amount_wei: int) -> RPCResponse:
    """Set an the account using the web3 provider

    Arguments
    ---------
    amount_wei : int
        amount_wei to fund, in wei

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
    """Get the balance for an account deployed on the web3 provider"""
    if not web3.is_checksum_address(account_address):
        raise ValueError(f"argument {account_address=} must be a checksum address")
    rpc_response = web3.provider.make_request(method=RPCEndpoint("eth_getBalance"), params=[account_address, "latest"])
    hex_result = rpc_response.get("result")
    if hex_result is not None:
        return int(hex_result, base=16)  # cast hex to int
    return None


def get_wait_for_new_block(web3: Web3) -> bool:
    """Returns if we should wait for a new block before attempting trades again.  For anvil nodes,
       if auto-mining is enabled then every transaction sent to the block is automatically mined so
       we don't need to wait for a new block before submitting trades again.

    Arguments
    ---------
    web3 : Web3
        web3.py instantiation.

    Returns
    -------
    bool
        Whether or not to wait for a new block before attempting trades again.
    """
    automine = False
    try:
        response = web3.provider.make_request(method=RPCEndpoint("anvil_getAutomine"), params=[])
        automine = bool(response.get("result", False))
    except Exception:  # pylint: disable=broad-exception-caught
        # do nothing, this will fail for non anvil nodes and we don't care.
        automine = False
    return not automine

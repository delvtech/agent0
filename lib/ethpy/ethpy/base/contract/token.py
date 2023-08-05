"""Utilities for token contracts."""

from __future__ import annotations

import logging
import time

from eth_typing import BlockNumber
from web3.contract.contract import Contract


def get_token_balance(
    contract: Contract, wallet_address: str, block_number: BlockNumber, token_id: int | None = None
) -> int | None:
    """Queries the given contract for the wallet's token_id balance.

    If no token_id is supplied, tries an ERC20 style lookup.  If a token_id is supplied, tries an ERC1155 style lookup

    Arguments
    ---------
    contract : Contract
        The contract to query.
    wallet_address: str
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
    retry_count = 10
    balance = None
    for attempt_count in range(retry_count):
        try:
            if token_id is None:
                # ERC20
                balance = contract.functions.balanceOf(wallet_address).call(block_identifier=block_number)
            else:
                # ERC1155
                balance = contract.functions.balanceOf(token_id, wallet_address).call(block_identifier=block_number)
            break
        except ValueError:
            logging.warning("Error in getting token balance, retrying %s/%s", attempt_count + 1, retry_count)
            time.sleep(1)
            continue
    return balance

"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""
from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Any

from eth_typing import BlockNumber
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from web3.contract.contract import Contract


def _convert_scaled_value(input_val: int | None) -> Decimal | None:
    """
    Given a scaled value int, converts it to a Decimal, while supporting Nones

    Arguments
    ----------
    input_val: int | None
        The scaled integer value to unscale and convert to Decimal

    Returns
    -------
    Decimal | None
        The unscaled Decimal value
    """
    if input_val is not None:
        # TODO add this cast within fixedpoint
        fp_val = FixedPoint(scaled_value=input_val)
        str_val = str(fp_val)
        return Decimal(str_val)
    return None


def recursive_dict_conversion(obj: Any) -> Any:
    """Recursively converts a dictionary to convert objects to hex values.

    Arguments
    ---------
    obj : Any
        Could be a HexBytes, dict, or any object with the `items` attribute

    Returns
    -------
    Any
        A nested dictionary containing the decoded object values


    .. todo::
        This function needs to be better constrained & typed, or avoided all together?
    """
    if isinstance(obj, HexBytes):
        return obj.hex()
    if isinstance(obj, dict):
        return {key: recursive_dict_conversion(value) for key, value in obj.items()}
    if hasattr(obj, "items"):  # any other type with "items" attr, e.g. TypedDict and OrderedDict
        return {key: recursive_dict_conversion(value) for key, value in obj.items()}
    return obj


RETRY_COUNT = 10


def query_contract_for_balance(
    contract: Contract, wallet_address: str, block_number: BlockNumber, token_id: int | None = None
) -> Decimal | None:
    """Queries the given contract for the wallet's token_id balance.

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
    num_token_scaled = None
    for attempt_count in range(RETRY_COUNT):
        try:
            if token_id is None:
                num_token_scaled = contract.functions.balanceOf(wallet_address).call(block_identifier=block_number)
            else:
                num_token_scaled = contract.functions.balanceOf(token_id, wallet_address).call(
                    block_identifier=block_number
                )
            break
        except ValueError:
            logging.warning("Error in getting token balance, retrying %s/%s", attempt_count + 1, RETRY_COUNT)
            time.sleep(1)
            continue
    return _convert_scaled_value(num_token_scaled)

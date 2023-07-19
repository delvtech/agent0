"""Error handling for the hyperdrive ecosystem"""
from typing import Literal, Sequence, TypedDict

from eth_utils.conversions import to_hex
from eth_utils.crypto import keccak
from web3.contract.contract import Contract
from web3.types import ABIFunctionParams


def decode_error_selector_for_contract(error_selector: str, contract: Contract) -> str:
    """Decode the error selector for a contract,

    Arguments
    ---------

    error_selector : str
        A 3 byte hex string obtained from a keccak256 has of the error signature, i.e.
        'InvalidToken()' would yield '0xc1ab6dc1'.
    contract: Contract
        A web3.py Contract interface, the abi is required for this function to work.

    Returns
    -------
    str
       The name of the error. If the error is not found, returns UnknownError.
    """

    abi = contract.abi
    if not abi:
        raise ValueError("Contract does not have an abi, cannot decode the error selector.")

    errors = [
        ABIError(name=err.get("name"), inputs=err.get("inputs"), type="error")  # type: ignore
        for err in abi
        if err.get("type") == "error"
    ]

    error_name = "UnknownError"

    for error in errors:
        error_inputs = error.get("inputs")
        # build a list of argument types like 'uint256,bytes,bool'
        input_types_csv = ",".join([input_type.get("type") or "" for input_type in error_inputs])
        # create an error signature, i.e. CustomError(uint256,bool)
        error_signature = f"{error.get('name')}({input_types_csv})"
        decoded_error_selector = str(to_hex(primitive=keccak(text=error_signature)))[:10]
        if decoded_error_selector == error_selector:
            error_name = error.get("name")
            break

    return error_name


# TODO: add this to web3.py
class ABIError(TypedDict, total=True):
    """ABI error definition."""

    name: str
    inputs: Sequence[ABIFunctionParams]
    type: Literal["error"]

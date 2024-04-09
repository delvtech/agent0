"""Error handling for the hyperdrive ecosystem"""

from __future__ import annotations

from enum import Enum
from typing import Any

from eth_utils.conversions import to_hex
from eth_utils.crypto import keccak
from web3.contract.contract import Contract

from .types import ABIError


class ContractCallType(Enum):
    r"""A type of token"""

    PREVIEW = "preview"
    TRANSACTION = "transaction"
    READ = "read"


class ContractCallException(Exception):
    """Custom contract call exception wrapper that contains additional information on the function call"""

    # We'd like to pass in these optional kwargs to this exception
    # pylint: disable=too-many-arguments
    def __init__(
        self,
        *args,
        # Explicitly passing these arguments as kwargs to allow for multiple `args` to be passed in
        # similar for other types of exceptions
        orig_exception: Exception | list[Exception] | BaseException | None = None,
        contract_call_type: ContractCallType | None = None,
        function_name_or_signature: str | None = None,
        fn_args: tuple | None = None,
        fn_kwargs: dict[str, Any] | None = None,
        raw_txn: dict[str, Any] | None = None,
        block_number: int | None = None,
    ):
        super().__init__(*args)
        self.orig_exception = orig_exception
        self.contract_call_type = contract_call_type
        self.function_name_or_signature = function_name_or_signature
        self.fn_args = fn_args
        self.fn_kwargs = fn_kwargs
        self.block_number = block_number
        self.raw_txn = raw_txn


def decode_error_selector_for_contract(error_selector: str, contract: Contract) -> str:
    """Decode the error selector for a contract,

    Arguments
    ---------
    error_selector: str
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

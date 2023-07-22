"""Types used for error handling by interface functions."""
from typing import Literal, Sequence, TypedDict

from web3.types import ABIFunctionParams


# TODO: add this to web3.py
class ABIError(TypedDict, total=True):
    """ABI error definition."""

    name: str
    inputs: Sequence[ABIFunctionParams]
    type: Literal["error"]

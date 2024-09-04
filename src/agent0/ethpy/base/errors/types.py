"""Error types from Web3"""

from typing import Literal, Sequence, TypedDict

from eth_typing import ABIComponent


# TODO: add this to web3.py
class ABIError(TypedDict, total=True):
    """ABI error definition."""

    name: str
    inputs: Sequence[ABIComponent]
    type: Literal["error"]


class UnknownBlockError(Exception):
    """UnknownBlockError throws when contract trasaction receipts with status == 0."""

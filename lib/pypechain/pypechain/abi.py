"""Utilities for solidity contract ABIs."""

import json
from typing import List, NamedTuple, Optional


class Input(NamedTuple):
    """An input of a function or event."""

    internalType: str
    name: str
    type: str
    indexed: Optional[bool] = None


class Output(NamedTuple):
    """An output of a function or event."""

    internalType: str
    internalType: str
    name: str
    type: str


class AbiItem(NamedTuple):
    """An item of an ABI, can be an event, function or struct."""

    type: str
    inputs: List[Input]
    stateMutability: Optional[str] = None
    anonymous: Optional[bool] = None
    name: Optional[str] = None
    outputs: Optional[List[Output]] = None


class AbiJson(NamedTuple):
    """A JSON representation of a solidity contract's Application Boundary Interface."""

    abi: List[AbiItem]


def load_abi(abi_path: str) -> AbiJson:
    """Loads the abi file into a json."""
    with open(abi_path, "r", encoding="utf-8") as abi_file:
        data = json.load(abi_file)

        # Assuming that the ABI data structure is at the top level of the JSON
        # (i.e., the file is a list of ABI items):
        abi_items = [AbiItem(**item) for item in data]

        return AbiJson(abi=abi_items)

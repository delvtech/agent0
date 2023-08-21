"""Utilities for solidity contract ABIs."""
from __future__ import annotations

import json
from typing import List, NamedTuple, TypeGuard

from web3.types import ABI, ABIElement, ABIEvent, ABIFunction


class Input(NamedTuple):
    """An input of a function or event."""

    internalType: str
    name: str
    type: str
    indexed: bool | None = None


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
    stateMutability: str | None = None
    anonymous: bool | None = None
    name: str | None = None
    outputs: List[Output] | None = None


class AbiJson(NamedTuple):
    """A JSON representation of a solidity contract's Application Boundary Interface."""

    abi: List[AbiItem]


def load_abi(abi_path: str) -> AbiJson:
    """Loads the abi file into a json.

    Arguments
    ---------
    abi_path : str
        Where the abi json is location.

    Returns
    -------
    AbiJson
        A named tuple representation of an abi json file.
    """

    with open(abi_path, "r", encoding="utf-8") as abi_file:
        data = json.load(abi_file)

        # Assuming that the ABI data structure is at the top level of the JSON
        # (i.e., the file is a list of ABI items):
        abi_items = [AbiItem(**item) for item in data]

        return AbiJson(abi=abi_items)


def is_abi_function(item: ABIElement) -> TypeGuard[ABIFunction]:
    """Typeguard function for ABIFunction.

    Arguments
    ---------
    item:  Any
        The item we are confirming is an ABIFunction

    Returns
    -------
    TypeGuard[ABIFunction]
    """
    # Check if the required keys exist
    required_keys = ["type", "name", "inputs"]

    # Check if the required keys exist
    if not all(key in item for key in required_keys):
        return False

    # Check if the type is "function"
    if item.get("type") != "function":
        return False

    return True


def is_abi_event(item: ABIElement) -> TypeGuard[ABIEvent]:
    """Typeguard function for ABIEvent.

    Arguments
    ---------
    item:  Any
        The item we are confirming is an ABIFunction

    Returns
    -------
    TypeGuard[ABIEvent]
    """
    # Check if the required keys exist
    required_keys = ["type", "name", "inputs"]

    # Check if the required keys exist
    if not all(key in item for key in required_keys):
        return False

    # Check if the type is "event"
    if item.get("type") != "event":
        return False

    return True

@dataclass
class StructInfo:
    name: str
    values: dict[str, str | StructInfo]

def get_internal_types(abi: ABI, internal_types: list[StructInfo]) -> list[NamedTuple]:
    """Gets all the

    Parameters
    ----------
    file_path : Path
        the file path to the ABI.

    Returns
    -------
    List[Union[ABIFunction, ABIEvent]]
        _description_
    """

    # leverage the private list of ABIFunction's
    # pylint: disable=protected-access
    for abi_item in abi:

    return abi_functions_and_events
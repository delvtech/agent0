"""Conversion for hyperdrivetypes to fixedpoint"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from fixedpointmath import FixedPoint
from hyperdrivetypes import FeesFP
from hyperdrivetypes.types.IHyperdrive import Checkpoint, PoolConfig, PoolInfo


def camel_to_snake(camel_string: str) -> str:
    """Convert camel case string to snake case string.

    Arguments
    ---------
    camel_string: str
        The string to convert.

    Returns
    -------
    str
        The snake case string.
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel_string).lower()


def snake_to_camel(snake_string: str) -> str:
    """Convert snake case string to camel case string.

    Arguments
    ---------
    snake_string: str
        The string to convert.

    Returns
    -------
    str
        The camel case string.
    """
    # First capitalize the letters following the underscores and remove underscores
    camel_string = re.sub(r"_([a-z])", lambda x: x.group(1).upper(), snake_string)
    # Ensure the first character is lowercase to achieve lowerCamelCase
    return camel_string[0].lower() + camel_string[1:] if camel_string else camel_string


def dataclass_to_dict(
    cls: PoolInfo | PoolConfig | Checkpoint,
) -> dict[str, Any]:
    """Convert a state dataclass into a dictionary.

    Arguments
    ---------
    cls: PoolInfo | PoolInfoFP | PoolConfig | PoolConfigFP | Checkpoint | CheckpointFP
        The dataclass to convert

    Returns
    -------
    dict[str, Any]
        The corresponding dictionary
    """
    out_dict = {}
    for key, val in asdict(cls).items():
        match val:
            case FixedPoint():
                out_dict[key] = val.scaled_value
            case FeesFP():
                out_dict[key] = (val.curve, val.flat, val.governance_lp, val.governance_zombie)
            case dict():
                out_dict[key] = (val["curve"], val["flat"], val["governanceLP"], val["governanceZombie"])
            case int():
                out_dict[key] = val
            case str():
                out_dict[key] = val
            case bytes():
                out_dict[key] = val
            case _:
                raise TypeError(f"Unsupported type for {key}={val}, with {type(val)=}.")
    return out_dict

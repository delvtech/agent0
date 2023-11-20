"""Functions for converting Hyperdrive state values."""
from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from fixedpointmath import FixedPoint
from hypertypes import Checkpoint as HtCheckpoint
from hypertypes import PoolConfig as HtPoolConfig
from hypertypes import PoolInfo as HtPoolInfo

from .checkpoint import Checkpoint
from .fees import Fees
from .pool_config import PoolConfig
from .pool_info import PoolInfo


def camel_to_snake(snake_string: str) -> str:
    """Convert camel case string to snake case string."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", snake_string).lower()


def snake_to_camel(snake_string: str) -> str:
    """Convert snake case string to camel case string."""
    # First capitalize the letters following the underscores and remove underscores
    camel_string = re.sub(r"_([a-z])", lambda x: x.group(1).upper(), snake_string)
    # Ensure the first character is lowercase to achieve lowerCamelCase
    return camel_string[0].lower() + camel_string[1:] if camel_string else camel_string


def dataclass_to_dict(
    cls: HtPoolInfo | PoolInfo | HtPoolConfig | PoolConfig | HtCheckpoint | Checkpoint,
) -> dict[str, Any]:
    """Convert a state dataclass into a dictionary."""
    out_dict = {}
    for key, val in asdict(cls).items():
        match val:
            case FixedPoint():
                out_dict[key] = val.scaled_value
            case Fees():
                out_dict[key] = (val.curve, val.flat, val.governance)
            case dict():
                out_dict[key] = (val["curve"], val["flat"], val["governance"])
            case int():
                out_dict[key] = val
            case str():
                out_dict[key] = val
            case bytes():
                out_dict[key] = val
            case _:
                raise TypeError(f"Unsupported type for {key}={val}, with {type(val)=}.")
    return out_dict

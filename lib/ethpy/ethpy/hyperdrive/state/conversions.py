"""Functions for converting Hyperdrive state values."""
from __future__ import annotations

from typing import Any

from ethpy.hyperdrive.addresses import camel_to_snake
from fixedpointmath import FixedPoint

from .checkpoint import Checkpoint
from .fees import Fees
from .pool_config import PoolConfig
from .pool_info import PoolInfo


def dataclass_to_dict(cls: PoolInfo | PoolConfig):
    out_dict = {}
    for key, val in cls.__dict__.items():
        match val:
            case FixedPoint():
                out_dict[key] = str(val.scaled_value)
            case int():
                out_dict[key] = str(val)
            case str():
                out_dict[key] = val
            case Fees():
                out_dict[key] = (val.curve, val.flat, val.governance)
            case _:
                raise TypeError("Unsupported type.")
    return out_dict


def convert_hyperdrive_pool_config_types(pool_config: dict[str, Any]) -> PoolConfig:
    """Convert the pool_config types from what solidity returns to FixedPoint

    Arguments
    ----------
    pool_config : dict[str, Any]
        The hyperdrive pool config.

    Returns
    -------
    PoolConfig
        A dataclass containing the Hyperdrive pool config with modified types.
        This dataclass has the same attributes as the Hyperdrive ABI, with these changes:
          - The attribute names are converted to snake_case.
          - FixedPoint types are used if the type was FixedPoint in the underlying contract.
    """
    # Adjust the pool_config to use snake case here
    # Dict comp is a copy
    pool_config = {camel_to_snake(key): value for key, value in pool_config.items()}
    fixedpoint_keys = ["initial_share_price", "minimum_share_reserves", "minimum_transaction_amount", "time_stretch"]
    for key in pool_config:
        if key in fixedpoint_keys:
            pool_config[key] = FixedPoint(scaled_value=pool_config[key])
    pool_config["fees"] = [FixedPoint(scaled_value=fee) for fee in pool_config["fees"]]
    return PoolConfig(**pool_config)


def convert_hyperdrive_pool_info_types(pool_info: dict[str, Any]) -> PoolInfo:
    """Convert the pool info types from what solidity returns to FixedPoint.

    Arguments
    ---------
    pool_info : dict[str, Any]
        The hyperdrive pool info.

    Returns
    -------
    PoolInfo
        A dataclass containing the Hyperdrive pool info with modified types.
        This dataclass has the same attributes as the Hyperdrive ABI, with these changes:
          - The attribute names are converted to snake_case.
          - FixedPoint types are used if the type was FixedPoint in the underlying contract.
    """
    return PoolInfo(**{camel_to_snake(key): FixedPoint(scaled_value=value) for (key, value) in pool_info.items()})


def convert_hyperdrive_checkpoint_types(checkpoint: dict[str, int]) -> Checkpoint:
    """Convert the checkpoint types from what solidity returns to FixedPoint.

    Arguments
    ---------
    checkpoint : dict[str, int]
        A dictionary containing the checkpoint details.

    Returns
    -------
    Checkpoint
        A dataclass containing the checkpoint share_price and exposure fields converted to FixedPoint.
    """
    return Checkpoint(**{camel_to_snake(key): FixedPoint(scaled_value=value) for key, value in checkpoint.items()})

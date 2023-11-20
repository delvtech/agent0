"""Conversion for hypertypes to fixedpoint"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ethpy.hyperdrive.state.checkpoint import Checkpoint
from ethpy.hyperdrive.state.conversions import camel_to_snake, snake_to_camel
from fixedpointmath import FixedPoint
from hypertypes import Checkpoint as HtCheckpoint
from hypertypes import Fees as HtFees
from hypertypes import PoolConfig as HtPoolConfig
from hypertypes import PoolInfo as HtPoolInfo
from hypertypes.fixedpoint_types import PoolConfigFP, PoolInfoFP


def hypertypes_pool_info_to_fixedpoint(hypertypes_pool_info: HtPoolInfo) -> PoolInfoFP:
    """Convert the Hypertypes PoolInfo attribute types from what solidity returns to FixedPoint.

    Arguments
    ---------
    pool_info : hypertypes.IHyperdriveTypes.PoolInfo
        The hyperdrive pool info.

    Returns
    -------
    ethpy.hyperdrive.state.PoolInfo
        A dataclass containing the Hyperdrive pool info with modified types.
        This dataclass has the same attributes as the Hyperdrive ABI, with these changes:
          - The attribute names are converted to snake_case.
          - FixedPoint types are used if the type was FixedPoint in the underlying contract.
    """
    return PoolInfoFP(
        **{camel_to_snake(key): FixedPoint(scaled_value=value) for (key, value) in asdict(hypertypes_pool_info).items()}
    )


def fixedpoint_pool_info_to_hypertypes(fixedpoint_pool_info: PoolInfoFP) -> HtPoolInfo:
    """Convert the PoolInfo attribute types from FixedPoint to what the Solidity ABI specifies.

    Arguments
    ---------
    pool_info : ethpy.hyperdrive.state.PoolInfo
        The hyperdrive pool info.

    Returns
    -------
    hypertypes.IHyperdriveTypes.PoolInfo
        A dataclass containing the Hyperdrive pool info with derived types from Pypechain.
    """
    return HtPoolInfo(
        **{snake_to_camel(key): value.scaled_value for (key, value) in asdict(fixedpoint_pool_info).items()}
    )


def contract_checkpoint_to_hypertypes(contract_checkpoint: dict[str, Any]) -> HtCheckpoint:
    """Convert the contract call return value into a HyperTypes Checkpoint object."""
    return HtCheckpoint(**contract_checkpoint)


def hypertypes_checkpoint_to_fixedpoint(hypertypes_checkpoint: HtCheckpoint) -> Checkpoint:
    """Convert the HyperTypes Checkpoint attribute types from what Solidity returns to FixedPoint.

    Arguments
    ---------
    checkpoint : hypertypes.IHyperdriveTypes.Checkpoint
        A checkpoint object with sharePrice and exposure fields with derived types from Pypechain.

    Returns
    -------
    ethpy.hyperdrive.state.Checkpoint
        A dataclass containing the checkpoint share_price and exposure fields converted to FixedPoint.
    """
    return Checkpoint(
        **{camel_to_snake(key): FixedPoint(scaled_value=value) for key, value in asdict(hypertypes_checkpoint).items()}
    )


def fixedpoint_checkpoint_to_hypertypes(fixedpoint_checkpoint: Checkpoint) -> HtCheckpoint:
    """Convert the Checkpoint attribute types from FixedPoint to what the Solidity ABI specifies.

    Arguments
    ---------
    checkpoint : ethpy.hyperdrive.state.Checkpoint
        A checkpoint object with FixedPoint values.

    Returns
    -------
    hypertypes.IHyperdriveTypes.Checkpoint
        A dataclass containing the checkpoint share_price and exposure fields converted to integers.
    """
    return HtCheckpoint(
        **{snake_to_camel(key): value.scaled_value for key, value in asdict(fixedpoint_checkpoint).items()}
    )


def contract_pool_info_to_hypertypes(contract_pool_info: dict[str, Any]) -> HtPoolInfo:
    """Convert the contract call return value into a HyperTypes PoolInfo object."""
    return HtPoolInfo(**contract_pool_info)


def contract_pool_config_to_hypertypes(contract_pool_config: dict[str, Any]) -> HtPoolConfig:
    """Convert the contract call returned pool config into a HyperTypes PoolConfig object."""
    return HtPoolConfig(
        baseToken=contract_pool_config["baseToken"],
        linkerFactory=contract_pool_config["linkerFactory"],
        linkerCodeHash=contract_pool_config["linkerCodeHash"],
        initialSharePrice=contract_pool_config["initialSharePrice"],
        minimumShareReserves=contract_pool_config["minimumShareReserves"],
        minimumTransactionAmount=contract_pool_config["minimumTransactionAmount"],
        precisionThreshold=contract_pool_config["precisionThreshold"],
        positionDuration=contract_pool_config["positionDuration"],
        checkpointDuration=contract_pool_config["checkpointDuration"],
        timeStretch=contract_pool_config["timeStretch"],
        governance=contract_pool_config["governance"],
        feeCollector=contract_pool_config["feeCollector"],
        fees=HtFees(
            curve=contract_pool_config["fees"][0],
            flat=contract_pool_config["fees"][1],
            governance=contract_pool_config["fees"][2],
        ),
    )


def hypertypes_pool_config_to_fixedpoint(hypertypes_pool_config: HtPoolConfig) -> PoolConfigFP:
    """Convert the HyperTypes PoolConfig attributes from what Solidity returns to FixedPoint.

    Arguments
    ----------
    pool_config : hypertypes.IHyperdriveTypes.PoolConfig
        The hyperdrive pool config.

    Returns
    -------
    ethpy.hyperdrive.state.PoolConfig
        A dataclass containing the Hyperdrive pool config with modified types.
        This dataclass has the same attributes as the Hyperdrive ABI, with these changes:
          - The attribute names are converted to snake_case.
          - FixedPoint types are used if the type was FixedPoint in the underlying contract.
    """
    dict_pool_config = {camel_to_snake(key): value for key, value in asdict(hypertypes_pool_config).items()}
    fixedpoint_keys = ["initial_share_price", "minimum_share_reserves", "minimum_transaction_amount", "time_stretch"]
    for key in dict_pool_config:
        if key in fixedpoint_keys:
            dict_pool_config[key] = FixedPoint(scaled_value=dict_pool_config[key])
        elif key == "fees":
            dict_pool_config[key] = (
                FixedPoint(scaled_value=dict_pool_config[key]["curve"]),
                FixedPoint(scaled_value=dict_pool_config[key]["flat"]),
                FixedPoint(scaled_value=dict_pool_config[key]["governance"]),
            )
    return PoolConfigFP(**dict_pool_config)


def fixedpoint_pool_config_to_hypertypes(fixedpoint_pool_config: PoolConfigFP) -> HtPoolConfig:
    """Convert the PoolConfig attribute types from FixedPoint to what the Solidity ABI specifies.

    Arguments
    ----------
    pool_config : ethpy.hyperdrive.state.PoolConfig
        The Hyperdrive pool config in FixedPoint format.

    Returns
    -------
    hypertypes.IHyperdriveTypes.PoolConfig
        A dataclass containing the Hyperdrive PoolConfig with types specified by the ABI via Pypechain
    """
    dict_pool_config = {snake_to_camel(key): value for key, value in asdict(fixedpoint_pool_config).items()}
    fixedpoint_keys = ["initialSharePrice", "minimumShareReserves", "minimumTransactionAmount", "timeStretch"]
    for key in dict_pool_config:
        if key in fixedpoint_keys:
            dict_pool_config[key] = dict_pool_config[key].scaled_value
        elif key == "fees":
            dict_pool_config[key] = (
                dict_pool_config[key]["curve"].scaled_value,
                dict_pool_config[key]["flat"].scaled_value,
                dict_pool_config[key]["governance"].scaled_value,
            )
    return HtPoolConfig(
        baseToken=dict_pool_config["baseToken"],
        linkerFactory=dict_pool_config["linkerFactory"],
        linkerCodeHash=dict_pool_config["linkerCodeHash"],
        initialSharePrice=dict_pool_config["initialSharePrice"],
        minimumShareReserves=dict_pool_config["minimumShareReserves"],
        minimumTransactionAmount=dict_pool_config["minimumTransactionAmount"],
        precisionThreshold=dict_pool_config["precisionThreshold"],
        positionDuration=dict_pool_config["positionDuration"],
        checkpointDuration=dict_pool_config["checkpointDuration"],
        timeStretch=dict_pool_config["timeStretch"],
        governance=dict_pool_config["governance"],
        feeCollector=dict_pool_config["feeCollector"],
        fees=HtFees(
            curve=dict_pool_config["fees"][0],
            flat=dict_pool_config["fees"][1],
            governance=dict_pool_config["fees"][2],
        ),
    )

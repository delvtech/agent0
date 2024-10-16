"""Helper functions for interfacing with hyperdrive."""

from __future__ import annotations

from fixedpointmath import FixedPoint
from hyperdrivetypes.fixedpoint_types import CheckpointFP, PoolConfigFP, PoolInfoFP
from hyperdrivetypes.types import IHyperdriveContract
from web3.types import BlockIdentifier, Timestamp


def get_hyperdrive_pool_config(hyperdrive_contract: IHyperdriveContract) -> PoolConfigFP:
    """Get the hyperdrive config from a deployed hyperdrive contract.

    Arguments
    ---------
    hyperdrive_contract: Contract
        The deployed hyperdrive contract instance.

    Returns
    -------
    dict[str, Any]
        The hyperdrive pool config.
    """
    pool_config = hyperdrive_contract.functions.getPoolConfig().call()
    return PoolConfigFP.from_pypechain(pool_config)


def get_hyperdrive_pool_info(hyperdrive_contract: IHyperdriveContract, block_identifier: BlockIdentifier) -> PoolInfoFP:
    """Get the block pool info from the Hyperdrive contract.

    Arguments
    ---------
    hyperdrive_contract: Contract
        The contract to query the pool info from.
    block_identifier: BlockIdentifier
        The block identifier to query from the chain.

    Returns
    -------
    dict[str, Any]
        A dictionary containing the Hyperdrive pool info returned from the smart contract.
    """
    pool_info = hyperdrive_contract.functions.getPoolInfo().call(None, block_identifier)
    return PoolInfoFP.from_pypechain(pool_info)


def get_hyperdrive_checkpoint(
    hyperdrive_contract: IHyperdriveContract, checkpoint_time: Timestamp, block_identifier: BlockIdentifier
) -> CheckpointFP:
    """Get the checkpoint info for the Hyperdrive contract at a given block.

    Arguments
    ---------
    hyperdrive_contract: IHyperdriveContract
        The contract to query the pool info from.
    checkpoint_time: Timestamp
        The block timestamp that indexes the checkpoint to get.
    block_identifier: BlockIdentifier
        The block number to query from the chain.

    Returns
    -------
    CheckpointFP
        The dataclass containing the checkpoint info in fixed point
    """
    checkpoint = hyperdrive_contract.functions.getCheckpoint(checkpoint_time).call(None, block_identifier)
    return CheckpointFP.from_pypechain(checkpoint)


def get_hyperdrive_checkpoint_exposure(
    hyperdrive_contract: IHyperdriveContract, checkpoint_time: Timestamp, block_identifier: BlockIdentifier
) -> FixedPoint:
    """Get the checkpoint exposure for the Hyperdrive contract at a given block.

    Arguments
    ---------
    hyperdrive_contract: IHyperdriveContract
        The contract to query the pool info from.
    checkpoint_time: Timestamp
        The block timestamp that indexes the checkpoint to get.
        This must be an exact checkpoint time for the deployed pool.
    block_identifier: BlockIdentifier
        The block number to query from the chain.

    Returns
    -------
    CheckpointFP
        The dataclass containing the checkpoint info in fixed point.
    """
    exposure = hyperdrive_contract.functions.getCheckpointExposure(checkpoint_time).call(None, block_identifier)
    return FixedPoint(scaled_value=exposure)

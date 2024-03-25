"""Helper function for checking if a new block has ticked on the chain."""

from __future__ import annotations

from eth_typing import BlockNumber
from web3 import Web3
from web3.types import BlockData, RPCEndpoint

from agent0.ethpy.hyperdrive import HyperdriveReadInterface


def check_for_new_block(
    interface: HyperdriveReadInterface, last_block_number: BlockNumber | int
) -> tuple[bool, BlockData]:
    """Returns True if the chain has ticked to a block that is newer than the input block.

    Arguments
    ---------
    interface: HyperdriveReadInterface
        The Hyperdrive API interface object.
    last_block_number: BlockNumber | int
        The last block number to check against.

    Returns
    -------
    tuple[bool, BlockData]
        Tuple with a boolean indicating if the latest block is newer than the last_block input,
        as well as the latest block data.
    """
    latest_block = interface.web3.eth.get_block("latest")
    latest_block_number = latest_block.get("number", None)
    latest_block_timestamp = latest_block.get("timestamp", None)
    if latest_block_number is None or latest_block_timestamp is None:
        raise AssertionError("latest_block_number and latest_block_timestamp can not be None")
    wait_for_new_block = _get_wait_for_new_block(interface.web3)
    new_block = not wait_for_new_block or latest_block_number > last_block_number
    return new_block, latest_block


def _get_wait_for_new_block(web3: Web3) -> bool:
    """Returns if we should wait for a new block before attempting trades again.  For anvil nodes,
       if auto-mining is enabled then every transaction sent to the block is automatically mined so
       we don't need to wait for a new block before submitting trades again.

    .. note::
    This function will soon be deprecated in favor of the IHyperdrive workflow

    Arguments
    ---------
    web3: Web3
        web3.py instantiation.

    Returns
    -------
    bool
        Whether or not to wait for a new block before attempting trades again.
    """
    automine = False
    try:
        response = web3.provider.make_request(method=RPCEndpoint("anvil_getAutomine"), params=[])
        automine = bool(response.get("result", False))
    except Exception:  # pylint: disable=broad-exception-caught
        # do nothing, this will fail for non anvil nodes and we don't care.
        automine = False
    return not automine

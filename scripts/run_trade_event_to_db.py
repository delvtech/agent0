"""Script to maintain trade events on an external db."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import NamedTuple, Sequence

import websockets
from eth_typing import HexStr
from web3 import AsyncWeb3
from web3.providers import WebSocketProvider

from agent0 import Chain, Hyperdrive

# Encoded event hashes
# TODO is there a way to generate these from events?
ENCODED_EVENTS = {
    "AddLiquidity": "0xDCC4A01CEA4510BD52201CEBC8CD2D47D60429B35D68329ABC591A70AA2EFABF",
    "Approval": "0x8C5BE1E5EBEC7D5BD14F71427D1E84F3DD0314C0F7B2291E5B200AC8C7C3B925",
    "ApprovalForAll": "0x17307EAB39AB6107E8899845AD3D59BD9653F200F220920489CA2B5937696C31",
    "CheckpointRewarderUpdated": "0xAE062FB82C932C653CD44617343ECDA1D13E375E0D6F20D969C944FBDA1963D3",
    "CloseLong": "0x3B2C44173852B22D1ECF7784963C2BAB6D4DD07E64ED560F818F144D72EE5267",
    "CloseShort": "0xF87A3DE08B9FE89D655D6731088496CF5F5DA0ABD455E9F7CDC5F0C717F209E5",
    "CollectGovernanceFee": "0x3E5EB8642141E29A1B4E5C28B467396F814C1698E1ADFC3FF327DDB9A6038361",
    "CreateCheckpoint": "0xFF888CF98D2696E95C8C39AA98C9AD55A5378008F7A56614C9353B7137A57AB7",
    "FeeCollectorUpdated": "0xE5693914D19C789BDEE50A362998C0BC8D035A835F9871DA5D51152F0582C34F",
    "GovernanceUpdated": "0x9D3E522E1E47A2F6009739342B9CC7B252A1888154E843AB55EE1C81745795AB",
    "Initialize": "0x4931B9953A65531203C17D9ABE77870A3E49D8B13AF522EC3321C18B5ABB8AF3",
    "OpenLong": "0x7FC9757758F4C7F2EB9F011C4500BEB349847D2F2ACBDD5FFCE3E2F01E79903A",
    "OpenShort": "0xFA6DD2E3E152DBC3FE91196C0B8AA871C26FD7A1D07DE126EC3159FD4EDE2C75",
    "PauseStatusUpdated": "0x7C4D1FE30FDBFDA9E9C4C43E759EF32E4DB5128D4CB58FF3AE9583B89B6242A5",
    "PauserUpdated": "0x902923DCD4814F6CEF7005A70E01D5CF2035AB02D4523EF3B865F1D7BAB885AF",
    "RedeemWithdrawalShares": "0x07210CF9A89FAE8012341FDC131255728787856379269F07C2E41C23B3C09B58",
    "RemoveLiquidity": "0x1C7999DEB68182DE77CE89D32F82D0E13EB042921B2BFA9F35AA1C43F62F261E",
    "Sweep": "0x951F51EE88C8E42633698BBA90D1E53C0954470938036879E691C0232B47E096",
    "SweepCollectorUpdated": "0xC049058B1DF2DD8902739CEB78992DF12FA8369C06C450B3C6787137B452FDD2",
    "TransferSingle": "0xC3D58168C5AE7397731D063D5BBF3D657854427343F4C083240F7AACAA2D0F62",
}

# All hex strings are lowercase in web3
ENCODED_EVENTS = {k: v.lower() for k, v in ENCODED_EVENTS.items()}

REVERSE_ENCODED_EVENTS = {v: k for k, v in ENCODED_EVENTS.items()}


async def _init_event_handler(ws_web3: AsyncWeb3, pools: Sequence[Hyperdrive]) -> dict[str, Hyperdrive]:
    """Initializes the event handler on the registery pools.

    Arguments
    ---------
    ws_web3: AsyncWeb3
        The web3 connection to the websocket provider.
    registry_pools: Sequence[Hyperdrive]
        A list of Hyperdrive pools.

    Returns
    -------
    dict[str, Hyperdrive]
        A dictionary mapping subscription ids to the pools.
    """
    # Define list of events we want to listen to
    filter_events = [
        "AddLiquidity",
        "RemoveLiquidity",
        "OpenLong",
        "CloseLong",
        "OpenShort",
        "CloseShort",
        "RedeemWithdrawalShares",
    ]

    subscription_id_to_pool_lookup = {}
    # Loop through new registery pools
    for pool in pools:
        # Subscribe to hyperdrive events on the new pool
        subscription_id = await ws_web3.eth.subscribe(
            "logs",
            {
                "address": pool.hyperdrive_address,
                # This topics specifies any of the listed events in the first position, and anything after.
                # More information on subscribe topics here:
                # https://docs.alchemy.com/reference/logs
                "topics": [[HexStr(ENCODED_EVENTS[filter_event]) for filter_event in filter_events]],
            },
        )
        subscription_id_to_pool_lookup[subscription_id] = pool

    return subscription_id_to_pool_lookup


async def run_event_handler(
    ws_rpc_uri: str,
    pools: Sequence[Hyperdrive],
):
    """Runs the event handler on the registry pools.

    Arguments
    ---------
    ws_rpc_uri: str
        The websocket rpc uri.
    pools: Sequence[Hyperdrive]
        The list of Hyperdrive pools to run invariant checks on.
    log_to_rollbar: bool
        Whether or not to log to rollbar.
    invariance_ignore_func: Callable[[Exception], bool] | None
        A function defining what invariance errors to ignore.
    rollbar_verbose: bool
        Whether or not to log debugging statements to rollbar.
    """

    # Initialize web socket in context manager.
    # This automatically reconnects if the connection is lost
    async for ws_web3 in AsyncWeb3(WebSocketProvider(ws_rpc_uri)):
        try:
            # Initialize event handler by subscribing to events
            subscription_id_to_pool_lookup = await _init_event_handler(ws_web3, pools)

            # Listen for responses
            async for response in ws_web3.socket.process_subscriptions():
                # Result here is encoded, need to decode if we want to use anything from it.
                # We get the first topic element, which defines the type of event.
                assert "result" in response
                assert "subscription" in response

                subscription_id = response["subscription"]

                encoded_event = response["result"]["topics"][0].to_0x_hex()
                event_str = REVERSE_ENCODED_EVENTS[encoded_event]
                check_block = response["result"]["blockNumber"]

                # Look up the pool based on the subscription id
                pool = subscription_id_to_pool_lookup[subscription_id]

                log_str = (
                    f"{pool.chain.name}: Event {event_str} found on block {check_block} for pool {pool.name}. "
                    "Updating db."
                )
                logging.info(log_str)

                # Sync the events database
                # TODO there may be an issue around expired db sessions if this doesn't run often enough.
                # Solution here is to reconnect the dbsession.
                pool._sync_events()  # pylint: disable=protected-access

        except websockets.ConnectionClosed:
            # If the connection is lost, we iterate the outer loop to attempt a reconnection
            continue


def _look_for_exception_in_handler(handler: asyncio.Task):
    # Query the event handler to catch any exceptions that may have been made.
    if handler.done():
        exception = handler.exception()
        if exception is not None:
            raise exception


async def main(argv: Sequence[str] | None = None) -> None:
    """Check Hyperdrive invariants each block.

    Arguments
    ---------
    argv: Sequence[str]
        A sequence containing the uri to the database server.
    """
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements

    # Placeholder in case we have cli args
    _ = parse_arguments(argv)

    # TODO Abstract this method out for infra scripts
    # Get the rpc uri from env variable
    rpc_uri = os.getenv("RPC_URI", None)
    if rpc_uri is None:
        raise ValueError("RPC_URI is not set")

    ws_rpc_uri = os.getenv("WS_RPC_URI", None)
    if ws_rpc_uri is None:
        raise ValueError("WS_RPC_URI is not set")

    chain = Chain(rpc_uri, Chain.Config(use_existing_postgres=True))

    # Get the registry address from artifacts
    registry_address = os.getenv("REGISTRY_ADDRESS", None)
    if registry_address is None:
        raise ValueError("REGISTRY_ADDRESS is not set")

    logging.info("Checking for new pools...")
    deployed_pools = Hyperdrive.get_hyperdrive_pools_from_registry(chain, registry_address)

    # Initial run, we sync the db
    for pool in deployed_pools:
        pool._sync_events()  # pylint: disable=protected-access

    # Type narrowing, we do the check earlier
    assert ws_rpc_uri is not None
    # Run event handler in background
    event_handler = asyncio.create_task(
        run_event_handler(
            ws_rpc_uri,
            deployed_pools,
        )
    )
    # Sleep forever, looking for exceptions in the event handler
    while True:
        _look_for_exception_in_handler(event_handler)
        await asyncio.sleep(10)


class Args(NamedTuple):
    """Command line arguments for the script."""


# Placeholder for cli args
def namespace_to_args(namespace: argparse.Namespace) -> Args:  # pylint: disable=unused-argument
    """Converts argprase.Namespace to Args.

    Arguments
    ---------
    namespace: argparse.Namespace
        Object for storing arg attributes.

    Returns
    -------
    Args
        Formatted arguments
    """
    return Args()


def parse_arguments(argv: Sequence[str] | None = None) -> Args:
    """Parses input arguments.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.

    Returns
    -------
    Args
        Formatted arguments
    """
    parser = argparse.ArgumentParser(description="Populates a database with trade events on hyperdrive.")

    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv

    return namespace_to_args(parser.parse_args())


if __name__ == "__main__":
    asyncio.run(main())

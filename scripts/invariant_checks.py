"""Script for automatically detecting deployed pools using the registry contract on testnet,
and checking Hyperdrive invariants.

# Invariance checks (these should be True):
- hyperdrive base & eth balances are zero
- the expected total shares equals the hyperdrive balance in the vault contract
- the pool has more than the minimum share reserves
- the system is solvent, i.e. (share reserves - long exposure in shares - min share reserves) > 0
- if a hyperdrive trade happened then a checkpoint was created at the appropriate time

NOTE: this script doesn't check for new registered pools. Rerun the script to run on updated registry.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from functools import partial
from typing import Callable, NamedTuple, Sequence

import websockets
from eth_typing import HexStr
from web3 import AsyncWeb3
from web3.providers import WebSocketProvider

from agent0 import Chain, Hyperdrive
from agent0.ethpy.hyperdrive import get_hyperdrive_registry_from_artifacts
from agent0.hyperfuzz import FuzzAssertionException
from agent0.hyperfuzz.system_fuzz.invariant_checks import run_invariant_checks
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar, log_rollbar_exception, log_rollbar_message
from agent0.utils import async_runner

LOOKBACK_BLOCK_LIMIT = 1000
HANDLER_EXCEPTION_CHECK_TIME = 10

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


def _sepolia_ignore_errors(exc: Exception) -> bool:
    # Ignored fuzz exceptions
    if isinstance(exc, FuzzAssertionException):
        # LP rate invariance check
        if (
            # Only ignore steth pools
            "STETH" in exc.exception_data["pool_name"]
            and len(exc.args) >= 2
            and exc.args[0] == "Continuous Fuzz Bots Invariant Checks"
            and "actual_vault_shares=" in exc.args[1]
            and "is expected to be greater than expected_vault_shares=" in exc.args[1]
        ):
            return True
    return False


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
    log_to_rollbar: bool,
    invariance_ignore_func: Callable[[Exception], bool] | None,
    rollbar_verbose: bool,
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
                    "Running invariant checks."
                )
                logging.info(log_str)
                if rollbar_verbose:
                    log_rollbar_message(log_str, log_level=logging.INFO)

                # Run invariant checks on the pool.
                check_block_data = pool.chain.block_data(block_identifier=check_block)

                run_invariant_checks(
                    check_block_data=check_block_data,
                    interface=pool.interface,
                    log_to_rollbar=log_to_rollbar,
                    rollbar_log_level_threshold=pool.chain.config.rollbar_log_level_threshold,
                    rollbar_log_filter_func=invariance_ignore_func,
                    pool_name=pool.name,
                    log_anvil_state_dump=pool.chain.config.log_anvil_state_dump,
                    # We can't test lp share price here since we don't have access to the pending block.
                    lp_share_price_test=False,
                )

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

    parsed_args = parse_arguments(argv)

    if parsed_args.sepolia:
        invariance_ignore_func = _sepolia_ignore_errors
    else:
        invariance_ignore_func = None

    if parsed_args.infra:
        # TODO Abstract this method out for infra scripts
        # Get the rpc uri from env variable
        rpc_uri = os.getenv("RPC_URI", None)
        if rpc_uri is None:
            raise ValueError("RPC_URI is not set")

        ws_rpc_uri = os.getenv("WS_RPC_URI", None)

        chain = Chain(rpc_uri, Chain.Config(no_postgres=True))

        # Get the registry address from artifacts
        registry_address = os.getenv("REGISTRY_ADDRESS", None)
        if registry_address is None or registry_address == "":
            artifacts_uri = os.getenv("ARTIFACTS_URI", None)
            if artifacts_uri is None:
                raise ValueError("ARTIFACTS_URI must be set if registry address is not set.")
            registry_address = get_hyperdrive_registry_from_artifacts(artifacts_uri)

        check_time = os.getenv("INVARIANCE_CHECK_TIME", None)
        if check_time is None:
            # This sets the default if not passed in
            check_time = parsed_args.check_time
        else:
            # Convert string to python integer
            check_time = int(check_time)

        run_on_event_trigger = os.getenv("INVARIANCE_CHECK_EVENT_TRIGGER", None)
        if run_on_event_trigger is None:
            run_on_event_trigger = parsed_args.event_trigger
        else:
            # Convert string to python boolean
            run_on_event_trigger = run_on_event_trigger.lower() == "true"
    else:
        chain = Chain(parsed_args.rpc_uri, Chain.Config(no_postgres=True))
        registry_address = parsed_args.registry_addr
        ws_rpc_uri = parsed_args.ws_rpc_uri
        check_time = parsed_args.check_time
        run_on_event_trigger = parsed_args.event_trigger

    if run_on_event_trigger:
        if ws_rpc_uri is None:
            raise ValueError("ws_rpc_uri must be set if `event-trigger` is set.")

    rollbar_environment_name = "invariant_checks"
    log_to_rollbar = initialize_rollbar(rollbar_environment_name)

    # Keeps track of the last time we executed an invariant check
    # There are issues with chains where sometimes the block_number
    # returned here isn't a valid block, so we lag behind a block.
    batch_check_start_block = chain.block_number() - 1

    # Check pools on first iteration
    logging.info("Checking for new pools...")
    deployed_pools = Hyperdrive.get_hyperdrive_pools_from_registry(chain, registry_address)

    event_handler: asyncio.Task | None = None
    if run_on_event_trigger:
        # Type narrowing, we do the check earlier
        assert ws_rpc_uri is not None
        # Run event handler in background
        event_handler = asyncio.create_task(
            run_event_handler(
                ws_rpc_uri,
                deployed_pools,
                log_to_rollbar,
                invariance_ignore_func,
                parsed_args.rollbar_verbose,
            )
        )

    # Run periodic invariant checks
    while True:
        # The batch_check_end_block is inclusive
        # (i.e., we do batch_check_end_block + 1 in the loop range)

        # There are issues with chains where sometimes the block_number
        # returned here isn't a valid block, so we lag behind a block.
        batch_check_end_block = chain.block_number() - 1

        # If a block hasn't ticked, we sleep
        if batch_check_start_block > batch_check_end_block:
            # take a nap
            await asyncio.sleep(3)
            continue

        # We have an option to run in 2 modes:
        # 1. When `check_time` < 0, we check every block, including any blocks we may have missed.
        # 2. When `check_time` >= 0, we don't check every block, but instead check every `check_time` seconds.
        #    0 means we don't wait and check as fast as possible, skipping intermediate blocks.
        if check_time >= 0:
            # We don't iterate through all skipped blocks, but instead only check a single block
            batch_check_start_block = batch_check_end_block

        # Look at the number of blocks we need to iterate through
        # If it's past the limit, log an error and catch up by
        # skipping to the latest block
        if (batch_check_end_block - batch_check_start_block) > LOOKBACK_BLOCK_LIMIT:
            error_message = f"{chain.name}: Unable to keep up with invariant checks. Skipping check blocks."
            logging.error(error_message)
            log_rollbar_message(error_message, logging.ERROR)
            batch_check_start_block = batch_check_end_block

        # Loop through all deployed pools and run invariant checks
        print(
            f"Running periodic invariant checks from block {batch_check_start_block} "
            f"to {batch_check_end_block} (inclusive)"
        )
        for check_block in range(batch_check_start_block, batch_check_end_block + 1):
            check_block_data = chain.block_data(block_identifier=check_block)
            partials = [
                partial(
                    run_invariant_checks,
                    check_block_data=check_block_data,
                    interface=hyperdrive_obj.interface,
                    log_to_rollbar=log_to_rollbar,
                    rollbar_log_level_threshold=chain.config.rollbar_log_level_threshold,
                    rollbar_log_filter_func=invariance_ignore_func,
                    pool_name=hyperdrive_obj.name,
                    log_anvil_state_dump=chain.config.log_anvil_state_dump,
                )
                for hyperdrive_obj in deployed_pools
            ]

            log_str = (
                f"{chain.name}: Running periodic invariant checks for block {check_block} "
                f"on pools {[pool.name for pool in deployed_pools]}"
            )
            logging.info(log_str)

            await async_runner(partials)

        batch_check_start_block = batch_check_end_block + 1

        # We check for exceptions in the event handler.
        # This is necessary, as without it, the main thread
        # will happily keep going even if the handler errors out,
        # and won't throw the exception until we await the handler.

        # If set, we sleep for check_time amount.
        if run_on_event_trigger:
            # Type narrowing, we do the check earlier
            assert event_handler is not None
            if check_time > 0:
                # While we're waiting, we want to keep looking for exceptions in the event handler
                num_iterations = check_time // HANDLER_EXCEPTION_CHECK_TIME
                for _ in range(num_iterations):
                    _look_for_exception_in_handler(event_handler)
                    await asyncio.sleep(HANDLER_EXCEPTION_CHECK_TIME)
            else:
                _look_for_exception_in_handler(event_handler)
        else:
            if check_time > 0:
                await asyncio.sleep(check_time)


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    rollbar_verbose: bool
    infra: bool
    registry_addr: str
    rpc_uri: str
    ws_rpc_uri: str
    sepolia: bool
    check_time: int
    event_trigger: bool


def namespace_to_args(namespace: argparse.Namespace) -> Args:
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
    return Args(
        rollbar_verbose=namespace.rollbar_verbose,
        infra=namespace.infra,
        registry_addr=namespace.registry_addr,
        rpc_uri=namespace.rpc_uri,
        ws_rpc_uri=namespace.ws_rpc_uri,
        sepolia=namespace.sepolia,
        check_time=namespace.check_time,
        event_trigger=namespace.event_trigger,
    )


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
    parser = argparse.ArgumentParser(description="Runs a loop to check Hyperdrive invariants at each block.")

    parser.add_argument(
        "--rollbar-verbose",
        default=False,
        action="store_true",
        help="If true, will log info to rollbar for debugging",
    )

    parser.add_argument(
        "--infra",
        default=False,
        action="store_true",
        help="Infra mode, we get registry address from artifacts, and we fund a random account with eth as sender.",
    )

    parser.add_argument(
        "--registry-addr",
        type=str,
        default="",
        help="The address of the registry.",
    )

    parser.add_argument(
        "--rpc-uri",
        type=str,
        default="",
        help="The RPC URI of the chain.",
    )

    parser.add_argument(
        "--ws-rpc-uri",
        type=str,
        default="",
        help="The websocket RPC URI of the chain.",
    )

    parser.add_argument(
        "--sepolia",
        default=False,
        action="store_true",
        help="Running on Sepolia Testnet. If True, will ignore some known errors.",
    )

    parser.add_argument(
        "--check-time",
        type=int,
        default=3600,
        help=(
            "Periodic invariance check, in addition to listening for events (if enabled). "
            "Negative number means to backfill to check every block. "
            "Defaults to once an hour."
        ),
    )

    # The argument below adds both
    # `--event-trigger` (default) and
    # `--no-event-trigger` (turn it off)
    parser.add_argument(
        "--event-trigger",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable or disable invariant checks on event triggers via websockets.",
    )

    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv

    return namespace_to_args(parser.parse_args())


if __name__ == "__main__":
    # Wrap everything in a try catch to log any non-caught critical errors and log to rollbar
    try:
        asyncio.run(main())
    except BaseException as e:  # pylint: disable=broad-except
        # pylint: disable=invalid-name
        _rpc_uri = os.getenv("RPC_URI", None)
        if _rpc_uri is None:
            _log_prefix = "Uncaught Critical Error in Invariant Checks:"
        else:
            _chain_name = _rpc_uri.split("//")[-1].split("/")[0]
            _log_prefix = f"Uncaught Critical Error for {_chain_name} in Invariant Checks:"

        log_rollbar_exception(exception=e, log_level=logging.ERROR, rollbar_log_prefix=_log_prefix)
        raise e

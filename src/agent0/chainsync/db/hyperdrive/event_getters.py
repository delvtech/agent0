"""Event getters specific to database."""

from __future__ import annotations

from typing import Any

from fixedpointmath import FixedPoint
from web3.contract.contract import ContractEvent
from web3.types import BlockIdentifier, EventData

from agent0.ethpy.base import EARLIEST_BLOCK_LOOKUP
from agent0.ethpy.hyperdrive import HyperdriveReadInterface

EVENT_QUERY_PAGE_SIZE = 80000


# Event getters
def _event_data_to_dict(in_val: EventData, numeric_args_as_str: bool) -> dict[str, Any]:
    out = dict(in_val)
    # The args field is also an attribute dict, change to dict
    if numeric_args_as_str:
        # We cast all integer values to strings to keep precision
        # We use `type(v)` instead of `isinstance` to avoid converting booleans to strings
        # pylint: disable=unidiomatic-typecheck
        out["args"] = {k: (str(v) if type(v) is int else v) for k, v in in_val["args"].items()}
    else:
        out["args"] = dict(in_val["args"])

    # Convert transaction hash to string
    out["transactionHash"] = in_val["transactionHash"].hex()
    # Get token id field from args.
    # This field is `assetId` for open/close long/short
    return out


def _convert_event_lido_shares_to_steth(events: list[dict[str, Any]], numeric_args_as_str: bool) -> None:
    # TODO consider not making this conversion and keeping things in lido shares

    # NOTE this edits the list of events in place.
    # Since event arguments can potentially be strings,
    # we cast them back to int to do math, then convert it back to string
    for event in events:
        # We expect all of these fields to exist in the event
        assert "args" in event
        assert "asBase" in event["args"]
        assert "amount" in event["args"]
        assert "vaultSharePrice" in event["args"]
        # If the transaction was made with the vault token, we need to convert
        if not event["args"]["asBase"]:
            event["args"]["amount"] = (
                FixedPoint(scaled_value=int(event["args"]["amount"]))
                * FixedPoint(scaled_value=int(event["args"]["vaultSharePrice"]))
            ).scaled_value
            if numeric_args_as_str:
                event["args"]["amount"] = str(event["args"]["amount"])
            # Shorts also have base_proceeds and base_payment that we need to convert
            if "base_proceeds" in event["args"]:
                event["args"]["base_proceeds"] = (
                    FixedPoint(scaled_value=int(event["args"]["base_proceeds"]))
                    * FixedPoint(scaled_value=int(event["args"]["vaultSharePrice"]))
                ).scaled_value
                if numeric_args_as_str:
                    event["args"]["base_proceeds"] = str(event["args"]["base_proceeds"])
            if "base_payment" in event["args"]:
                event["args"]["base_payment"] = (
                    FixedPoint(scaled_value=int(event["args"]["base_payment"]))
                    * FixedPoint(scaled_value=int(event["args"]["vaultSharePrice"]))
                ).scaled_value
                if numeric_args_as_str:
                    event["args"]["base_payment"] = str(event["args"]["base_payment"])


def get_event_logs_for_db(
    hyperdrive_interface: HyperdriveReadInterface,
    event_class: ContractEvent,
    trade_base_unit_conversion: bool,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
    numeric_args_as_str: bool = True,
) -> list[dict[str, Any]]:
    """Get event logs based on the event_class, making necessary conversions for the database.

    Arguments
    ---------
    hyperdrive_interface: HyperdriveReadInterface
        The hyperdrive interface to use.
    event_class: type[ContractEvent]
        The event class to get logs for.
    trade_base_unit_conversion: bool
        Whether to convert trade base units from steth "shares" to steth.
    from_block: BlockIdentifier | None, optional
        The block to start getting events from. Defaults to "earliest", with some exceptions for specific chains.
    argument_filters: dict[str, Any] | None, optional
        A dictionary of filters to apply to the arguments of events. Defaults to None.
    numeric_args_as_str: bool, optional
        Whether to convert numeric event arguments to strings for keeping precision.
        Defaults to True.

    Returns
    -------
    list[dict[str, Any]]
        A list of emitted events.
    """
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments

    # We look up the chain id, and define the `from_block` based on which chain it is as the default.
    if from_block is None:
        chain_id = hyperdrive_interface.web3.eth.chain_id
        # If not in lookup, we default to `earliest`
        from_block = EARLIEST_BLOCK_LOOKUP.get(chain_id, "earliest")

    current_block = hyperdrive_interface.web3.eth.block_number
    # If the from block specified is a specific block number, make sure it's not a pending block
    # If it's past the latest block, no events to return
    if isinstance(from_block, int) and from_block > current_block:
        return []

    # split up from_block if too large
    out_events = []
    for _from_block in range(int(from_block), current_block + 1, EVENT_QUERY_PAGE_SIZE):
        # -1 because to block in get_logs is inclusive
        _to_block = _from_block + EVENT_QUERY_PAGE_SIZE - 1
        if _to_block >= current_block:
            _to_block = "latest"

        out_events.extend(
            _event_data_to_dict(e, numeric_args_as_str)
            for e in event_class.get_logs(from_block=_from_block, to_block=_to_block, argument_filters=argument_filters)
        )

    # Convert output event data from lido shares to steth
    if trade_base_unit_conversion and hyperdrive_interface.hyperdrive_kind == hyperdrive_interface.HyperdriveKind.STETH:
        _convert_event_lido_shares_to_steth(out_events, numeric_args_as_str)

    return out_events

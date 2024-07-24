"""Hyperdrive interface functions that get event logs from the chain."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fixedpointmath import FixedPoint
from web3.types import BlockIdentifier, EventData

if TYPE_CHECKING:
    from .read_interface import HyperdriveReadInterface


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


# TODO it may be useful to return a list of our defined event types.
# For now, we directly return the result of the web3 call.
# TODO we can split up argument filters as individual arguments
# instead of a dict since we know event arguments here.
def _get_checkpoint_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None,
    argument_filters: dict[str, Any] | None,
    numeric_args_as_str: bool,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    return [
        _event_data_to_dict(e, numeric_args_as_str)
        for e in hyperdrive_interface.hyperdrive_contract.events.CreateCheckpoint.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]


def _get_transfer_single_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None,
    argument_filters: dict[str, Any] | None,
    numeric_args_as_str: bool,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    return [
        _event_data_to_dict(e, numeric_args_as_str)
        for e in hyperdrive_interface.hyperdrive_contract.events.TransferSingle.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]


def _get_initialize_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None,
    argument_filters: dict[str, Any] | None,
    numeric_args_as_str: bool,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e, numeric_args_as_str)
        for e in hyperdrive_interface.hyperdrive_contract.events.Initialize.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    # Convert output event data from lido shares to steth
    if hyperdrive_interface.hyperdrive_kind == hyperdrive_interface.HyperdriveKind.STETH:
        _convert_event_lido_shares_to_steth(out_events, numeric_args_as_str)
    return out_events


# TODO we can add a helper function to get all trading events here
def _get_open_long_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None,
    argument_filters: dict[str, Any] | None,
    numeric_args_as_str: bool,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e, numeric_args_as_str)
        for e in hyperdrive_interface.hyperdrive_contract.events.OpenLong.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    if hyperdrive_interface.hyperdrive_kind == hyperdrive_interface.HyperdriveKind.STETH:
        _convert_event_lido_shares_to_steth(out_events, numeric_args_as_str)

    return out_events


def _get_close_long_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None,
    argument_filters: dict[str, Any] | None,
    numeric_args_as_str: bool,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e, numeric_args_as_str)
        for e in hyperdrive_interface.hyperdrive_contract.events.CloseLong.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    if hyperdrive_interface.hyperdrive_kind == hyperdrive_interface.HyperdriveKind.STETH:
        _convert_event_lido_shares_to_steth(out_events, numeric_args_as_str)
    return out_events


def _get_open_short_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None,
    argument_filters: dict[str, Any] | None,
    numeric_args_as_str: bool,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e, numeric_args_as_str)
        for e in hyperdrive_interface.hyperdrive_contract.events.OpenShort.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    if hyperdrive_interface.hyperdrive_kind == hyperdrive_interface.HyperdriveKind.STETH:
        _convert_event_lido_shares_to_steth(out_events, numeric_args_as_str)
    return out_events


def _get_close_short_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None,
    argument_filters: dict[str, Any] | None,
    numeric_args_as_str: bool,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e, numeric_args_as_str)
        for e in hyperdrive_interface.hyperdrive_contract.events.CloseShort.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    if hyperdrive_interface.hyperdrive_kind == hyperdrive_interface.HyperdriveKind.STETH:
        _convert_event_lido_shares_to_steth(out_events, numeric_args_as_str)
    return out_events


def _get_add_liquidity_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None,
    argument_filters: dict[str, Any] | None,
    numeric_args_as_str: bool,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e, numeric_args_as_str)
        for e in hyperdrive_interface.hyperdrive_contract.events.AddLiquidity.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    if hyperdrive_interface.hyperdrive_kind == hyperdrive_interface.HyperdriveKind.STETH:
        _convert_event_lido_shares_to_steth(out_events, numeric_args_as_str)
    return out_events


def _get_remove_liquidity_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None,
    argument_filters: dict[str, Any] | None,
    numeric_args_as_str: bool,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e, numeric_args_as_str)
        for e in hyperdrive_interface.hyperdrive_contract.events.RemoveLiquidity.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    if hyperdrive_interface.hyperdrive_kind == hyperdrive_interface.HyperdriveKind.STETH:
        _convert_event_lido_shares_to_steth(out_events, numeric_args_as_str)
    return out_events


def _get_redeem_withdrawal_shares_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None,
    argument_filters: dict[str, Any] | None,
    numeric_args_as_str: bool,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e, numeric_args_as_str)
        for e in hyperdrive_interface.hyperdrive_contract.events.RedeemWithdrawalShares.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    if hyperdrive_interface.hyperdrive_kind == hyperdrive_interface.HyperdriveKind.STETH:
        _convert_event_lido_shares_to_steth(out_events, numeric_args_as_str)
    return out_events

"""Hyperdrive interface functions that get event logs from the chain."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fixedpointmath import FixedPoint
from web3.types import BlockIdentifier, EventData

if TYPE_CHECKING:
    from .read_interface import HyperdriveReadInterface


def _event_data_to_dict(in_val: EventData) -> dict[str, Any]:
    out = dict(in_val)
    # The args field is also an attribute dict, change to dict
    out["args"] = dict(in_val["args"])

    # Convert transaction hash to string
    out["transactionHash"] = in_val["transactionHash"].hex()
    # Get token id field from args.
    # This field is `assetId` for open/close long/short
    return out


def _convert_event_lido_shares_to_steth(events: list[dict[str, Any]]) -> None:
    # NOTE this edits the list of events in place.
    for event in events:
        # We expect all of these fields to exist in the event
        assert "args" in event
        assert "asBase" in event["args"]
        assert "amount" in event["args"]
        assert "vaultSharePrice" in event["args"]
        # If the transaction was made with the vault token, we need to convert
        if not event["args"]["asBase"]:
            event["args"]["amount"] = (
                FixedPoint(scaled_value=event["args"]["amount"])
                * FixedPoint(scaled_value=event["args"]["vaultSharePrice"])
            ).scaled_value
            # Shorts also have base_proceeds and base_payment that we need to convert
            if "base_proceeds" in event["args"]:
                event["args"]["base_proceeds"] = (
                    FixedPoint(scaled_value=event["args"]["base_proceeds"])
                    * FixedPoint(scaled_value=event["args"]["vaultSharePrice"])
                ).scaled_value
            if "base_payment" in event["args"]:
                event["args"]["base_payment"] = (
                    FixedPoint(scaled_value=event["args"]["base_payment"])
                    * FixedPoint(scaled_value=event["args"]["vaultSharePrice"])
                ).scaled_value


# TODO it may be useful to return a list of our defined event types.
# For now, we directly return the result of the web3 call.
# TODO we can split up argument filters as individual arguments
# instead of a dict since we know event arguments here.
def _get_checkpoint_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    return [
        _event_data_to_dict(e)
        for e in hyperdrive_interface.hyperdrive_contract.events.CreateCheckpoint.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]


def _get_transfer_single_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    return [
        _event_data_to_dict(e)
        for e in hyperdrive_interface.hyperdrive_contract.events.TransferSingle.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]


def _get_initialize_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e)
        for e in hyperdrive_interface.hyperdrive_contract.events.Initialize.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    # Convert output event data from lido shares to steth
    if hyperdrive_interface.vault_is_steth:
        _convert_event_lido_shares_to_steth(out_events)
    return out_events


# TODO we can add a helper function to get all trading events here
def _get_open_long_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e)
        for e in hyperdrive_interface.hyperdrive_contract.events.OpenLong.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    if hyperdrive_interface.vault_is_steth:
        _convert_event_lido_shares_to_steth(out_events)

    return out_events


def _get_close_long_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e)
        for e in hyperdrive_interface.hyperdrive_contract.events.CloseLong.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    if hyperdrive_interface.vault_is_steth:
        _convert_event_lido_shares_to_steth(out_events)
    return out_events


def _get_open_short_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e)
        for e in hyperdrive_interface.hyperdrive_contract.events.OpenShort.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    if hyperdrive_interface.vault_is_steth:
        _convert_event_lido_shares_to_steth(out_events)
    return out_events


def _get_close_short_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e)
        for e in hyperdrive_interface.hyperdrive_contract.events.CloseShort.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    if hyperdrive_interface.vault_is_steth:
        _convert_event_lido_shares_to_steth(out_events)
    return out_events


def _get_add_liquidity_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e)
        for e in hyperdrive_interface.hyperdrive_contract.events.AddLiquidity.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    if hyperdrive_interface.vault_is_steth:
        _convert_event_lido_shares_to_steth(out_events)
    return out_events


def _get_remove_liquidity_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e)
        for e in hyperdrive_interface.hyperdrive_contract.events.RemoveLiquidity.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    if hyperdrive_interface.vault_is_steth:
        _convert_event_lido_shares_to_steth(out_events)
    return out_events


def _get_redeem_withdrawal_shares_events(
    hyperdrive_interface: HyperdriveReadInterface,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """See API for documentation."""
    out_events = [
        _event_data_to_dict(e)
        for e in hyperdrive_interface.hyperdrive_contract.events.RedeemWithdrawalShares.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    ]
    if hyperdrive_interface.vault_is_steth:
        _convert_event_lido_shares_to_steth(out_events)
    return out_events

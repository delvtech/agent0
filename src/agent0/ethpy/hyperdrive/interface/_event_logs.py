"""Hyperdrive interface functions that get event logs from the chain."""

from __future__ import annotations

from typing import Any

from web3.types import BlockIdentifier, EventData

from agent0.hypertypes import IHyperdriveContract


# TODO it may be useful to return a list of our defined event types.
# For now, we directly return the result of the web3 call.
# TODO we can split up argument filters as individual arguments
# instead of a dict since we know event arguments here.
def _get_checkpoint_events(
    hyperdrive_contract: IHyperdriveContract,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[EventData]:
    """See API for documentation."""
    return list(
        hyperdrive_contract.events.CreateCheckpoint.get_logs(fromBlock=from_block, argument_filters=argument_filters)
    )


def _get_transfer_single_events(
    hyperdrive_contract: IHyperdriveContract,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[EventData]:
    """See API for documentation."""
    return list(
        hyperdrive_contract.events.TransferSingle.get_logs(fromBlock=from_block, argument_filters=argument_filters)
    )


def _get_initialize_events(
    hyperdrive_contract: IHyperdriveContract,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[EventData]:
    """See API for documentation."""
    return list(hyperdrive_contract.events.Initialize.get_logs(fromBlock=from_block, argument_filters=argument_filters))


# TODO we can add a helper function to get all trading events here
def _get_open_long_events(
    hyperdrive_contract: IHyperdriveContract,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[EventData]:
    """See API for documentation."""
    return list(hyperdrive_contract.events.OpenLong.get_logs(fromBlock=from_block, argument_filters=argument_filters))


def _get_close_long_events(
    hyperdrive_contract: IHyperdriveContract,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[EventData]:
    """See API for documentation."""
    return list(hyperdrive_contract.events.CloseLong.get_logs(fromBlock=from_block, argument_filters=argument_filters))


def _get_open_short_events(
    hyperdrive_contract: IHyperdriveContract,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[EventData]:
    """See API for documentation."""
    return list(hyperdrive_contract.events.OpenShort.get_logs(fromBlock=from_block, argument_filters=argument_filters))


def _get_close_short_events(
    hyperdrive_contract: IHyperdriveContract,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[EventData]:
    """See API for documentation."""
    return list(hyperdrive_contract.events.CloseShort.get_logs(fromBlock=from_block, argument_filters=argument_filters))


def _get_add_liquidity_events(
    hyperdrive_contract: IHyperdriveContract,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[EventData]:
    """See API for documentation."""
    return list(
        hyperdrive_contract.events.AddLiquidity.get_logs(fromBlock=from_block, argument_filters=argument_filters)
    )


def _get_remove_liquidity_events(
    hyperdrive_contract: IHyperdriveContract,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[EventData]:
    """See API for documentation."""
    return list(
        hyperdrive_contract.events.RemoveLiquidity.get_logs(fromBlock=from_block, argument_filters=argument_filters)
    )


def _get_redeem_withdrawal_shares_events(
    hyperdrive_contract: IHyperdriveContract,
    from_block: BlockIdentifier | None = None,
    argument_filters: dict[str, Any] | None = None,
) -> list[EventData]:
    """See API for documentation."""
    return list(
        hyperdrive_contract.events.RedeemWithdrawalShares.get_logs(
            fromBlock=from_block, argument_filters=argument_filters
        )
    )

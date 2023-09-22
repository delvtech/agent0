# pylint: disable=invalid-name
"""Dataclasses for all structs in the ERC20Mintable contract."""

from web3.types import ABIEvent, ABIEventParams

from dataclasses import dataclass

Approval = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="value", type="uint256"),
    ],
    name="Approval",
    type="event",
)

Transfer = ABIEvent(
    anonymous=False,
    inputs=[
        ABIEventParams(indexed=False, name="value", type="uint256"),
    ],
    name="Transfer",
    type="event",
)

# pylint: disable=invalid-name
"""Dataclasses for all structs in the ERC20Mintable contract."""
from __future__ import annotations

from dataclasses import dataclass

from web3.types import ABIEvent, ABIEventParams

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

"""Dataclasses for all structs in the ERC20Mintable contract."""
# super() call methods are generic, while our version adds values & types
# pylint: disable=arguments-differ
# contracts have PascalCase names
# pylint: disable=invalid-name
# contracts control how many attributes and arguments we have in generated code
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
# unable to determine which imports will be used in the generated code
# pylint: disable=unused-import
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

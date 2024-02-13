"""The trade result object after executing trades in agent0"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from ethpy.hyperdrive import ReceiptBreakdown

if TYPE_CHECKING:
    from agent0.base import Trade


class TradeStatus(Enum):
    r"""A type of token"""

    SUCCESS = "success"
    FAIL = "fail"


@dataclass(kw_only=True)
class TradeResult:
    """A data object that stores all information of an executed trade

    Attributes
    ----------
    status: TradeStatus
        The status of the trade
    tx_receipt: ReceiptBreakdown
        The transaction receipt for the trade
    contract_call: dict[str, Any]
        Data on the contract call that was made
    block_number: int
        The block number of the trade
    block_timestamp: int
        The block timestamp of the trade
    exception: Exception | None
        The exception that was thrown
    orig_exception: Exception | list[Exception] | BaseException | None
        The original exception that was thrown
    additional_info: dict[str, Any]
        Additional information used for crash reporting
    raw_transaction: dict[str, Any]
        The raw transaction sent to solidity
    anvil_state: str | None
        The anvil state dump when the exception occurred
    """

    # pylint: disable=too-many-instance-attributes

    status: TradeStatus
    # TODO add base trade object here
    tx_receipt: ReceiptBreakdown | None = None
    contract_call: dict[str, Any] | None = None
    # Optional fields for crash reporting
    # These fields are typically set as human readable versions
    block_number: int | None = None
    block_timestamp: int | None = None
    exception: Exception | None = None
    orig_exception: Exception | list[Exception] | BaseException | None = None
    additional_info: dict[str, Any] | None = None
    raw_transaction: dict[str, Any] | None = None
    anvil_state: str | None = None

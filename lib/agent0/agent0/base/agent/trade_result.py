"""The trade result object after executing trades in agent0"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from ethpy.hyperdrive import ReceiptBreakdown

if TYPE_CHECKING:
    from agent0.base import BaseMarketAction, Trade


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
    trade_object: Trade[HyperdriveMarketAction]
        The trade object that was executed
    """

    status: TradeStatus
    trade_object: Trade[BaseMarketAction] | None = None
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

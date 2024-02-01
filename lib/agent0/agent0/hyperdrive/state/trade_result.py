"""The resulting deltas of a market action"""

# Please enter the commit message for your changes. Lines starting
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from ethpy.hyperdrive import ReceiptBreakdown

if TYPE_CHECKING:
    from agent0.base import Trade
    from agent0.hyperdrive import HyperdriveMarketAction
    from agent0.hyperdrive.agents import HyperdriveAgent


class TradeStatus(Enum):
    r"""A type of token"""

    SUCCESS = "success"
    FAIL = "fail"


# TODO some of these are generic, move to base directory
@dataclass
# Dataclass has lots of attributes
# pylint: disable=too-many-instance-attributes
class TradeResult:
    """A data object that stores all information of an executed trade

    Attributes
    ----------
    status: TradeStatus
        The status of the trade
    agent: HyperdriveAgent
        The agent that was executing the trade
    exception: Exception | None
        The exception that was thrown
    pool_config: dict[str, Any]
        The configuration of the pool
    pool_info: dict[str, Any]
        The information of the pool
    checkpoint_info: dict[str, Any]
        The information of the latest checkpoint
    additional_info: dict[str, Any]
        Additional information used for crash reporting
    anvil_state: str | None
        The anvil state dump when the exception occurred
    """

    status: TradeStatus
    agent: HyperdriveAgent | None = None
    trade_object: Trade[HyperdriveMarketAction] | None = None
    tx_receipt: ReceiptBreakdown | None = None
    contract_call: dict[str, Any] | None = None
    # Flags for known errors
    is_slippage: bool = False
    is_invalid_balance: bool = False
    is_min_txn_amount: bool = False
    # Optional fields for crash reporting
    # These fields are typically set as human readable versions
    block_number: int | None = None
    block_timestamp: int | None = None
    exception: Exception | None = None
    orig_exception: Exception | list[Exception] | BaseException | None = None
    pool_config: dict[str, Any] | None = None
    pool_info: dict[str, Any] | None = None
    checkpoint_info: dict[str, Any] | None = None
    contract_addresses: dict[str, Any] | None = None
    additional_info: dict[str, Any] | None = None
    # Machine readable states
    raw_transaction: dict[str, Any] | None = None
    raw_pool_config: dict[str, Any] | None = None
    raw_pool_info: dict[str, Any] | None = None
    raw_checkpoint: dict[str, Any] | None = None
    anvil_state: str | None = None

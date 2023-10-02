"""The resulting deltas of a market action"""
# Please enter the commit message for your changes. Lines starting
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from agent0.hyperdrive.agents import HyperdriveAgent
    from agent0.hyperdrive.state import HyperdriveMarketAction
    from elfpy import types


class TradeStatus(Enum):
    r"""A type of token"""

    SUCCESS = "success"
    FAIL = "fail"


# TODO some of these are generic, move to base directory
class TradeResult(NamedTuple):
    """A data object that stores all information of an executed trade

    Attributes
    ----------

    exception: Exception | None
        The exception that was thrown
    agent: HyperdriveAgent
        The agent that was executing the trade
    trade: types.Trade[HyperdriveMarketAction]
        The trade that caused the crash
    """

    status: TradeStatus
    agent: HyperdriveAgent
    trade_object: types.Trade[HyperdriveMarketAction]
    # Optional fields for crash reporting
    exception: Exception | None | None = None
    pool_config: dict[str, Any] | None = None
    pool_info: dict[str, Any] | None = None

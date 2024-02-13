"""The trade result object after executing trades in agent0"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from agent0.base.agent import TradeResult

if TYPE_CHECKING:
    from agent0.base import Trade

    from .hyperdrive_actions import HyperdriveMarketAction
    from .hyperdrive_agent import HyperdriveAgent


@dataclass(kw_only=True)
# Dataclass has lots of attributes
# pylint: disable=too-many-instance-attributes
class HyperdriveTradeResult(TradeResult):
    """A data object that stores all information of an executed trade

    Attributes
    ----------
    agent: HyperdriveAgent
        The agent that was executing the trade
    trade_object: Trade[HyperdriveMarketAction]
        The trade object that was executed
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

    agent: HyperdriveAgent | None = None
    # Narrowing trade object type for Hyperdrive
    trade_object: Trade[HyperdriveMarketAction] | None = None
    # Flags for known errors
    is_slippage: bool = False
    is_invalid_balance: bool = False
    is_min_txn_amount: bool = False
    # Optional fields for crash reporting
    pool_config: dict[str, Any] | None = None
    pool_info: dict[str, Any] | None = None
    checkpoint_info: dict[str, Any] | None = None
    contract_addresses: dict[str, Any] | None = None
    # Machine readable states
    raw_pool_config: dict[str, Any] | None = None
    raw_pool_info: dict[str, Any] | None = None
    raw_checkpoint: dict[str, Any] | None = None

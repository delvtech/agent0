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
    trade_object: Trade[HyperdriveMarketAction]
        The trade object that was executed
    agent: HyperdriveAgent
        The agent that was executing the trade
    is_slippage: bool
        Whether the trade resulted in a slippage
    is_invalid_balance: bool
        Whether the trade resulted in an invalid balance
    is_min_txn_amount: bool
        Whether the trade resulted in a minimum transaction amount
    pool_config: dict[str, Any]
        The configuration of the pool
    pool_info: dict[str, Any]
        The information of the pool
    checkpoint_info: dict[str, Any]
        The information of the latest checkpoint
    contract_addresses: dict[str, Any]
        The addresses of the hyperdrive contracts
    raw_pool_config: dict[str, Any]
        The pool configuration directly from solidity
    raw_pool_info: dict[str, Any]
        The pool information directly from solidity
    raw_checkpoint: dict[str, Any]
        The checkpoint information directly from solidity
    """

    trade_object: Trade[HyperdriveMarketAction] | None = None
    agent: HyperdriveAgent | None = None
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

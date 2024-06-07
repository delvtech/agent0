"""The resulting deltas of a market action"""

# Please enter the commit message for your changes. Lines starting
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount

    from agent0.core.base import Trade
    from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
    from agent0.ethpy.hyperdrive import ReceiptBreakdown

    from .hyperdrive_actions import HyperdriveMarketAction
    from .hyperdrive_wallet import HyperdriveWallet


# TODO some of these are generic, move to base directory
@dataclass
# Dataclass has lots of attributes
# pylint: disable=too-many-instance-attributes
class TradeResult:
    """A data object that stores all information of an executed trade."""

    trade_successful: bool
    """The status of the trade."""
    account: LocalAccount | None = None
    """The agent that was executing the trade."""
    wallet: HyperdriveWallet | None = None
    """The wallet of the agent that was executing the trade."""
    policy: HyperdriveBasePolicy | None = None
    """The policy that was executing the trade."""
    trade_object: Trade[HyperdriveMarketAction] | None = None
    """The trade object for the trade."""
    tx_receipt: ReceiptBreakdown | None = None
    """The transaction receipt of the trade."""
    contract_call: dict[str, Any] | None = None
    """A dictionary detailing the underlying contract call."""

    # Flags for known errors
    is_slippage: bool = False
    """If the trade failed due to slippage."""
    is_invalid_balance: bool = False
    """If the trade failed due to invalid balance."""
    is_insufficient_allowance: bool = False
    """If the trade failed due to insufficient approval."""
    is_min_txn_amount: bool = False
    """If the trade failed due to minimum transaction amount."""

    # Optional fields for crash reporting
    # These fields are typically set as human readable versions
    block_number: int | None = None
    """The block number of the transaction."""
    block_timestamp: int | None = None
    """The block timestamp of the transaction."""
    exception: Exception | None = None
    """The exception that was thrown."""
    orig_exception: Exception | list[Exception] | BaseException | None = None
    """If exception was wrapped, the original exception that was thrown."""
    pool_config: dict[str, Any] | None = None
    """The pool config information."""
    pool_info: dict[str, Any] | None = None
    """The pool info information."""
    checkpoint_info: dict[str, Any] | None = None
    """The checkpoint info information."""
    contract_addresses: dict[str, Any] | None = None
    """The contract addresses."""
    additional_info: dict[str, Any] | None = None
    """Additional information used for crash reporting."""
    # Machine readable states
    raw_transaction: dict[str, Any] | None = None
    """The raw transaction sent to the chain."""
    raw_pool_config: dict[str, Any] | None = None
    """The raw pool config."""
    raw_pool_info: dict[str, Any] | None = None
    """The raw pool info."""
    raw_checkpoint: dict[str, Any] | None = None
    """The raw checkpoint info."""
    anvil_state: str | None = None
    """The dumped anvil state."""

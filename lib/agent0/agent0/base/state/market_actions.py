"""A dataclass for storing possible action types and wallets in any given market."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from agent0.base import freezable

from .eth_wallet import EthWallet


@freezable(frozen=False, no_new_attribs=True)
@dataclass
class BaseMarketAction:
    r"""Market action specification"""

    action_type: Enum  # these two variables are required to be set by the strategy
    wallet: EthWallet  # the agent's wallet

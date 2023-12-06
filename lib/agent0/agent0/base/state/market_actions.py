"""A dataclass for storing possible action types and wallets in any given market."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

from agent0.base import freezable

from .eth_wallet import EthWallet

T = TypeVar("T", bound=Enum)
W = TypeVar("W", bound=EthWallet)


@freezable(frozen=False, no_new_attribs=True)
@dataclass
class BaseMarketAction(Generic[T, W]):
    r"""Market action specification"""

    action_type: T  # these two variables are required to be set by the strategy
    wallet: W  # the agent's wallet

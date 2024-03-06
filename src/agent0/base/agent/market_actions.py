"""A dataclass for storing possible action types and wallets in any given market."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

T = TypeVar("T", bound=Enum)


@dataclass
class BaseMarketAction(Generic[T]):
    r"""Market action specification"""

    action_type: T  # these two variables are required to be set by the strategy

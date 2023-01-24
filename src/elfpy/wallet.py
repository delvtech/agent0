"""
Implements abstract classes that control user behavior
"""

from __future__ import annotations  # types will be strings by default in 3.11
from typing import TYPE_CHECKING, Dict
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from typing import Any


@dataclass
class Long:
    """An open long position.

    Arguments
    ---------
    balance : float
        The amount of bonds that the position is long.
    """

    balance: float

    def __str__(self):
        return f"Long(balance: {self.balance})"


@dataclass
class Short:
    """An open short position.

    Arguments
    ---------
    balance : float
        The amount of bonds that the position is short.
    margin : float
        The amount of margin the short position has.
    """

    balance: float
    margin: float

    def __str__(self):
        return f"Short(balance: {self.balance}, margin: {self.margin})"


@dataclass(frozen=False)
class Wallet:
    """
    Stores what's in the agent's wallet

    Arguments
    ---------
    address : int
        The trader's address.
    base : float
        The base assets that held by the trader.
    lp_tokens : float
        The LP tokens held by the trader.
    longs : Dict[float, Long]
        The long positions held by the trader.
    shorts : Dict[float, Short]
        The short positions held by the trader.
    fees_paid : float
        The fees paid by the wallet.
    """

    # pylint: disable=too-many-instance-attributes
    # dataclasses can have many attributes

    # agent identifier
    address: int

    # fungible
    base: float = 0
    lp_tokens: float = 0

    # non-fungible (identified by mint_time, stored as dict)
    longs: Dict[float, Long] = field(default_factory=dict)
    shorts: Dict[float, Short] = field(default_factory=dict)

    # TODO: This isn't used for short trades
    fees_paid: float = 0

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __str__(self) -> str:
        output_string = ""
        for key, value in vars(self).items():
            if value:  #  check if object exists
                if value != 0:
                    output_string += f" {key}: "
                    if isinstance(value, float):
                        output_string += f"{value}"
                    elif isinstance(value, list):
                        output_string += "[" + ", ".join(list(value)) + "]"
                    elif isinstance(value, dict):
                        output_string += "{" + ", ".join([f"{k}: {v}" for k, v in value.items()]) + "}"
                    else:
                        output_string += f"{value}"
        return output_string

    @property
    def state(self) -> dict:
        """The wallet's current state of public variables
        TODO: Set this up as a dataclass instead of a dict, which then needs to be converted when adding to the state
        """
        return {
            f"agent_{self.address}_base": self.base,
            f"agent_{self.address}_lp_tokens": self.lp_tokens,
            f"agent_{self.address}_total_longs": sum((long.balance for long in self.longs.values())),
            f"agent_{self.address}_total_shorts": sum((short.balance for short in self.shorts.values())),
        }

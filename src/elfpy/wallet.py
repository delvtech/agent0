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
    r"""An open long position.

    Parameters
    ----------
    balance : float
        The amount of bonds that the position is long.
    """

    balance: float

    def __str__(self):
        return f"Long(balance: {self.balance})"


@dataclass
class Short:
    r"""An open short position.

    Parameters
    ----------
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
    r"""Stores what is in the agent's wallet

    Parameters
    ----------
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
        long_string = "\tlongs={\n"
        for key, value in self.longs.items():
            long_string += f"\t\t{key}: {value}\n"
        long_string += "\t}"
        short_string = "\tshorts={\n"
        for key, value in self.shorts.items():
            short_string += f"\t\t{key}: {value}\n"
        short_string += "\t}"
        output_string = (
            "Wallet(\n"
            f"\t{self.address=},\n"
            f"\t{self.base=},\n"
            f"\t{self.lp_tokens=},\n"
            f"\t{self.lp_tokens=},\n"
            f"{long_string},\n"
            f"{short_string},\n"
            ")"
        )
        return output_string

    @property
    def state(self) -> dict:
        r"""The wallet's current state of public variables

        .. todo:: TODO: Set this up as a dataclass instead of a dict & convert when adding to the state
        """
        return {
            f"agent_{self.address}_base": self.base,
            f"agent_{self.address}_lp_tokens": self.lp_tokens,
            f"agent_{self.address}_total_longs": sum((long.balance for long in self.longs.values())),
            f"agent_{self.address}_total_shorts": sum((short.balance for short in self.shorts.values())),
            f"agent_{self.address}_longs": self.longs,
            f"agent_{self.address}_shorts": self.shorts,
        }

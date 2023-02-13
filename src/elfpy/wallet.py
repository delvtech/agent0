"""Implements abstract classes that control user behavior"""
from __future__ import annotations  # types will be strings by default in 3.11

from typing import TYPE_CHECKING, Dict
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from elfpy.markets import Market
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
    open_share_price: float
        The share price at the time the short was opened.
    """

    balance: float
    open_share_price: float

    def __str__(self):
        return f"Short(balance: {self.balance}, open_share_price: {self.open_share_price})"


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

    def get_state(self, market: Market) -> dict:
        r"""The wallet's current state of public variables

        .. todo:: TODO: return a dataclass instead of dict to avoid having to check keys & the get_state_keys func
        """
        lp_token_value = 0
        if self.lp_tokens > 0:  # proceed further only if the agent has LP tokens
            if market.market_state.lp_reserves > 0:  # avoid divide by zero
                share_of_pool = self.lp_tokens / market.market_state.lp_reserves
                pool_value = market.market_state.bond_reserves * market.spot_price  # in base
                pool_value += market.market_state.share_reserves * market.market_state.share_price  # in base
                lp_token_value = pool_value * share_of_pool  # in base
        share_reserves = market.market_state.share_reserves
        # compute long values in units of base
        longs_value = 0
        longs_value_no_mock = 0
        for mint_time, long in self.longs.items():
            base = (
                market.close_long(self.address, long.balance, mint_time)[1].base
                if long.balance > 0 and share_reserves
                else 0.0
            )
            base_no_mock = long.balance * market.spot_price
            longs_value += base
            longs_value_no_mock += base_no_mock
        # compute short values in units of base
        shorts_value = 0
        shorts_value_no_mock = 0
        for mint_time, short in self.shorts.items():
            base = (
                market.close_short(self.address, short.open_share_price, short.balance, mint_time)[1].base
                if short.balance > 0 and share_reserves
                else 0.0
            )
            base_no_mock = short.balance * (1 - market.spot_price)
            shorts_value += base
            shorts_value_no_mock += base_no_mock
        return {
            f"agent_{self.address}_base": self.base,
            f"agent_{self.address}_lp_tokens": lp_token_value,
            f"agent_{self.address}_total_longs": longs_value,
            f"agent_{self.address}_total_shorts": shorts_value,
            f"agent_{self.address}_total_longs_no_mock": longs_value_no_mock,
            f"agent_{self.address}_total_shorts_no_mock": shorts_value_no_mock,
        }

    def get_state_keys(self) -> list:
        """Get state keys for a wallet."""
        return [
            f"agent_{self.address}_base",
            f"agent_{self.address}_lp_tokens",
            f"agent_{self.address}_total_longs",
            f"agent_{self.address}_total_shorts",
            f"agent_{self.address}_total_longs_no_mock",
            f"agent_{self.address}_total_shorts_no_mock",
        ]

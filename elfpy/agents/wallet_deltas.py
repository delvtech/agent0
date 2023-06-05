"""Dataclass for updating agent wallets"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from elfpy.math import FixedPoint
from elfpy.types import freezable, Quantity, TokenType

if TYPE_CHECKING:
    from elfpy.agents.wallet import Long, Short, Borrow


@freezable()
@dataclass()
class WalletDeltas:
    r"""Stores changes for an agent's wallet

    Arguments
    ----------
    balance : Quantity
        The base assets that held by the trader.
    lp_tokens : FixedPoint
        The LP tokens held by the trader.
    longs : Dict[FixedPoint, Long]
        The long positions held by the trader.
    shorts : Dict[FixedPoint, Short]
        The short positions held by the trader.
    borrows : Dict[FixedPoint, Borrow]
        The borrow positions held by the trader.
    """
    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes

    # fungible
    balance: Quantity = field(default_factory=lambda: Quantity(amount=FixedPoint(0), unit=TokenType.BASE))
    # TODO: Support multiple typed balances:
    #     balance: Dict[TokenType, Quantity] = field(default_factory=dict)
    lp_tokens: FixedPoint = FixedPoint(0)
    # non-fungible (identified by key=mint_time, stored as dict)
    longs: dict[FixedPoint, Long] = field(default_factory=dict)
    shorts: dict[FixedPoint, Short] = field(default_factory=dict)
    withdraw_shares: FixedPoint = FixedPoint(0)
    # borrow and  collateral have token type, which is not represented here
    # this therefore assumes that only one token type can be used at any given mint time
    borrows: dict[FixedPoint, Borrow] = field(default_factory=dict)
    fees_paid: FixedPoint = FixedPoint(0)

    def copy(self) -> WalletDeltas:
        """Returns a new copy of self"""
        return WalletDeltas(**copy.deepcopy(self.__dict__))

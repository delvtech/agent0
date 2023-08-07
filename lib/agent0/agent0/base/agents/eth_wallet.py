"""Empty accounts for engaging with smart contracts"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Any

from elfpy import check_non_zero
from elfpy.types import Quantity, TokenType
from elfpy.wallet.wallet_deltas import WalletDeltas
from fixedpointmath import FixedPoint
from hexbytes import HexBytes


@dataclass(kw_only=True)
class EthWallet:
    r"""Stateful variable for storing what is in the agent's wallet

    Arguments
    ----------
    address : HexBytes
        The associated agent's eth address
    balance : Quantity
        The base assets that held by the trader.
    """
    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes
    address: HexBytes
    # TODO: Support multiple typed balances:
    #     balance: Dict[TokenType, Quantity] = field(default_factory=dict)
    balance: Quantity = field(default_factory=lambda: Quantity(amount=FixedPoint(0), unit=TokenType.BASE))

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def copy(self) -> EthWallet:
        """Returns a new copy of self"""
        return EthWallet(**copy.deepcopy(self.__dict__))

    def update(self, wallet_deltas: WalletDeltas) -> None:
        """Update the agent's wallet in-place

        Arguments
        ----------
        wallet_deltas : AgentDeltas
            The agent's wallet that tracks the amount of assets this agent holds
        """
        # track over time the agent's weighted average spend, for return calculation
        for key, value_or_dict in wallet_deltas.copy().__dict__.items():
            if value_or_dict is None:
                continue
            match key:
                case "frozen" | "no_new_attribs":
                    continue
                case "balance":
                    logging.debug(
                        "agent #%g %s pre-trade = %.0g\npost-trade = %1g\ndelta = %1g",
                        self.address,
                        key,
                        float(getattr(self, key).amount),
                        float(getattr(self, key).amount + value_or_dict.amount),
                        float(value_or_dict.amount),
                    )
                    getattr(self, key).amount += value_or_dict.amount
                case _:
                    raise ValueError(f"wallet_{key=} is not allowed.")
            self.check_valid_wallet_state(self.__dict__)

    def check_valid_wallet_state(self, dictionary: dict | None = None) -> None:
        """Test that all wallet state variables are greater than zero"""
        if dictionary is None:
            dictionary = self.__dict__
        check_non_zero(dictionary)

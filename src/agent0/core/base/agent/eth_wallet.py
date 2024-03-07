"""Empty accounts for engaging with smart contracts"""

from __future__ import annotations

import copy
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from fixedpointmath import FixedPoint
from hexbytes import HexBytes

from agent0.core.base.types import Quantity, TokenType, freezable


def check_non_zero(data: Any) -> None:
    r"""Performs a general non-zero check on a dictionary or class that has a __dict__ attribute.

    Arguments
    ---------
    data: Any
        The data to check for non-zero values.
        If it is a FixedPoint then it will be checked.
        If it is dict-like then each key/value in the dict will be checked.
        Otherwise it will not be checked.
    """
    if isinstance(data, FixedPoint) and data < FixedPoint(0):
        raise AssertionError(f"{data=} >= 0")
    if hasattr(data, "__dict__"):  # can be converted to a dict
        check_non_zero(data.__dict__)
    if isinstance(data, (dict, defaultdict)):
        for key, value in data.items():
            if isinstance(value, FixedPoint) and value < FixedPoint(0):
                raise AssertionError(f"{key} attribute with {value=} must be >= 0")
            if isinstance(value, dict):
                check_non_zero(value)
            elif hasattr(value, "__dict__"):  # can be converted to a dict
                check_non_zero(value.__dict__)
            else:
                continue  # noop; frozen, etc


@freezable()
@dataclass()
class EthWalletDeltas:
    r"""Stores changes for an agent's wallet."""

    # fungible
    balance: Quantity = field(default_factory=lambda: Quantity(amount=FixedPoint(0), unit=TokenType.BASE))
    """The base assets that held by the trader."""

    # TODO: Support multiple typed balances:
    #     balance: Dict[TokenType, Quantity] = field(default_factory=dict)
    def copy(self) -> EthWalletDeltas:
        """Returns a new copy of self.

        Returns
        -------
        EthWalletDeltas
            A deepcopy of the deltas.
        """
        return EthWalletDeltas(**copy.deepcopy(self.__dict__))


T = TypeVar("T", bound=EthWalletDeltas)


@dataclass(kw_only=True)
class EthWallet(Generic[T]):
    r"""Stateful variable for storing what is in the agent's wallet."""

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes
    address: HexBytes
    """The associated agent's eth address."""
    # TODO: Support multiple typed balances:
    #     balance: Dict[TokenType, Quantity] = field(default_factory=dict)
    balance: Quantity = field(default_factory=lambda: Quantity(amount=FixedPoint(0), unit=TokenType.BASE))
    """The base assets that held by the trader."""

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def copy(self) -> EthWallet:
        """Returns a new copy of self.

        Returns
        -------
        EthWallet
            A deepcopy of the wallet.
        """
        return EthWallet(**copy.deepcopy(self.__dict__))

    def update(self, wallet_deltas: T) -> None:
        """Update the agent's wallet in-place

        Arguments
        ---------
        wallet_deltas: AgentDeltas
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
        """Test that all wallet state variables are greater than zero.

        Arguments
        ---------
        dictionary: dict | None, optional
            The dictionary to check.
            If not provided, it will use `self.__dict__`.
        """
        if dictionary is None:
            dictionary = self.__dict__
        check_non_zero(dictionary)

"""Empty accounts for engaging with smart contracts"""

from __future__ import annotations

import copy
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from fixedpointmath import FixedPoint
from hexbytes import HexBytes

from agent0.core.base.types import Quantity, TokenType


def check_non_zero(data: Any) -> None:
    r"""Perform a general non-zero check on a dictionary or class that has a __dict__ attribute.

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


@dataclass(kw_only=True)
class EthWallet:
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
        """Return a new copy of self.

        Returns
        -------
        EthWallet
            A deepcopy of the wallet.
        """
        return EthWallet(**copy.deepcopy(self.__dict__))

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

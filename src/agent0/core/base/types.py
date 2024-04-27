"""Core types used across the repo."""

from __future__ import annotations  # types will be strings by default in 3.11

from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

from fixedpointmath import FixedPoint

# We don't need to worry about return docstrings for the decorator because they will be overwritten
# pylint: disable=missing-return-doc
# pylint: disable=missing-return-type-doc

# This is the minimum allowed value to be passed into calculations to avoid
# problems with sign flips that occur when the floating point range is exceeded.
WEI = FixedPoint(scaled_value=1)  # smallest denomination of ether


class Freezable:
    """Config object with frozen attributes."""

    def __setattr__(self, attrib: str, value: Any) -> None:
        """Set the value of the attribute."""
        if hasattr(self, attrib) and hasattr(self, "frozen") and getattr(self, "frozen"):
            raise AttributeError(f"{self.__class__.__name__} is frozen, cannot change attribute '{attrib}'.")
        if not hasattr(self, attrib) and hasattr(self, "no_new_attribs") and getattr(self, "no_new_attribs"):
            raise AttributeError(f"{self.__class__.__name__} has no_new_attribs set, cannot add attribute '{attrib}'.")
        super().__setattr__(attrib, value)

    def freeze(self) -> None:
        """Disallows changing existing members."""
        super().__setattr__("frozen", True)

    def disable_new_attribs(self) -> None:
        """Disallows adding new members."""
        super().__setattr__("no_new_attribs", True)

    def astype(self, new_type):
        """Cast all member attributes to a new type.

        Arguments
        ---------
        new_type: Any
            The type to cast to.
        """
        new_data = {}
        for attr_name, attr_value in self.__dict__.items():
            try:
                if isinstance(attr_value, list):
                    new_data[attr_name] = [new_type(val) for val in attr_value]
                else:
                    new_data[attr_name] = new_type(attr_value)
                if hasattr(self, "__annotations__"):
                    self.__annotations__[attr_name] = new_type
            except (ValueError, TypeError) as err:
                raise TypeError(f"unable to cast {attr_name=} of type {type(attr_value)=} to {new_type=}") from err
        # create a new instance of the data class with the updated
        # attributes, rather than modifying the current instance in-place
        return self.__class__(**new_data)

    @property
    def dtypes(self) -> dict[str, type]:
        """Return a dict listing name & type of each member variable.

        Returns
        -------
        dict[str, type]
            The named types of the class.
        """
        return {attr_name: type(attr_value) for attr_name, attr_value in self.__dict__.items()}


class TokenType(Enum):
    r"""A type of token."""

    BASE = "base"


@dataclass
class Quantity:
    r"""An amount with a unit."""

    amount: FixedPoint
    unit: TokenType

    def __neg__(self):
        """Return the negative of the amount."""
        return Quantity(amount=-self.amount, unit=self.unit)


class MarketType(Enum):
    r"""A type of market."""

    HYPERDRIVE = "hyperdrive"
    BORROW = "borrow"


MarketAction = TypeVar("MarketAction")


@dataclass
class Trade(Generic[MarketAction]):
    """A trade for a market."""

    market_type: MarketType
    market_action: MarketAction

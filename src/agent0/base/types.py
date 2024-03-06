"""Core types used across the repo"""

from __future__ import annotations  # types will be strings by default in 3.11

from dataclasses import asdict, dataclass, is_dataclass, replace
from enum import Enum
from functools import wraps
from typing import Any, Generic, TypeVar

from fixedpointmath import FixedPoint

# We don't need to worry about return docstrings for the decorator because they will be overwritten
# pylint: disable=missing-return-doc
# pylint: disable=missing-return-type-doc

# This is the minimum allowed value to be passed into calculations to avoid
# problems with sign flips that occur when the floating point range is exceeded.
WEI = FixedPoint(scaled_value=1)  # smallest denomination of ether


class FrozenClass:
    """Config object with frozen attributes."""

    def freeze(self):
        """Disallows changing existing members."""
        raise NotImplementedError

    def disable_new_attribs(self):
        """Disallows adding new members."""
        raise NotImplementedError

    def astype(self, _new_type):
        """Cast all member attributes to a new type."""
        raise NotImplementedError

    @property
    def dtypes(self):
        """Return a dict listing name & type of each member variable."""
        raise NotImplementedError


def freezable(frozen: bool = False, no_new_attribs: bool = False):
    """A wrapper that allows classes to be frozen, such that existing member attributes cannot be changed.

    Arguments
    ---------
    frozen: bool, optional
        Whether or not the class attributes can be changed.
        Defaults to False, indicating that they can be changed.
    no_new_attribs: bool, optional
        Whether or not new attributes can be added to the class.
        Defaults to False, indicating that new attributes can be added.
    """

    def decorator(cls):
        """Decorator for the provided class.

        Arguments
        ---------
        cls: Class
            The Class object to decorate, which can optionally be a Dataclass
        """
        # this decorator should only be placed atop a dataclass
        if not is_dataclass(cls):
            raise TypeError("The class must be a data class.")

        @wraps(wrapped=cls, updated=())
        class DecoratedFrozenClass(cls, FrozenClass):
            """Subclass cls to enable freezing of attributes.

            .. todo:: resolve why pyright cannot access member "freeze" when instantiated_class.freeze() is called
            """

            def __init__(self, *args, frozen=frozen, no_new_attribs=no_new_attribs, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                super().__setattr__("frozen", frozen)
                super().__setattr__("no_new_attribs", no_new_attribs)

            def __setattr__(self, attrib: str, value: Any) -> None:
                if hasattr(self, attrib) and hasattr(self, "frozen") and getattr(self, "frozen"):
                    raise AttributeError(f"{self.__class__.__name__} is frozen, cannot change attribute '{attrib}'.")
                if not hasattr(self, attrib) and hasattr(self, "no_new_attribs") and getattr(self, "no_new_attribs"):
                    raise AttributeError(
                        f"{self.__class__.__name__} has no_new_attribs set, cannot add attribute '{attrib}'."
                    )
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
                for attr_name, attr_value in asdict(self).items():
                    try:
                        if isinstance(attr_value, list):
                            new_data[attr_name] = [new_type(val) for val in attr_value]
                        else:
                            new_data[attr_name] = new_type(attr_value)
                        self.__annotations__[attr_name] = new_type
                    except (ValueError, TypeError) as err:
                        raise TypeError(
                            f"unable to cast {attr_name=} of type {type(attr_value)=} to {new_type=}"
                        ) from err
                # create a new instance of the data class with the updated
                # attributes, rather than modifying the current instance in-place
                return replace(self, **new_data)

            @property
            def dtypes(self) -> dict[str, type]:
                """Return a dict listing name & type of each member variable.

                Returns
                -------
                dict[str, type]
                    The named types of the class.
                """
                dtypes_dict: dict[str, type] = {}
                for attr_name, attr_value in asdict(self).items():
                    dtypes_dict[attr_name] = type(attr_value)
                return dtypes_dict

        # Set the name of the wrapped class to the name of the input class to preserve metadata
        DecoratedFrozenClass.__name__ = cls.__name__
        return DecoratedFrozenClass

    return decorator


class TokenType(Enum):
    r"""A type of token"""

    BASE = "base"


@dataclass
class Quantity:
    r"""An amount with a unit."""

    amount: FixedPoint
    unit: TokenType

    def __neg__(self):
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

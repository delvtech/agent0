"""Core types used across the repo"""
from __future__ import annotations  # types will be strings by default in 3.11

from dataclasses import dataclass, asdict, replace, is_dataclass
from enum import Enum
from functools import wraps
from typing import Any, Type


def freezable(frozen: bool = False, no_new_attribs: bool = False) -> Type:
    r"""A wrapper that allows classes to be frozen, such that existing member attributes cannot be changed"""

    def decorator(cls):
        if not is_dataclass(cls):
            raise TypeError("The class must be a data class.")

        @wraps(wrapped=cls, updated=())
        class FrozenClass(cls):
            """Subclass cls to enable freezing of attributes

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
                """disallows changing existing members"""
                super().__setattr__("frozen", True)

            def disable_new_attribs(self) -> None:
                """disallows adding new members"""
                super().__setattr__("no_new_attribs", True)

            def astype(self, new_type):
                """Cast all member attributes to a new type"""
                new_data = {}
                for attr_name, attr_value in asdict(self).items():
                    try:
                        new_data[attr_name] = new_type(attr_value)
                    except ValueError:
                        print(f"Unable to cast {attr_name} to {new_type}")

                return replace(self, **new_data)

            @property
            def dtypes(self) -> dict[str, type]:
                """Return a dict listing name & type of each member variable"""
                dtypes_dict: dict[str, type] = {}
                for attr_name, attr_value in asdict(self).items():
                    dtypes_dict[attr_name] = type(attr_value)
                return dtypes_dict

        # Set the name of the wrapped class to the name of the input class to preserve metadata
        FrozenClass.__name__ = cls.__name__
        return FrozenClass

    return decorator


class MarketType(Enum):
    r"""A type of market"""

    HYPERDRIVE = "hyperdrive"
    BORROW = "borrow"


class TokenType(Enum):
    r"""A type of token"""

    BASE = "base"
    PT = "pt"
    LP_SHARE = "lp_share"


@dataclass
class Quantity:
    r"""An amount with a unit"""

    amount: float
    unit: TokenType

    def __neg__(self):
        return Quantity(amount=-self.amount, unit=self.unit)


@dataclass
class Trade:
    r"""A trade for a market"""

    market: MarketType
    trade: Any  # TODO: How to specify the type as a generic market action?

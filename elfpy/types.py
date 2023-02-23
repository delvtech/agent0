"""Core types used across the repo"""
from __future__ import annotations  # types will be strings by default in 3.11
from enum import Enum
from dataclasses import dataclass
from functools import wraps
from typing import Type, Any


def to_description(description: str) -> dict[str, str]:
    r"""A dataclass helper that constructs metadata containing a description."""
    return {"description": description}


def freezable(frozen: bool = False, no_new_attribs: bool = False) -> Type:
    r"""A wrapper that allows classes to be frozen, such that existing member attributes cannot be changed"""

    def decorator(cls: Type) -> Type:
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

        return FrozenClass

    return decorator


class MarketType(Enum):
    r"""A type of market"""

    YIELDSPACE = "yieldspace"
    HYPERDRIVE = "hyperdrive"
    BORROW = "borrow"


class TokenType(Enum):
    r"""A type of token"""

    BASE = "base"
    PT = "pt"


@dataclass
class Quantity:
    r"""An amount with a unit"""

    amount: float
    unit: TokenType

    def __neg__(self):
        return Quantity(amount=-self.amount, unit=self.unit)


@dataclass
class Trade:
    r"""A trade for a in the simulation"""

    # TODO: change this import to Agent after we move this dataclass to simulators/
    agent: Any
    market: MarketType
    trade: Any  # TODO: How to specify the type as a generic market action?

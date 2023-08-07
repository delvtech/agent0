"""Market state information."""
from __future__ import annotations

import copy
from dataclasses import dataclass

import elfpy
from elfpy import types


@types.freezable(frozen=False, no_new_attribs=False)
@dataclass(kw_only=True)
class BaseMarketState:
    r"""The state of an AMM."""

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    def apply_delta(self, delta: BaseMarketState) -> None:
        r"""Applies a delta to the market state."""
        raise NotImplementedError

    def copy(self) -> BaseMarketState:
        """Returns a new copy of self"""
        return BaseMarketState(**copy.deepcopy(self.__dict__))

    def check_valid_market_state(self, dictionary: dict | None = None) -> None:
        """Test that all market state variables are greater than zero"""
        if dictionary is None:
            dictionary = self.__dict__
        elfpy.check_non_zero(dictionary)

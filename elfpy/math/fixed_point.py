"""Fixed point datatype & arithmetic"""
from __future__ import annotations

import copy
from typing import Union

import elfpy.errors.errors as errors
from .fixed_point_integer_math import FixedPointIntegerMath


class FixedPoint:
    """Fixed-point number datatype

    Values are stored internally as intergers, however they are generally treated like floats.
    The first (right-most) `decimal_places` digits represent what would be to the right of
    the decimal in a float representation, while the remaining (left-most) digits represent
    the whole-number part of a float representation.

    The type supports most math sugar, including `+`, `-`, `*`, `/`, `//`, `%`, and `**`.
    It also supports non-finite values and corresponding behavior.

    Arithmetic follows the Delv Hyperdrive Solidity smart contract standards.
    However, we have expanded some operations due to the flexible application space of the Python simulations,
    for example by including non-finite representations.
    Whenever expanding beyond what is in the Solidity contracts, we follow the IEEE 754 floating point standard.

    .. todo::
        * add __round__, __ceil__, __floor__, __trunc__ so that it will be a proper numbers.Real type
        https://docs.python.org/3/library/numbers.html#numbers.Real
    """

    int_value: int  # integer representation of self

    def __init__(self, value: Union[FixedPoint, float, int, str] = 0, decimal_places: int = 18, signed: bool = True):
        """Store fixed-point properties"""
        # TODO: support unsigned option
        if not signed:
            raise NotImplementedError("only signed FixedPoint ints are supported.")
        self.signed = signed
        # TODO: support non-default decimal values
        if decimal_places != 18:
            raise NotImplementedError("only 18 decimal precision FixedPoint ints are supported.")
        self.decimal_places = decimal_places
        # parse input and set up class properties
        self.special_value = None
        if isinstance(value, float):
            value = int(value * 10**decimal_places)  # int truncates to `decimal_places` precision
        if isinstance(value, str):
            # non-finite values are specified with strings
            if value.lower() in ("nan", "inf", "-inf"):
                self.special_value = value.lower()
                value = 0
            else:
                if "." not in value:
                    raise ValueError(
                        "string argument must be a float string, e.g. '1.0', for the FixedPoint constructor"
                    )
                lhs, rhs = value.split(".")
                rhs = rhs.replace("_", "")  # removes underscores; they won't affect `int` cast and will affect `len`
                is_negative = "-" in lhs
                if is_negative:
                    value = int(lhs) * 10**decimal_places - int(rhs) * 10 ** (decimal_places - len(rhs))
                else:
                    value = int(lhs) * 10**decimal_places + int(rhs) * 10 ** (decimal_places - len(rhs))
        if isinstance(value, FixedPoint):
            self.special_value = value.special_value
            value = value.int_value
        self.int_value = copy.copy(int(value))

    def _coerce_other(self, other):
        """Cast inputs to the FixedPoint type if they come in as something else.

        .. note::
            Right now we do not support operating against int and float because those are logically confusing
        """
        if isinstance(other, FixedPoint):
            if other.special_value is not None:
                return FixedPoint(other.special_value)
            return other
        if isinstance(other, (int, float)):  # currently don't allow floats & ints
            raise TypeError(f"unsupported operand type(s): {type(other)}")
        return NotImplemented

    def __add__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables '+' syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if self.is_nan() or other.is_nan():  # anything + nan is nan
            return FixedPoint("nan")
        if self.is_inf():  # self is inf
            if other.is_inf() and self.sign() != other.sign():  # both are inf, signs don't match
                return FixedPoint("nan")
            return self  # doesn't matter if other is inf or not because if other is inf, then signs match
        if other.is_inf():  # self is not inf
            return other
        return FixedPoint(FixedPointIntegerMath.add(self.int_value, other.int_value), self.decimal_places, self.signed)

    def __radd__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables reciprocal addition to support other + FixedPoint"""
        return self.__add__(other)

    def __sub__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables '-' syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if self.is_nan() or other.is_nan():  # anything - nan is nan
            return FixedPoint("nan")
        if self.is_inf():  # self is  inf
            if other.is_inf() and self.sign() == other.sign():  # both are inf, sign is equal
                return FixedPoint("nan")
            # it doesn't matter if other is inf because the signs are different & finite gets overruled
            # e.g. inf - (-inf) = inf; -inf - (inf) = -inf; and inf - (+/-)finite = inf
            return self
        if other.is_inf():  # self is not inf, so return sign flipped other
            return FixedPoint("-inf") if other.sign() == FixedPoint("1.0") else FixedPoint("inf")
        return FixedPoint(FixedPointIntegerMath.sub(self.int_value, other.int_value), self.decimal_places, self.signed)

    def __rsub__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables reciprocal subtraction to support other - FixedPoint"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if other.is_nan() or self.is_nan():
            return FixedPoint("nan")
        if other.is_inf():
            if self.is_inf() and other.sign() == self.sign():
                return FixedPoint("nan")
            return other
        if self.is_inf():
            return self
        return FixedPoint(FixedPointIntegerMath.sub(other.int_value, self.int_value), self.decimal_places, self.signed)

    def __mul__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables '*' syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if self.is_nan() or other.is_nan():
            return FixedPoint("nan")
        if self.is_zero() or other.is_zero():
            if self.is_inf() or other.is_inf():
                return FixedPoint("nan")  # zero * inf is nan
            return FixedPoint(0)  # zero * finite is zero
        if self.is_inf() or other.is_inf():  # anything * inf is inf, follow normal mul rules for sign
            return FixedPoint("inf" if self.sign() == other.sign() else "-inf")
        return FixedPoint(
            FixedPointIntegerMath.mul_down(self.int_value, other.int_value), self.decimal_places, self.signed
        )

    def __rmul__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables reciprocal multiplication to support other * FixedPoint"""
        return self * other

    def __truediv__(self, other):
        """Enables '/' syntax, which mirrors `//` syntax.

        We mirror floordiv because most solidity contract equations use divdown
        """
        return self.__floordiv__(other)

    def __rtruediv__(self, other):
        """Enables reciprocal division to support other / FixedPoint"""
        return self.__truediv__(other)

    def __floordiv__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables '//' syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if other == FixedPoint("0.0"):
            raise errors.DivisionByZero
        if self.is_nan() or other.is_nan():  # nan / anything is nan
            return FixedPoint("nan")
        if self.is_inf():  # self is inf
            if other.is_inf():  # inf / inf is nan
                return FixedPoint("nan")
            return self  # (+/-) inf / finite is (+/-) inf
        if other.is_inf():  # self is finite
            return FixedPoint(0)  # finite / (+/-) inf is zero
        return FixedPoint(
            FixedPointIntegerMath.div_down(self.int_value, other.int_value), self.decimal_places, self.signed
        )

    def __pow__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables '**' syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if self.is_finite() and other.is_finite():
            return FixedPoint(
                FixedPointIntegerMath.pow(self.int_value, other.int_value), self.decimal_places, self.signed
            )
        # pow is tricky -- leaning on float operations under the hood for non-finite
        return FixedPoint(str(float(self) ** float(other)))

    def __rpow__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables reciprocal pow to support other ** FixedPoint"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        return FixedPoint(FixedPointIntegerMath.pow(self.int_value, other.int_value), self.decimal_places, self.signed)

    def __mod__(self, other: FixedPoint) -> FixedPoint:
        r"""Enables `%` syntax

        In Python, for ints and floats, this is computed as
        `r = a - (n * floor(a/n))`,
        where, `r` is the remainder; `a` is the dividend (i.e. `self`); and `n` is the divisor (i.e. `other`).
        Note that `floor` will always round negative results away from zero.
        This means that modulo will take the sign of the divisor.
        This is the same as modulo in `Solidity <https://en.wikipedia.org/wiki/Modulo#In_programming_languages>`_,
        but different from the `Decimal.decimal` and `math.fmod`
        `implementations in Python <https://realpython.com/python-modulo-operator/#python-modulo-operator-advanced-uses>`_.
        """
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if other == FixedPoint("0.0"):
            raise errors.DivisionByZero
        if not self.is_finite() or other.is_nan():
            return FixedPoint("nan")
        if other.is_inf():
            return self
        if other == FixedPoint("1.0"):  # everything divides evenly into 1
            return FixedPoint("0.0")
        return self - (other * (self / other).floor())

    def __rmod__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables reciprocal modulo to allow other % FixedPoint"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        return other % self

    def __neg__(self) -> FixedPoint:
        """Enables flipping value sign"""
        if self.is_nan():
            return self
        return FixedPoint("-1.0") * self

    def __abs__(self) -> FixedPoint:
        """Enables 'abs()' function"""
        if self.is_nan():
            return self
        return FixedPoint(abs(self.int_value), self.decimal_places, self.signed)

    # comparison methods
    def __eq__(self, other: FixedPoint) -> bool:
        """Enables `==` syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if not self.is_finite() or not other.is_finite():
            if self.is_nan() or other.is_nan():
                return False
            return self.special_value == other.special_value
        return self.int_value == other.int_value

    def __ne__(self, other: FixedPoint) -> bool:
        """Enables `!=` syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if not self.is_finite() or not other.is_finite():
            if self.is_nan() or other.is_nan():
                return True
            return self.special_value != other.special_value
        return self.int_value != other.int_value

    def __lt__(self, other: FixedPoint) -> bool:
        """Enables `<` syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if self.is_nan() or other.is_nan():  # nan can't be compared
            return False
        if self.is_inf() and other.is_inf():
            return self.sign() < other.sign()
        if self.is_inf():  # other is finite
            return self.sign() < FixedPoint(0)
        if other.is_inf():  # self is finite
            return other.sign() > FixedPoint(0)
        # both are finite
        return self.int_value < other.int_value

    def __le__(self, other: FixedPoint) -> bool:
        """Enables `<=` syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if self.is_nan() or other.is_nan():  # nan can't be compared
            return False
        if self.is_inf() and other.is_inf():
            return self.sign() <= other.sign()
        if self.is_inf():  # other is finite
            return self.sign() < FixedPoint(0)
        if other.is_inf():  # self is finite
            return other.sign() > FixedPoint(0)
        # both are finite
        return self.int_value <= other.int_value

    def __gt__(self, other: FixedPoint) -> bool:
        """Enables `>` syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if self.is_nan() or other.is_nan():  # nan can't be compared
            return False
        if self.is_inf() and other.is_inf():
            return self.sign() > other.sign()
        if self.is_inf():  # other is finite
            return self.sign() > FixedPoint(0)
        if other.is_inf():  # self is finite
            return other.sign() < FixedPoint(0)
        # both are finite
        return self.int_value > other.int_value

    def __ge__(self, other: FixedPoint) -> bool:
        """Enables `>=` syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if self.is_nan() or other.is_nan():  # nan can't be compared
            return False
        if self.is_inf() and other.is_inf():
            return self.sign() >= other.sign()
        if self.is_inf():  # other is finite
            return self.sign() > FixedPoint(0)
        if other.is_inf():  # self is finite
            return other.sign() < FixedPoint(0)
        # both are finite
        return self.int_value >= other.int_value

    # type casting
    def __int__(self) -> int:
        """Cast to int"""
        if self.special_value is not None:
            raise ValueError(f"cannot convert FixedPoint {self.special_value} to integer")
        return self.int_value

    def __float__(self) -> float:
        """Cast to float"""
        if self.special_value is not None:
            return float(self.special_value)
        return float(self.int_value) / 10**self.decimal_places

    def __bool__(self) -> bool:
        """Cast to bool"""
        if self.is_finite() and self != FixedPoint(0):
            return True
        return False

    def __str__(self) -> str:
        """Cast to str"""
        if self.special_value is not None:
            return self.special_value
        lhs = str(self.int_value)[:-18]  # remove right-most 18 digits for whole number
        if len(lhs) == 0:  # float(input) was <0
            sign = "-" if self.int_value < 0 else ""
            lhs = sign + "0"
            scale = len(str(self.int_value))
            if self.int_value < 0:
                scale -= 1  # ignore negative sign
            num_left_zeros = self.decimal_places - scale
            rhs = "0" * num_left_zeros + str(abs(self.int_value))
        else:  # float(input) was >=0
            rhs = str(self.int_value)[len(lhs) :]  # should be 18 left
        # remove trailing zeros
        if len(rhs.rstrip("0")) == 0:  # all zeros
            rhs = "0"
        else:
            rhs = rhs.rstrip("0")
        return lhs + "." + rhs

    def __repr__(self) -> str:
        """Returns executable string representation

        For example: "FixedPoint(1234)"
        """
        if self.special_value is not None:
            return f"{self.__class__.__name__}({self.special_value})"
        return f"{self.__class__.__name__}({self.int_value})"

    # additional arethmitic & helper functions
    def div_up(self, other: int | FixedPoint) -> FixedPoint:
        """Divide self by other, rounding up"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if other <= FixedPoint("0.0"):
            raise errors.DivisionByZero
        return FixedPoint(
            FixedPointIntegerMath.div_up(self.int_value, other.int_value), self.decimal_places, self.signed
        )

    def mul_up(self, other: int | FixedPoint) -> FixedPoint:
        """Multiply self by other, rounding up"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if self == FixedPoint("0.0") or other == FixedPoint("0.0"):
            return FixedPoint("0.0")
        return FixedPoint(
            FixedPointIntegerMath.mul_up(self.int_value, other.int_value), self.decimal_places, self.signed
        )

    def is_nan(self) -> bool:
        """Return True if self is not a number (NaN)."""
        if self.special_value is not None and self.special_value == "nan":
            return True
        return False

    def is_inf(self) -> bool:
        """Return True if self is inf or -inf."""
        if self.special_value is not None and "inf" in self.special_value:
            return True
        return False

    def is_zero(self) -> bool:
        """Return True if self is zero, and False is self is non-zero or non-finite"""
        if not self.is_finite():
            return False
        return self.int_value == 0

    def is_finite(self) -> bool:
        """Return True if self is finite, that is not inf, -inf, or nan"""
        return not (self.is_nan() or self.is_inf())

    def sign(self) -> FixedPoint:
        """Return the sign of self if self is finite, inf, or -inf; otherwise return nan"""
        if self.special_value == "nan":
            return FixedPoint("nan")
        if self == FixedPoint("0.0"):
            return self
        if "-" in str(self):
            return FixedPoint("-1.0")
        return FixedPoint("1.0")

    def floor(self) -> FixedPoint:
        """Returns an integer rounded following Python `floor` behavior
        Given a real number x, return as output the greatest integer less than or equal to x.
        """
        if not self.is_finite():
            return self
        lhs, rhs = str(self).split(".")
        # if the number is negative & there is a remainder
        if self.int_value < 0 < len(rhs.rstrip("0")):
            return FixedPoint(str(int(lhs) - 1) + ".0")  # round down to -inf
        return FixedPoint(lhs + ".0")

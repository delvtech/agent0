"""Fixed point datatype & arithmetic"""
from __future__ import annotations

import re
import copy
from typing import Union, Any, Literal

import elfpy.errors.errors as errors
from .fixed_point_integer_math import FixedPointIntegerMath

OtherTypes = Union[int, bool, float]
SpecialValues = Literal["nan", "inf", "-inf"]


class FixedPoint:
    r"""Fixed-point number datatype

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
    """

    _scaled_value: int  # integer representation of self
    _special_value: SpecialValues  # string representation of self

    def __init__(
        self,
        value: OtherTypes | str | FixedPoint | None = None,  # use default conversion
        scaled_value: int | None = None,  # assume integer is already converted
        decimal_places: int = 18,  # how many decimal places to store (must be 18)
        signed: bool = True,  # whether or not it is a signed FixedPoint (must be True)
    ):
        r"""Store fixed-point properties"""
        if value is None and scaled_value is None:
            value = 0
        # TODO: support unsigned option
        if not signed:
            raise NotImplementedError("only signed FixedPoint ints are supported.")
        self.signed = signed
        # TODO: support non-default decimal values
        if decimal_places != 18:
            raise NotImplementedError("only 18 decimal precision FixedPoint ints are supported.")
        self.decimal_places = decimal_places
        # parse input and set up class properties
        super().__setattr__("_scaled_value", None)
        super().__setattr__("_special_value", None)
        # check bool first, and coerce it following `float` rules
        if isinstance(value, bool):
            value = int(value)
        if value is None:
            if not isinstance(scaled_value, int):
                raise TypeError(f"{scaled_value=} must have type `int`")
            super().__setattr__("_scaled_value", scaled_value)
        elif isinstance(value, float):
            # int truncates to `decimal_places` precision
            super().__setattr__("_scaled_value", int(value * 10**decimal_places))
        elif isinstance(value, int):
            super().__setattr__("_scaled_value", value * 10**decimal_places)
        elif isinstance(value, FixedPoint):
            super().__setattr__("_special_value", value.special_value)
            super().__setattr__("_scaled_value", value.scaled_value)
        elif isinstance(value, str):
            # non-finite values are specified with strings
            if value.lower() in ("nan", "inf", "-inf"):
                super().__setattr__("_special_value", value.lower())
                super().__setattr__("_scaled_value", 0)
            else:  # string must be a float or int representation
                if not self._is_valid_number(value):
                    raise ValueError(
                        f"string argument {value=} must be a float string, e.g. '1.0', for the FixedPoint constructor"
                    )
                if "." not in value:  # input is always assumed to be a float
                    value += ".0"
                integer, remainder = value.split(".")  # lhs = integer part, rhs = fractional part
                # removes underscores; they won't affect `int` cast and will affect `len`
                remainder = remainder.replace("_", "")
                is_negative = "-" in integer
                if is_negative:
                    super().__setattr__(
                        "_scaled_value",
                        int(integer) * 10**decimal_places - int(remainder) * 10 ** (decimal_places - len(remainder)),
                    )
                else:
                    super().__setattr__(
                        "_scaled_value",
                        int(integer) * 10**decimal_places + int(remainder) * 10 ** (decimal_places - len(remainder)),
                    )
        else:
            raise TypeError(f"{type(value)=} is not supported")

    @property
    def scaled_value(self) -> int:
        """Scaled value from FixedPoint format

        This work-around is required to make the internal representation immutable,
        which then stops dictionary keys from being changed unexpectedly
        """
        # we had to set _scaled_value to super() in __init__ to get around immutability
        # pylint: disable=no-member
        return self._scaled_value

    @scaled_value.setter
    def scaled_value(self, value: Any) -> None:
        """Not allowed to set the scaled value"""
        raise ValueError("scaled_value is immutable")

    @property
    def special_value(self) -> str:
        """Special value from FixedPoint format

        This work-around is required to make the internal representation immutable,
        which then stops dictionary keys from being changed unexpectedly
        """
        # we had to set _scaled_value to super() in __init__ to get around immutability
        # pylint: disable=no-member
        return self._special_value

    @special_value.setter
    def special_value(self, value: Any) -> None:
        raise ValueError("special_value is immutable")

    def __setattr__(self, key: str, value: Any) -> None:
        """Set attribute, while denying _scaled_value"""
        if key[0] == "_":  # immutable attributes start with _
            raise ValueError(f"{key} is an immutable attribute")
        super().__setattr__(key, value)

    @staticmethod
    def _is_valid_number(float_string: str) -> bool:
        r"""Regular expression pattern to determine if the string argument is valid for initializing FixedPoint

        Valid inputs are:
        - an optional negative sign
        - one or more digits
        - an optional underscore for digit grouping
        - an optional decimal point followed by one or more digits

        The regular expression used here, `^-?\d{1,3}(?:_?\d{3})*(?:\.\d+)?$`, works as follows:

        `^` : Start of the string

        `-?` : An optional negative sign

        `\d{1,3}` : Between one and three digit

        `(?:_?\d{3})*` : Zero or more groups consisting of an optional underscore and three digits

        `(?:\.\d+)?` : An optional group consisting of a decimal point and one or more digits

        `$` : End of the string

        Arguments
        ---------
        float_string : str
            FixedPoint constructor argument that represents a valid number

        Returns
        -------
        bool
            True if the string represents a valid number
        """
        pattern = r"^-?\d{1,3}(?:_?\d{3})*(?:\.\d+)?$"
        return bool(re.match(pattern, float_string))

    def _coerce_other(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Cast inputs to the FixedPoint type if they come in as something else.

        .. note::
            Right now we do not support operating against int and float because those are logically confusing
        """
        if isinstance(other, bool):
            return FixedPoint(float(other))
        if isinstance(other, FixedPoint):
            if other.special_value is not None:
                return FixedPoint(other.special_value)
            return other
        if isinstance(other, int):
            return FixedPoint(other)
        if isinstance(other, float):  # currently don't allow (most) floats
            if other == 0.0:  # 0 is unambiguous, so we will allow it
                return FixedPoint(other)
            raise TypeError(f"unsupported operand type(s): {type(other)}")
        raise TypeError(f"unsupported operand type(s): {type(other)}")

    def __add__(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Enables '+' syntax"""
        other = self._coerce_other(other)
        if self.is_nan() or other.is_nan():  # anything + nan is nan
            return FixedPoint("nan")
        if self.is_inf():  # self is inf
            if other.is_inf() and self.sign() != other.sign():  # both are inf, signs don't match
                return FixedPoint("nan")
            return self  # doesn't matter if other is inf or not because if other is inf, then signs match
        if other.is_inf():  # self is not inf
            return other
        return FixedPoint(
            scaled_value=FixedPointIntegerMath.add(self.scaled_value, other.scaled_value),
            decimal_places=self.decimal_places,
            signed=self.signed,
        )

    def __radd__(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Enables reciprocal addition to support other + FixedPoint"""
        return self + other  # commutative operation

    def __sub__(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Enables '-' syntax"""
        other = self._coerce_other(other)
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
        return FixedPoint(
            scaled_value=FixedPointIntegerMath.sub(self.scaled_value, other.scaled_value),
            decimal_places=self.decimal_places,
            signed=self.signed,
        )

    def __rsub__(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Enables reciprocal subtraction to support other - FixedPoint"""
        other = self._coerce_other(other)  # convert to FixedPoint
        return other - self  # now use normal subtraction

    def __mul__(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Enables '*' syntax

        We use mul_down to match the majority of Hyperdrive solidity contract equations
        """
        other = self._coerce_other(other)
        if self.is_nan() or other.is_nan():
            return FixedPoint("nan")
        if self.is_zero() or other.is_zero():
            if self.is_inf() or other.is_inf():
                return FixedPoint("nan")  # zero * inf is nan
            return FixedPoint(0)  # zero * finite is zero
        if self.is_inf() or other.is_inf():  # anything * inf is inf, follow normal mul rules for sign
            return FixedPoint("inf" if self.sign() == other.sign() else "-inf")
        return FixedPoint(
            scaled_value=FixedPointIntegerMath.mul_down(self.scaled_value, other.scaled_value),
            decimal_places=self.decimal_places,
            signed=self.signed,
        )

    def __rmul__(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Enables reciprocal multiplication to support other * FixedPoint"""
        return self * other  # commutative operation

    def __truediv__(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Enables '/' syntax.

        We use div_down to match the majority of Hyperdrive solidity contract equations
        """
        other = self._coerce_other(other)
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
            scaled_value=FixedPointIntegerMath.div_down(self.scaled_value, other.scaled_value),
            decimal_places=self.decimal_places,
            signed=self.signed,
        )

    def __rtruediv__(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Enables reciprocal division to support other / FixedPoint"""
        other = self._coerce_other(other)  # convert to FixedPoint
        return other / self  # then divide normally

    def __floordiv__(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Enables '//' syntax

        While FixedPoint numbers are represented as integers, they act like floats.
        So floordiv should return only whole numbers.
        """
        return (self.__truediv__(other)).__floor__()

    def __rfloordiv__(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Enables reciprocal floor division to support other // FixedPoint"""
        other = self._coerce_other(other)  # convert to FixedPoint
        return other // self  # then normal divide

    def __pow__(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Enables '**' syntax"""
        other = self._coerce_other(other)
        if self.is_finite() and other.is_finite():
            return FixedPoint(
                scaled_value=FixedPointIntegerMath.pow(self.scaled_value, other.scaled_value),
                decimal_places=self.decimal_places,
                signed=self.signed,
            )
        # pow is tricky -- leaning on float operations under the hood for non-finite
        return FixedPoint(str(float(self) ** float(other)))

    def __rpow__(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Enables reciprocal pow to support other ** FixedPoint"""
        other = self._coerce_other(other)  # convert to FixedPoint
        return other**self  # then normal pow

    def __mod__(self, other: OtherTypes | FixedPoint) -> FixedPoint:
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
        if other == FixedPoint("0.0"):
            raise errors.DivisionByZero
        if not self.is_finite() or other.is_nan():
            return FixedPoint("nan")
        if other.is_inf():
            return self
        if other == FixedPoint("1.0"):  # everything divides evenly into 1
            return FixedPoint("0.0")
        return self - (other * (self / other).floor())

    def __rmod__(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Enables reciprocal modulo to allow other % FixedPoint"""
        other = self._coerce_other(other)
        return other % self

    def __divmod__(self, other: OtherTypes | FixedPoint) -> tuple[FixedPoint, FixedPoint]:
        r"""Enables `divmod()` function"""
        return (self // other, self % other)

    def __neg__(self) -> FixedPoint:
        r"""Enables flipping value sign"""
        if self.is_nan():
            return self
        return FixedPoint("-1.0") * self

    def __abs__(self) -> FixedPoint:
        r"""Enables 'abs()' function"""
        if self.is_nan():
            return self
        return FixedPoint(scaled_value=abs(self.scaled_value), decimal_places=self.decimal_places, signed=self.signed)

    # comparison methods
    def __eq__(self, other: OtherTypes | FixedPoint) -> bool:
        r"""Enables `==` syntax"""
        other = self._coerce_other(other)
        if not self.is_finite() or not other.is_finite():
            if self.is_nan() or other.is_nan():
                return False
            return self.special_value == other.special_value
        return self.scaled_value == other.scaled_value

    def __ne__(self, other: OtherTypes | FixedPoint) -> bool:
        r"""Enables `!=` syntax"""
        other = self._coerce_other(other)
        if not self.is_finite() or not other.is_finite():
            if self.is_nan() or other.is_nan():
                return True
            return self.special_value != other.special_value
        return self.scaled_value != other.scaled_value

    def __lt__(self, other: OtherTypes | FixedPoint) -> bool:
        r"""Enables `<` syntax"""
        other = self._coerce_other(other)
        if self.is_nan() or other.is_nan():  # nan can't be compared
            return False
        if self.is_inf() and other.is_inf():
            return self.sign() < other.sign()
        if self.is_inf():  # other is finite
            return self.sign() < FixedPoint(0)
        if other.is_inf():  # self is finite
            return other.sign() > FixedPoint(0)
        # both are finite
        return self.scaled_value < other.scaled_value

    def __le__(self, other: OtherTypes | FixedPoint) -> bool:
        r"""Enables `<=` syntax"""
        other = self._coerce_other(other)
        if self.is_nan() or other.is_nan():  # nan can't be compared
            return False
        if self.is_inf() and other.is_inf():
            return self.sign() <= other.sign()
        if self.is_inf():  # other is finite
            return self.sign() < FixedPoint(0)
        if other.is_inf():  # self is finite
            return other.sign() > FixedPoint(0)
        # both are finite
        return self.scaled_value <= other.scaled_value

    def __gt__(self, other: OtherTypes | FixedPoint) -> bool:
        r"""Enables `>` syntax"""
        other = self._coerce_other(other)
        if self.is_nan() or other.is_nan():  # nan can't be compared
            return False
        if self.is_inf() and other.is_inf():
            return self.sign() > other.sign()
        if self.is_inf():  # other is finite
            return self.sign() > FixedPoint(0)
        if other.is_inf():  # self is finite
            return other.sign() < FixedPoint(0)
        # both are finite
        return self.scaled_value > other.scaled_value

    def __ge__(self, other: OtherTypes | FixedPoint) -> bool:
        r"""Enables `>=` syntax"""
        other = self._coerce_other(other)
        if self.is_nan() or other.is_nan():  # nan can't be compared
            return False
        if self.is_inf() and other.is_inf():
            return self.sign() >= other.sign()
        if self.is_inf():  # other is finite
            return self.sign() > FixedPoint(0)
        if other.is_inf():  # self is finite
            return other.sign() < FixedPoint(0)
        # both are finite
        return self.scaled_value >= other.scaled_value

    def __trunc__(self) -> FixedPoint:
        r"""Return x with the fractional part removed, leaving the integer part.

        This rounds toward 0: trunc() is equivalent to floor() for positive x, and equivalent to ceil() for negative x.
        """
        if not self.is_finite():
            return self
        integer, _ = str(self).split(".")  # extract the integer part
        return FixedPoint(integer + ".0")

    def __floor__(self) -> FixedPoint:
        r"""Returns an integer rounded following Python `math.floor` behavior

        Given a real number x, return as output the greatest integer less than or equal to x.
        """
        if not self.is_finite():
            return self
        integer, remainder = str(self).split(".")
        # if the number is negative & there is a remainder
        if self.scaled_value < 0 < len(remainder.rstrip("0")):
            return FixedPoint(str(int(integer) - 1) + ".0")  # round down to -inf
        return FixedPoint(integer + ".0")

    def __ceil__(self) -> FixedPoint:
        r"""Returns an integer rounded following Python `math.ceil` behavior

        Given a real number x, return as output the smallest integer greater than or equal to x.
        """
        if not self.is_finite():
            return self
        integer, remainder = str(self).split(".")
        # if there is a remainder
        if len(remainder.rstrip("0")) > 0:
            if 0 > self.scaled_value:  # the number is negative
                return FixedPoint(integer + ".0")  # truncating decimal rounds towards zero
            if 0 < self.scaled_value:  # the number is positive
                return FixedPoint(str(int(integer) + 1) + ".0")  # increase integer component by one
        return FixedPoint(integer + ".0")  # the number has no remainder

    def __round__(self, ndigits: int = 0) -> FixedPoint:
        r"""Returns a number rounded following Python `round` behavior.

        Given a real number x and an optional integer ndigits, return as output the number
        rounded to the closest multiple of 10 to the power -ndigits. If ndigits is omitted, it
        defaults to 0 (round to nearest integer).
        Uses Python's "round half to even" strategy, which is the default for the built-in round function.
        """
        if not self.is_finite():
            return self
        integer, remainder = str(self).split(".")  # lhs = integer part, rhs = fractional part
        if ndigits >= len(remainder):
            # If ndigits is larger than the number of decimal places, return the number itself.
            return self
        # Check the digit at the nth decimal place
        digit = int(remainder[ndigits])
        if ndigits == 0 or len(remainder) < ndigits:
            left_digit = int(integer[-1])
        else:
            left_digit = int(remainder[ndigits - 1])
        # If these conditions are met, we should round down
        if digit < 5 or (  # digit less than 5 OR
            digit == 5  # digit is exactly 5 AND
            and all(d == "0" for d in remainder[ndigits + 1 :])  # all of the following digits are zero AND
            and (left_digit % 2 == 0)  # the digit to the left is even
        ):
            # Take the integer part and the decimals up to (but not including) the nth place as is
            rounded = integer + remainder[:ndigits]
        else:
            # Round up by adding one to the integer obtained by truncating at the nth place
            # Take care to handle negative numbers correctly
            if self.scaled_value >= 0:
                rounded = str(int(integer + remainder[:ndigits]) + 1)
            else:
                rounded = str(int(integer + remainder[:ndigits]) - 1)
        # Append the decimal point and additional zeros, if necessary.
        if ndigits > 0:
            return FixedPoint(rounded[: len(integer)] + "." + rounded[len(integer) :].ljust(ndigits, "0"))
        return FixedPoint(rounded + ".0")

    # type casting
    def __int__(self) -> int:
        r"""Cast to int"""
        if self.special_value is not None:
            raise ValueError(f"cannot convert FixedPoint {self.special_value} to integer")
        return int(self.scaled_value // 10**self.decimal_places)

    def __float__(self) -> float:
        r"""Cast to float"""
        if self.special_value is not None:
            return float(self.special_value)
        return float(self.scaled_value) / 10**self.decimal_places

    def __bool__(self) -> bool:
        r"""Cast to bool"""
        if self.is_finite() and self != FixedPoint(0):
            return True
        return False

    def __str__(self) -> str:
        r"""Cast to str"""
        if self.special_value is not None:
            return self.special_value
        integer = str(self.scaled_value)[:-18]  # remove right-most 18 digits for whole number
        if len(integer) == 0 or integer == "-":  # float(input) was <0
            sign = "-" if self.scaled_value < 0 else ""
            integer = sign + "0"
            scale = len(str(self.scaled_value))
            if self.scaled_value < 0:
                scale -= 1  # ignore negative sign
            num_left_zeros = self.decimal_places - scale
            remainder = "0" * num_left_zeros + str(abs(self.scaled_value))
        else:  # float(input) was >=0
            remainder = str(self.scaled_value)[len(integer) :]  # should be 18 left
        # remove trailing zeros
        if len(remainder.rstrip("0")) == 0:  # all zeros
            remainder = "0"
        else:
            remainder = remainder.rstrip("0")
        return integer + "." + remainder

    def __repr__(self) -> str:
        r"""Returns executable string representation

        For example: "FixedPoint("1234.0")"
        """
        if self.special_value is not None:
            return f'{self.__class__.__name__}("{self.special_value}")'
        return f'{self.__class__.__name__}("{str(self)}")'

    def __hash__(self) -> int:
        r"""Returns a hash of self"""
        # act like a float for non-finite
        if not self.is_finite():
            return hash((float(copy.deepcopy(self)), self.__class__.__name__))
        # act like an integer otherwise
        return hash((copy.deepcopy(self).scaled_value, self.__class__.__name__))

    # additional arethmitic & helper functions
    def div_up(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Divide self by other, rounding up"""
        other = self._coerce_other(other)
        if other <= FixedPoint("0.0"):
            raise errors.DivisionByZero
        return FixedPoint(
            scaled_value=FixedPointIntegerMath.div_up(self.scaled_value, other.scaled_value),
            decimal_places=self.decimal_places,
            signed=self.signed,
        )

    def mul_up(self, other: OtherTypes | FixedPoint) -> FixedPoint:
        r"""Multiply self by other, rounding up"""
        other = self._coerce_other(other)
        if self == FixedPoint("0.0") or other == FixedPoint("0.0"):
            return FixedPoint("0.0")
        return FixedPoint(
            scaled_value=FixedPointIntegerMath.mul_up(self.scaled_value, other.scaled_value),
            decimal_places=self.decimal_places,
            signed=self.signed,
        )

    def is_nan(self) -> bool:
        r"""Return True if self is not a number (NaN)."""
        if self.special_value is not None and self.special_value == "nan":
            return True
        return False

    def is_inf(self) -> bool:
        r"""Return True if self is inf or -inf."""
        if self.special_value is not None and "inf" in self.special_value:
            return True
        return False

    def is_zero(self) -> bool:
        r"""Return True if self is zero, and False is self is non-zero or non-finite"""
        if not self.is_finite():
            return False
        return self.scaled_value == 0

    def is_finite(self) -> bool:
        r"""Return True if self is finite, that is not inf, -inf, or nan"""
        return not (self.is_nan() or self.is_inf())

    def sign(self) -> FixedPoint:
        r"""Return the sign of self if self is finite, inf, or -inf; otherwise return nan"""
        if self.special_value == "nan":
            return FixedPoint("nan")
        if self == FixedPoint("0.0"):
            return self
        if "-" in str(self):
            return FixedPoint("-1.0")
        return FixedPoint("1.0")

    def floor(self) -> FixedPoint:
        r"""Calls the `__floor__` function"""
        return self.__floor__()  # pylint: disable=unnecessary-dunder-call

    def ceil(self) -> FixedPoint:
        r"""Calls the `__ceil__` function"""
        return self.__ceil__()  # pylint: disable=unnecessary-dunder-call

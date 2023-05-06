"""Fixed point datatype & arithmetic"""
from __future__ import annotations

import copy
from typing import TypeVar, Union

import elfpy.errors.errors as errors

# we will use single letter names for the FixedPointMath class since all functions do basic arithmetic
# pylint: disable=invalid-name


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
        return FixedPoint(FixedPointMath.add(self.int_value, other.int_value), self.decimal_places, self.signed)

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
        return FixedPoint(FixedPointMath.sub(self.int_value, other.int_value), self.decimal_places, self.signed)

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
        return FixedPoint(FixedPointMath.sub(other.int_value, self.int_value), self.decimal_places, self.signed)

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
        return FixedPoint(FixedPointMath.mul_down(self.int_value, other.int_value), self.decimal_places, self.signed)

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
        return FixedPoint(FixedPointMath.div_down(self.int_value, other.int_value), self.decimal_places, self.signed)

    def __pow__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables '**' syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if self.is_finite() and other.is_finite():
            return FixedPoint(FixedPointMath.pow(self.int_value, other.int_value), self.decimal_places, self.signed)
        # pow is tricky -- leaning on float operations under the hood for non-finite
        return FixedPoint(str(float(self) ** float(other)))

    def __rpow__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables reciprocal pow to support other ** FixedPoint"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        return FixedPoint(FixedPointMath.pow(self.int_value, other.int_value), self.decimal_places, self.signed)

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
        if self.is_finite() and self == FixedPoint(0):
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
        return FixedPoint(FixedPointMath.div_up(self.int_value, other.int_value), self.decimal_places, self.signed)

    def mul_up(self, other: int | FixedPoint) -> FixedPoint:
        """Multiply self by other, rounding up"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if self == FixedPoint("0.0") or other == FixedPoint("0.0"):
            return FixedPoint("0.0")
        return FixedPoint(FixedPointMath.mul_up(self.int_value, other.int_value), self.decimal_places, self.signed)

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


NUMERIC = TypeVar("NUMERIC", FixedPoint, int, float)


class FixedPointMath:
    """Safe, high precision (1e18) fixed-point integer arethmetic"""

    # int has no max size in python 3. Use 256 since that is max for solidity.
    INT_MAX = 2**255 - 1
    INT_MIN = -(2**255)
    UINT_MAX = 2**256 - 1
    UINT_MIN = 0
    EXP_MAX = 135305999368893231589  # floor(log((2**255 -1) / 1e18) * 1e18)
    EXP_MIN = -42139678854452767622  # floor(log(0.5e-18)*1e18)
    ONE_18 = 1 * 10**18

    @staticmethod
    def add(a: int, b: int) -> int:
        """Add two fixed-point numbers in 1e18 format."""
        c = a + b
        # Solidity has this: `if c < a or a > FixedPointMath.INT_MAX - b`
        # However, we allow negative values sometimes, which trips up that check.
        # Python 3 also won't actually overflow if we go over INT_MAX, so we can just check:
        if c > FixedPointMath.INT_MAX:
            raise OverflowError(f"add: sum cannot be greater than {FixedPointMath.INT_MAX=}")
        return c

    @staticmethod
    def sub(a: int, b: int) -> int:
        """Subtract two fixed-point numbers in 1e18 format."""
        c = a - b
        # solidity has this: `if b > a`
        # However, we are encoding our own INT_MIN, since python 3 `int` has no min/max
        if c < FixedPointMath.INT_MIN:
            raise OverflowError(f"sub: difference cannot be less than {FixedPointMath.INT_MIN=}")
        return c

    @staticmethod
    def mul_div_down(x: int, y: int, d: int) -> int:
        """Multiply x and y, then divide by d, rounding down."""
        z = x * y
        # don't want to divide by zero; product overflow will cause (x * y) / x != y
        require = d != 0 and (x == 0 or z // x == y)
        if not require:
            raise ValueError("mul_div_down: invalid input")
        if z // d == 0:
            return 0
        # floor div automatically rounds down
        return z // d

    @staticmethod
    def mul_down(a: int, b: int) -> int:
        """Multiply two fixed-point numbers in 1e18 format and round down."""
        return FixedPointMath.mul_div_down(a, b, FixedPointMath.ONE_18)

    @staticmethod
    def div_down(a: int, b: int) -> int:
        """Divide two fixed-point numbers in 1e18 format and round down."""
        return FixedPointMath.mul_div_down(a, FixedPointMath.ONE_18, b)

    @staticmethod
    def mul_div_up(x: int, y: int, d: int) -> int:
        """Multiply x and y, then divide by d, rounding up."""
        z = x * y
        # don't want to divide by zero; product overflow will cause (x * y) / x != y
        require = d != 0 and (x == 0 or z // x == y)
        if not require:
            raise ValueError("mul_div_up: invalid input")
        # if product is zero, just return zero; this avoids z-1 underflow
        # else, first, divide z - 1 by the d and add 1, which rounds up
        if z == 0:
            return int(0)
        # divide z - 1 by d and add 1, allowing z - 1 to underflow if z is 0
        return ((z - 1) // d) + 1

    @staticmethod
    def mul_up(a: int, b: int) -> int:
        """Multiply a and b, rounding up."""
        return FixedPointMath.mul_div_up(a, b, FixedPointMath.ONE_18)

    @staticmethod
    def div_up(a: int, b: int) -> int:
        r"""Divide a by b, rounding up."""
        return FixedPointMath.mul_div_up(a, FixedPointMath.ONE_18, b)

    @staticmethod
    def ilog2(x: int) -> int:
        r"""Returns floor(log2(x)) if x is nonzero, otherwise 0.

        This is the same as the location of the highest set bit.
        """
        if x == 0:
            return type(x)(0)
        return x.bit_length() - 1

    @staticmethod
    def ln(x: int) -> int:
        r"""Computes ln(x) in 1e18 fixed point.

        Reverts if value is negative or 0.
        """
        if x <= 0:
            raise ValueError(f"ln: argument must be positive, not {x}")
        # We want to convert x from `precision` fixed point to 2**96 fixed point.
        # We do this by multiplying by 2**96 / precision.
        # But since ln(x * C) = ln(x) + ln(C), we can simply do nothing here
        # and add ln(2**96 / precision) at the end.
        #
        # Reduce range of x to (1, 2) * 2**96
        # ln(2^k * x) = k * ln(2) + ln(x)
        k = FixedPointMath.ilog2(x) - 96
        x <<= 159 - k
        x >>= 159
        # Evaluate using a (8, 8)-term rational approximation
        # p is made monic, we will multiply by a scale factor later
        p = x + 3273285459638523848632254066296
        p = ((p * x) >> 96) + 24828157081833163892658089445524
        p = ((p * x) >> 96) + 43456485725739037958740375743393
        p = ((p * x) >> 96) - 11111509109440967052023855526967
        p = ((p * x) >> 96) - 45023709667254063763336534515857
        p = ((p * x) >> 96) - 14706773417378608786704636184526
        p = p * x - (795164235651350426258249787498 << 96)
        # We leave p in 2**192 basis so we don't need to scale it back up for the division.
        # q is monic by convention
        q = x + 5573035233440673466300451813936
        q = ((q * x) >> 96) + 71694874799317883764090561454958
        q = ((q * x) >> 96) + 283447036172924575727196451306956
        q = ((q * x) >> 96) + 401686690394027663651624208769553
        q = ((q * x) >> 96) + 204048457590392012362485061816622
        q = ((q * x) >> 96) + 31853899698501571402653359427138
        q = ((q * x) >> 96) + 909429971244387300277376558375
        # r is in the range (0, 0.125) * 2**96
        # r is computed using floor division;
        # future versions could use the remainder, p % q, to increase precision
        r = p // q
        # Finalization, we need to
        # * multiply by the scale factor s = 5.549…
        # * add ln(2**96 / 10**18)
        # * add k * ln(2)
        # * multiply by 10**18 / 2**96 = 5**18 >> 78
        # mul s * 5e18 * 2**96, base is now 5**18 * 2**192
        r *= 1677202110996718588342820967067443963516166
        # add ln(2) * k * 5e18 * 2**192
        r += 16597577552685614221487285958193947469193820559219878177908093499208371 * k
        # add ln(2**96 / 10**18) * 5e18 * 2**192
        r += 600920179829731861736702779321621459595472258049074101567377883020018308
        # base conversion: mul 2**18 / 2**192
        r >>= 174
        return r

    @staticmethod
    def exp(x: int) -> int:
        r"""Perform a high-precision exponential operator on a fixed-point integer with 1e18 precision"""
        # Input x is in fixed point format, with scale factor 1/1e18.
        # When the result is < 0.5 we return zero. This happens when
        # x <= floor(log(0.5e-18) * 1e18) ~ -42e18
        if x <= FixedPointMath.EXP_MIN:
            return 0
        # When the result is > (2**255 - 1) / 1e18 we can not represent it
        # as an int256. This happens when x >= floor(log((2**255 -1) / 1e18) * 1e18) ~ 135.
        if x >= FixedPointMath.EXP_MAX:
            raise ValueError(f"exp: exponent={x} must be less than {FixedPointMath.EXP_MAX=}")
        # x is now in the range (-42, 136) * 1e18, inclusive.
        # Convert to (-42, 136) * 2**96 for more intermediate
        # precision and a binary basis. This base conversion
        # is a multiplication by 1e18 / 2**96 = 5**18 / 2**78.
        x = (x << 78) // (5**18)
        # Reduce range of x to (-0.5 * ln 2, 0.5 * ln 2) * 2**96 by factoring out powers of two
        # such that exp(x) = exp(x') * 2**k, where k is an integer.
        # Solving this gives k = round(x / log(2)) and x' = x - k * log(2).
        # k is in the range [-61, 195].
        k = (((x << 96) // 54916777467707473351141471128) + (2**95)) >> 96
        x = x - k * 54916777467707473351141471128
        # Evaluate using a (6, 7)-term rational approximation
        # p is made monic, we will multiply by a scale factor later
        p = x + 2772001395605857295435445496992
        p = ((p * x) >> 96) + 44335888930127919016834873520032
        p = ((p * x) >> 96) + 398888492587501845352592340339721
        p = ((p * x) >> 96) + 1993839819670624470859228494792842
        p = p * x + (4385272521454847904659076985693276 << 96)
        # We leave p in 2**192 basis so we don't need to scale it back up for the division.
        # Evaluate using using Knuth's scheme from p. 491.
        z = x + 750530180792738023273180420736
        z = ((z * x) >> 96) + 32788456221302202726307501949080
        w = x - 2218138959503481824038194425854
        w = ((w * z) >> 96) + 892943633302991980437332862907700
        q = z + w - 78174809823045304726920794422040
        q = ((q * w) >> 96) + 4203224763890128580604056984195872
        # r should be in the range (0.09, 0.25) * 2**96.
        # r is computed using floor division;
        # future versions could use the remainder, p % q, to increase precision
        r = p // q
        # We now need to multiply r by
        #  * the scale factor s = ~6.031367120...,
        #  * the 2**k factor from the range reduction, and
        #  * the 1e18 / 2**96 factor for base conversion.
        # We do all of this at once, with an intermediate result in 2**213 basis
        # so the final right shift is always by a positive amount.
        return (r * 3822833074963236453042738258902158003155416615667) >> (195 - k)

    @staticmethod
    def pow(x: int, y: int) -> int:
        r"""Using logarithms we calculate x ** y

        .. math::
            \begin{align*}
                &ln(x^y) = y * ln(x)\\
                &ln(x^y) = y * ln(x) / 1 * 10 ** 18 \\
                &e^{(y * ln(y))} = x^y
            \end{align*}

        Any overflow for x will be caught in ln() in the initial bounds check
        """
        if x == 0:
            if y == 0:
                return FixedPointMath.ONE_18
            return 0
        ylnx = y * FixedPointMath.ln(x) // FixedPointMath.ONE_18
        return FixedPointMath.exp(ylnx)

    @staticmethod
    def maximum(x: NUMERIC, y: NUMERIC) -> NUMERIC:
        """Compare the two inputs and return the greater value.

        If the first argument equals the second, return the first.
        """
        if x >= y:
            return x
        return y

    @staticmethod
    def minimum(x: NUMERIC, y: NUMERIC) -> NUMERIC:
        """Compare the two inputs and return the lesser value.

        If the first argument equals the second, return the first.
        """
        if x <= y:
            return x
        return y

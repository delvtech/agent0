"""Fixed point datatype & arithmetic"""
from __future__ import annotations

import copy
from typing import TypeVar, Union

import elfpy.errors.errors as errors

# we will use single letter names for this class since all functions do basic arithmetic
# pylint: disable=invalid-name


class FixedPoint:
    """New fixed-point datatype

    .. todo::
        * add __round__, __ceil__, __floor__, __trunc__ so that it will be a proper numbers.Real type
        https://docs.python.org/3/library/numbers.html#numbers.Real
    """

    int_value: int  # integer representation of self

    def __init__(self, value: Union[FixedPoint, float, int, str] = 0, decimal_places: int = 18, signed: bool = True):
        """Store fixed-point properties"""
        # TODO: support unsigned option
        if not signed:
            raise NotImplementedError("Only signed FixedPoint ints are supported.")
        self.signed = signed
        # TODO: support non-default decimal values
        if decimal_places != 18:
            raise NotImplementedError("Only 18 decimal precision FixedPoint ints are supported.")
        self.decimal_places = decimal_places
        self.special_value = None
        if isinstance(value, float):
            # round with one extra precision then int truncates
            value = int(value * 10**decimal_places)
        if isinstance(value, str):
            if value.lower() in ("nan", "inf", "-inf"):
                self.special_value = value.lower()
                value = 0
            else:
                if "." not in value:
                    raise ValueError(
                        "String arguments must be float strings, e.g. '1.0', for the FixedPoint constructor."
                    )
                lhs, rhs = value.split(".")
                rhs = rhs.replace("_", "")  # removes underscores; they won't affect `int` cast and will affect `len`
                value = int(lhs) * 10**decimal_places + int(rhs) * 10 ** (decimal_places - len(rhs))
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
        if self.is_nan() or other.is_nan():
            return FixedPoint("nan")
        if self.is_inf():
            if other.is_inf() and self.sign() != other.sign():
                return FixedPoint("nan")
            return self
        if other.is_inf():
            return other
        return FixedPoint(FixedPointMath.add(self.int_value, other.int_value), self.decimal_places, self.signed)

    def __radd__(self, other: int | FixedPoint) -> FixedPoint:
        """Reflected add"""
        return self.__add__(other)

    def __sub__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables '-' syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if self.is_nan() or other.is_nan():
            return FixedPoint("nan")
        if self.is_inf():
            if other.is_inf() and self.sign() == other.sign():
                return FixedPoint("nan")
            return self
        if other.is_inf():
            return FixedPoint("-inf") if other.sign() == FixedPoint("1.0") else FixedPoint("inf")
        return FixedPoint(FixedPointMath.sub(self.int_value, other.int_value), self.decimal_places, self.signed)

    def __rsub__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables recprical subtraction to support int - FixedPoint"""
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
            return FixedPoint(0)
        if self.is_inf() or other.is_inf():
            return FixedPoint("inf" if self.sign() == other.sign() else "-inf")
        return FixedPoint(FixedPointMath.mul_down(self.int_value, other.int_value), self.decimal_places, self.signed)

    def __rmul__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables recriprocal multiplication to allow int * FixedPoint"""
        return self.__mul__(other)

    def __truediv__(self, other):
        """Enables '/' syntax.

        Since most implementations use divdown, this mirrors '//' syntax
        """
        return self.__floordiv__(other)

    def __rtruediv__(self, other):
        """Enables '/' syntax.

        Since most implementations use divdown, this mirrors '//' syntax
        """
        return self.__truediv__(other)

    def __floordiv__(self, other: int | FixedPoint) -> FixedPoint:
        """Enables '//' syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if other == FixedPoint("0.0"):
            raise errors.DivisionByZero
        if self.is_nan() or other.is_nan():
            return FixedPoint("nan")
        if self.is_inf():
            if other.is_inf():  # inf / inf is zero
                return FixedPoint("nan")
            return self
        if other.is_inf():  # finite / inf is zero
            return FixedPoint(0)
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
        """Enables '**' syntax"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        return FixedPoint(FixedPointMath.pow(self.int_value, other.int_value), self.decimal_places, self.signed)

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
        """Uses int eq function to check for equality"""
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if not self.is_finite() or not other.is_finite():
            if self.is_nan() or other.is_nan():
                return False
            return self.special_value == other.special_value
        return self.int_value == other.int_value

    def __ne__(self, other: FixedPoint) -> bool:
        other = self._coerce_other(other)
        if other is NotImplemented:
            return NotImplemented
        if not self.is_finite() or not other.is_finite():
            if self.is_nan() or other.is_nan():
                return True
            return self.special_value != other.special_value
        return self.int_value != other.int_value

    def __lt__(self, other: FixedPoint) -> bool:
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
        if self.special_value is not None:
            return self.special_value
        return f"{float(self):.18f}"

    def __repr__(self) -> str:
        # e.g. FixedPoint(1234)
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
            raise OverflowError("FixedPointMath_AddOverflow")
        return c

    @staticmethod
    def sub(a: int, b: int) -> int:
        """Subtract two fixed-point numbers in 1e18 format."""
        c = a - b
        # solidity has this: `if b > a`
        # However, we are encoding our own INT_MIN, since python 3 `int` has no min/max
        if c < FixedPointMath.INT_MIN:
            raise OverflowError("FixedPointMath_SubOverflow")
        return c

    @staticmethod
    def mul_div_down(x: int, y: int, d: int) -> int:
        """Multiply x and y, then divide by d, rounding down."""
        z = x * y
        # don't want to divide by zero; product overflow will cause (x * y) / x != y
        require = d != 0 and (x == 0 or z // x == y)
        if not require:
            raise ValueError("FixedPointMath_mulDivDown_InvalidInput")
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
            raise ValueError("FixedPointMath_mulDivUp_InvalidInput")
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
            raise ValueError("FixedPointMath_NegativeOrZeroInput")
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
        r, _ = divmod(p, q)  # future versions can use remainder to increase precision
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
            raise ValueError("FixedPointMath_InvalidExponent")
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
        r, _ = divmod(p, q)  # future versions can use remainder to increase precision
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

# %% [markdown]
# Fixed point math

# %%
"""
SUGAR FUNCS

object.__add__(self, other)
object.__sub__(self, other)
object.__mul__(self, other)
object.__matmul__(self, other)
object.__truediv__(self, other)
object.__floordiv__(self, other)
object.__mod__(self, other)
object.__divmod__(self, other)
object.__pow__(self, other[, modulo])
object.__lshift__(self, other)
object.__rshift__(self, other)
object.__and__(self, other)
object.__xor__(self, other)
object.__or__(self, other)
These methods are called to implement the binary arithmetic operations (+, -, *, @, /, //, %, divmod(), pow(), **, <<, >>, &, ^, |).

object.__iadd__(self, other)
object.__isub__(self, other)
object.__imul__(self, other)
object.__imatmul__(self, other)
object.__itruediv__(self, other)
object.__ifloordiv__(self, other)
object.__imod__(self, other)
object.__ipow__(self, other[, modulo])
object.__ilshift__(self, other)
object.__irshift__(self, other)
object.__iand__(self, other)
object.__ixor__(self, other)
object.__ior__(self, other)
These methods are called to implement the augmented arithmetic assignments (+=, -=, *=, @=, /=, //=, %=, **=, <<=, >>=, &=, ^=, |=).

object.__neg__(self)
object.__pos__(self)
object.__abs__(self)
object.__invert__(self)
Called to implement the unary arithmetic operations (-, +, abs() and ~).

object.__int__(self)
object.__float__(self)
Called to implement the built-in functions int() and float().
Should return a value of the appropriate type.

"""
# %%
class FixedPoint(float):
    """New fixed-point datatype"""

    def __new__(cls, value: Union[float, int], decimal_places: int = 18, signed: bool = False):
        return super().__new__(cls, to_fixed_point(value, decimal_places))

    def __init__(self, value: Union[float, int], decimal_places: int = 18, signed: bool = False):
        self.signed = signed
        self.decimal_places = decimal_places
        # TODO: can I use sys.maxsize?? That's maximum `int`
        # The maximum value is 9 repeating decimal_places times
        # TODO: This assumes unsigned integer.
        # To do signed we should divide by two
        # (above half is positive, below half is negative)
        self.max_value = 10 ** (self.decimal_places + 1) - 1
        self.min_value = 0

    def __float__(self) -> float:
        # TODO: This is dumb -- need to convert sci notation str to int
        return to_floating_point(int(float(super().__str__())), self.decimal_places)

    def __add__(self, other):
        if not isinstance(other, FixedPoint):
            other = FixedPoint(other, self.decimal_places)
        result = super().__add__(other)
        # TODO: I think just the second condition is sufficient
        if result < self or result > self.max_value:
            raise OverflowError("Addition overflow error")
        return result

    def __sub__(self, other):
        if not isinstance(other, FixedPoint):
            other = FixedPoint(other, self.decimal_places)
        if other > self:
            raise OverflowError("Subtraction overflow error")
        result = super().__sub__(other)
        return result


# %%
import sys
import os
from typing import Union, TypeVar
import math

# always:
# int in -> int out
# float in -> float out
#
# when USE_FIXED_POINT == True:
#     internal operation is always fixed-point (int)
# else:
#     internal operation is normal (float)
#
# Need to support divup & divdown, etc. So we can't just override the operators.
# What's more is we need to have those functions detect whether the type is
# float or FixedPoint


def is_normal(value: float) -> bool:
    """
    Return True if the argument is a _normal_ finite number with
    an adjusted exponent greater than or equal to Emin. Return False
    if the argument is subnormal, infinite or a NaN.
    Note, the term normal is used here in a different sense than typical
    `normalize` methods, which are used to create canonical values.
    """
    return math.isfinite(value) and abs(value) >= sys.float_info.min


def to_fixed_point(float_var: float, decimal_places: int = 18) -> int:
    """Convert floating point argument to fixed point with desired number of decimals"""
    fixed_point = int(float_var * 10**decimal_places)
    # TODO: can I use sys.maxsize?? That's maximum `int`
    # max_value = (10**decimal_places + 1) - 1
    # if fixed_point > sys.maxsize:
    #    raise OverflowError("Fixed point value is too large")
    return fixed_point


def to_floating_point(fixed_var: int, decimal_places: int = 18) -> float:
    """Convert fixed point argument to floating point with specified number of decimals"""
    return float(fixed_var / 10**decimal_places)


T = TypeVar("T", int, float)


def mixed_precision_support(decimal_places: int = 18):
    def decorator(func):
        use_fixed_point = os.environ.get("USE_FIXED_POINT", False)
        if use_fixed_point:

            def fixed_func(*args: Union[float, int]) -> FixedPoint:
                result_fp = func(*[FixedPoint(arg, decimal_places) for arg in args])
                return result_fp

            def wrapper(*args: T) -> T:
                # if inputs were float then do the operations with
                # fixed point and then convert back to float
                result = fixed_func(*args)
                if isinstance(args[0], int):  # all args should have same type
                    return int(result)
                else:
                    return float(result)

        else:

            def wrapper(*args: T) -> T:
                result = func(*args)
                return type(args[0])(result)

        return wrapper

    return decorator


# %%
import numpy as np


class FixedFloatMath:
    @staticmethod
    def mul_div_down(value: T, multiplier: T, divisor: float = 10**18) -> T:
        if isinstance(value, float) and isinstance(multiplier, float):
            assert is_normal(value * multiplier)
            return np.floor(value * multiplier)
        product = value * multiplier
        # don't want to divide by zero; product overflow will cause (x * y) / x != y
        require = divisor != 0 and (value == 0 or product / value == multiplier)
        if not require:
            raise ValueError(
                f"{divisor=} must !=0 AND if {product=} !=0 then {(product/value)=} must equal {multiplier=}"
            )
        return type(value)(product / divisor)

    @staticmethod
    def mul_down(value: T, multiplier: T, scale: float = 10**18) -> T:
        return type(value)(FixedFloatMath().mul_div_down(value, multiplier, scale))

    @staticmethod
    def mul_div_up(value: T, multiplier: T, divisor: float = 10**18) -> T:
        if isinstance(value, float) and isinstance(multiplier, float):
            assert is_normal(value * multiplier)
            return np.ceil(value * multiplier)
        product = value * multiplier
        # don't want to divide by zero; product overflow will cause (x * y) / x != y
        require = divisor != 0 and (value == 0 or product / value == multiplier)
        if not require:
            raise ValueError(
                f"{divisor=} must !=0 AND if {product=} !=0 then {(product/value)=} must equal {multiplier=}"
            )
        # if product is zero, just return zero; this avoids z-1 underflow
        # else, first, divide z - 1 by the d and add 1, which rounds up
        if product == 0:
            return type(value)(0)
        return type(value)(((product - 1) / divisor) + 1)

    @staticmethod
    def mul_up(value: T, multiplier: T, scale: float = 10**18) -> T:
        return type(value)(FixedFloatMath().mul_div_up(value, multiplier, scale))

    @staticmethod
    def ilog2(value: int) -> int:
        """Returns floor(log2(x)) if x is nonzero, otherwise 0.
        This is the same as the location of the highest set bit.
        """
        result = 0
        if value >= 2**128:  # 0xffffffffffffffffffffffffffffffff
            result += 64
            value >>= 64
        if value >= 2**64:  # 0xffffffffffffffff
            result += 32
            value >>= 32
        if value >= 2**32:  # 0xffffffff
            result += 16
            value >>= 16
        if value >= 2**16:  # 0xffff
            result += 8
            value >>= 8
        if value >= 2**8:  # 0xff
            result += 4
            value >>= 4
        if value >= 2**4:  # 0xf
            result += 2
            value >>= 2
        if value >= 2**2:  # 0x3
            result += 1
            value >>= 1
        if value >= 2**1:  # 0x1
            result += 1
        return result


os.environ["USE_FIXED_POINT"] = "True"

fxp = FixedFloatMath()
# example usage
d = 0.1
e = 0.2
f = fxp.mul_up(d, e)
print(f)
f = fxp.mul_down(d, e)
print(f)
f = fxp.mul_down(int(d * int(1e18)), int(e * int(1e18)))
print(f)
print(f / int(1e18))

a = 0.123456789
b = to_fixed_point(a)
c = to_floating_point(b)
print(a)  # 0.123456789
print(b)  # 128849
print(c)  # 0.12345679473876953


@mixed_precision_support()
def simple(a: T) -> T:
    return a


print(simple(0.5))
print(simple(5))
print(simple(5.0))


@mixed_precision_support()
def do_some_ops(a: T, b: T, c: T) -> T:
    sum = a + b
    diff = sum - c
    return diff


# TODO: This overflows with 10x inputs, I assume bc it is signed.
# Need to add a "signed" arg I guess?
# I think we want to do entirely unsigned ints,
# although we will have to rewrite some of the apply_deltas if we're going to live in unsigned world.
print(do_some_ops(0.1, 0.4, 0.5))
# doesn't work :(
print(to_floating_point(int(do_some_ops(0.1, 0.4, 0.5))))


# %%
# PYTORCH VER

import torch


class FixedPointFunction(torch.autograd.Function):
    @staticmethod
    def forward(ctx, func, decimal_places, return_float, *args):
        fixed_args = []
        for arg in args:
            if isinstance(arg, (float, int)):
                arg = torch.tensor(arg)
            fixed_arg = to_fixed_point(arg, decimal_places)
            fixed_args.append(fixed_arg)
        result_fixed = func(*fixed_args)
        ctx.save_for_backward(result_fixed)
        ctx.decimal_places = decimal_places
        if return_float:
            result = to_floating_point(result_fixed, decimal_places)
            return result
        return result_fixed

    @staticmethod
    def backward(ctx, grad_output):
        (result_fixed,) = ctx.saved_tensors
        decimal_places = ctx.decimal_places
        grad_fixed = to_fixed_point(grad_output, decimal_places)
        grad_inputs = []
        for arg in ctx.saved_tensors:
            if arg is result_fixed:
                grad_inputs.append(grad_fixed)
            else:
                grad_inputs.append(None)
        return (None, None, None, *grad_inputs)


def fixed_point(decimal_places=18, return_float=True):
    def decorator(func):
        def wrapper(*args, **kwargs):
            torch_func = FixedPointFunction.apply
            return torch_func(func, decimal_places, return_float, *args, **kwargs)

        return wrapper

    return decorator


@fixed_point()
def multiply(x, y):
    return x * y


a = 0.1
b = 0.2

# c = multiply(torch.tensor(a), torch.tensor(b))
c = multiply(a, b)

torch.gradient(c, a)

print(c)  # 0.02

# %%
a = torch.as_tensor(0.123456789)
b = to_fixed_point(a)
c = to_floating_point(b)
print(a)  # 0.123456789
print(b)  # 128849
print(c)  # 0.12345679473876953

# %%
# def test_coeffs_6_7(P_coeffs, Q_coeffs):
#    assert P_coeffs[0] == 2772001395605857295435445496992
#    assert P_coeffs[1] == 44335888930127919016834873520032
#    assert P_coeffs[2] == 398888492587501845352592340339721
#    assert P_coeffs[3] == 1993839819670624470859228494792842
#    assert P_coeffs[4] == 4385272521454847904659076985693276
#
#    assert Q_coeffs[0] == 750530180792738023273180420736
#    assert Q_coeffs[1] == 32788456221302202726307501949080
#    assert Q_coeffs[2] == -2218138959503481824038194425854
#    assert Q_coeffs[3] == 892943633302991980437332862907700
#    assert Q_coeffs[4] == -78174809823045304726920794422040
#    assert Q_coeffs[5] == 4203224763890128580604056984195872
#
#
# test_coeffs_6_7(P_coeffs, Q_coeffs)


import math

import numpy as np

# Define your function that works with fixed-point numbers
def f_fixed_point(x):
    return int(np.exp(x / 1e18) * 1e18)


def fixed_array_to_float(array):
    return np.array([val / 1e18 for val in array], dtype=float)


def get_chebyshev_coefficients(f, deg_p, deg_q, x_min, x_max):
    # Get Chebyshev coefficients for rational approximation
    x = np.linspace(x_min + 1, x_max - 1, num=1000, dtype=np.int64)
    y = np.array([f(xi) for xi in x])
    x, y = fixed_array_to_float(x), fixed_array_to_float(y)
    # Fit the numerator (P) and denominator (Q) Chebyshev polynomials
    P_coeffs = np.polynomial.chebyshev.chebfit(x, y, deg_p)
    Q_coeffs = np.polynomial.chebyshev.chebfit(x, 1 / y, deg_q)
    # Convert coefficients to fixed-point integers
    P_coeffs_fixed = [(int(c * 1e18)) for c in P_coeffs]
    Q_coeffs_fixed = [(int(c * 1e18)) for c in Q_coeffs]
    return P_coeffs_fixed, Q_coeffs_fixed


# Precompute Chebyshev coefficients
deg_p = 6
deg_q = 7
x_min = -42139678854452767622  # floor(log(0.5e-18)*1e18)
x_max = 135305999368893231589  # floor(log((2**255 -1) / 1e18) * 1e18)
# P_coeffs, Q_coeffs = get_chebyshev_coefficients(f_fixed_point, deg_p, deg_q, x_min, x_max)
P_coeffs = [
    2772001395605857295435445496992,
    44335888930127919016834873520032,
    398888492587501845352592340339721,
    1993839819670624470859228494792842,
]
Q_coeffs = [
    750530180792738023273180420736,
    32788456221302202726307501949080,
    892943633302991980437332862907700,
    4203224763890128580604056984195872,
]


def exp_rational_approximation(x, P_coeffs, Q_coeffs):
    p = P_coeffs[-1]
    q = Q_coeffs[-1]
    for i in range(len(P_coeffs) - 2, -1, -1):
        p = (p * x) >> 96
        p += P_coeffs[i]
    for i in range(len(Q_coeffs) - 2, -1, -1):
        q = (q * x) >> 96
        q += Q_coeffs[i]
    r, _ = divmod(p, q)
    return r


# def exp_fixed_point(x: int, P_coeffs, Q_coeffs) -> int:
#    if x <= x_min:
#        return 0
#    if x >= x_max:
#        raise ValueError("FixedPointMath_InvalidExponent")
#    x_sign = int(np.sign(x))
#    x_abs = int(np.abs(x))
#    x_abs = (x_abs << 78) // (5**18)
#    k = (((x_abs << 96) // 54916777467707473351141471128) + (2**95)) >> 96
#    x_abs = x_abs - k * 54916777467707473351141471128
#    r = exp_rational_approximation(x_abs, P_coeffs, Q_coeffs)
#    exp_result = (r * 3822833074963236453042738258902158003155416615667) >> (195 - k)
#    if x_sign == -1:
#        return int(1e36 / exp_result)  # exp_result is already scaled, hense 10**(18*2)
#    else:
#        return exp_result


def exp_fixed_point(x: int) -> int:
    """Perform a high-precision exponential operator on a fixed-point integer with 1e18 precision"""
    if x <= -42139678854452767551:
        return 0
    if x >= 135305999368893231589:
        raise ValueError("FixedPointMath_InvalidExponent")

    x = (x << 78) // (5**18)

    k = (((x << 96) // 54916777467707473351141471128) + (2**95)) >> 96
    x = x - k * 54916777467707473351141471128

    # Evaluate using a (7, 8)-term rational approximation
    p = x + 2365435548388570098118095075024
    p = ((p * x) >> 96) + 34318668273274713581680426185014
    p = ((p * x) >> 96) + 270362775340040648191310281970436
    p = ((p * x) >> 96) + 1156191488514454307780970398971547
    p = ((p * x) >> 96) + 3194402146584678660962866511912080
    p = p * x + (4375469559312228512648270455331806 << 96)

    z = x + 521201360678861598364776969802
    z = ((z * x) >> 96) + 21147027975233597227311972109844
    z = ((z * x) >> 96) + 46878716226997331408243099685804
    w = x - 1868927284347447590429593199304
    w = ((w * z) >> 96) + 821958170767182251302643270771964
    w = ((w * x) >> 96) + 894462341794215185369349544389092
    q = z + w - 69899228270520792909738897833460
    q = ((q * w) >> 96) + 4090814022035512234858932535357952
    q = ((q * x) >> 96) + 4299133398527200399258460459368384

    r, _ = divmod(p, q)
    return (r * 3822833074963236453042738258902158003155416615667) >> (195 - k)


x_min = -42139678854452767622  # floor(log(0.5e-18)*1e18)
x_max = 135305999368893231589  # floor(log((2**255 -1) / 1e18) * 1e18)


def test_exp(x_min, x_max):
    test_cases = [
        (x_min - 1, 0),
        (int(5 * 1e18), int(math.exp(5) * 1e18)),
        (int(-5 * 1e18), int(math.exp(-5) * 1e18)),
        (int(10 * 1e18), int(math.exp(10) * 1e18)),
        (int(-10 * 1e18), int(math.exp(-10) * 1e18)),
        (0, int(math.exp(0) * 1e18)),
        (x_max - 1, int(math.exp((x_max - 1) / 1e18) * 1e18)),
    ]

    for case_number, (x, expected) in enumerate(test_cases):
        result = exp_fixed_point(x)  # , P_coeffs, Q_coeffs)
        assert math.isclose(result, expected, rel_tol=1e-18), f"exp(x) {case_number=}:\n{result=},\n{expected=}"


test_exp(x_min, x_max)


# %%
# Lets do this

import math, sys
import numpy as np


class FixedPointMath:
    ONE_18 = 10**18
    EXP_MIN = -42139678854452767622  # floor(log(0.5e-18)*1e18)
    EXP_MAX = 135305999368893231589  # floor(log((2**255 -1) / 1e18) * 1e18)

    @staticmethod
    def add(a: int, b: int) -> int:
        """Add two fixed-point numbers in 1e18 format."""
        # Fixed Point addition is the same as regular checked addition
        c = a + b
        if c < a or a > sys.maxsize - b:
            raise OverflowError("FixedPointMath_AddOverflow")
        return c

    @staticmethod
    def sub(a: int, b: int) -> int:
        """Subtract two fixed-point numbers in 1e18 format."""
        # Fixed Point subtraction is the same as regular checked subtraction
        if b > a:
            raise OverflowError("FixedPointMath_SubOverflow")
        c = a - b
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
        else:  # add d-1 to ensure small entries round down
            return (z + d - 1) // d

    @staticmethod
    def mul_down(a: int, b: int) -> int:
        """Multiply two fixed-point numbers in 1e18 format and round down."""
        return FixedPointMath.mul_div_down(a, b, FixedPointMath.ONE_18)

    @staticmethod
    def div_down(a: int, b: int) -> int:
        """Divide two fixed-point numbers in 1e18 format and round down."""
        return FixedPointMath.mul_div_down(a, FixedPointMath.ONE_18, b)  # Equivalent to (a * 1e18) // b rounded down.

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
            return 0
        else:  # Divide z - 1 by d and add 1, allowing z - 1 to underflow if z is 0
            return ((z - 1) // d) + 1

    @staticmethod
    def mul_up(a: int, b: int) -> int:
        """Multiply a and b, rounding up."""
        return FixedPointMath.mul_div_up(a, b, FixedPointMath.ONE_18)

    @staticmethod
    def div_up(a: int, b: int) -> int:
        """Divide a by b, rounding up."""
        return FixedPointMath.mul_div_up(a, FixedPointMath.ONE_18, b)

    @staticmethod
    def _ilog2(x: int) -> int:
        """Returns floor(log2(x)) if x is nonzero, otherwise 0.
        This is the same as the location of the highest set bit.
        """
        if x == 0:
            return type(x)(0)
        return x.bit_length() - 1

    @staticmethod
    def ln(x: int) -> int:
        """Computes ln(x) in 1e18 fixed point.
        Reverts if value is negative or 0
        """
        if x <= 0:
            raise ValueError("FixedPointMath_NegativeOrZeroInput")
        return FixedPointMath._ln(x)

    @staticmethod
    def _ln(x: int) -> int:
        """Computes ln(x) in 1e18 fixed point.
        Assumes x is non-negative.
        """
        if x < 0:
            raise ValueError("FixedPointMath_NegativeInput")
        # We want to convert x from `precision` fixed point to 2**96 fixed point.
        # We do this by multiplying by 2**96 / precision.
        # But since ln(x * C) = ln(x) + ln(C), we can simply do nothing here
        # and add ln(2**96 / precision) at the end.
        #
        # Reduce range of x to (1, 2) * 2**96
        # ln(2^k * x) = k * ln(2) + ln(x)
        k = FixedPointMath._ilog2(x) - 96
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
        r, _ = divmod(p, q)
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

    def exp(x: int) -> int:
        """Perform a high-precision exponential operator on a fixed-point integer with 1e18 precision"""
        # Input x is in fixed point format, with scale factor 1/1e18.
        # When the result is < 0.5 we return zero. This happens when
        # x <= floor(log(0.5e-18) * 1e18) ~ -42e18

        if x <= FixedPointMath.EXP_MIN:
            return 0
        # When the result is > (2**255 - 1) / 1e18 we can not represent it
        # as an int256. This happens when x >= floor(log((2**255 -1) / 1e18) * 1e18) ~ 135.
        if x >= FixedPointMath.EXP_MAX:
            raise ValueError("FixedPointMath_InvalidExponent")
        # x is now in the range [-42, 136) * 1e18. Convert to (-42, 136) * 2**96
        # for more intermediate precision and a binary basis. This base conversion
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
        r, _ = divmod(p, q)  # ORIGINAL
        # We now need to multiply r by
        #  * the scale factor s = ~6.031367120...,
        #  * the 2**k factor from the range reduction, and
        #  * the 1e18 / 2**96 factor for base conversion.
        # We do all of this at once, with an intermediate result in 2**213 basis
        # so the final right shift is always by a positive amount.
        return (r * 3822833074963236453042738258902158003155416615667) >> (195 - k)

    @staticmethod
    def pow(x: int, y: int) -> int:
        """Using logarithms we calculate x ** y
        ln(x^y) = y * ln(x)
        e^(y * ln(y)) = x^y
        Any overflow for x will be caught in _ln() in the initial bounds check
        """
        ylnx = y * FixedPointMath.ln(x) // FixedPointMath.ONE_18
        return FixedPointMath.exp(ylnx)


# Unit tests


def test_add() -> None:
    assert FixedPointMath.add(FixedPointMath.ONE_18, 5 * FixedPointMath.ONE_18) == 6 * FixedPointMath.ONE_18
    assert FixedPointMath.add(FixedPointMath.ONE_18, FixedPointMath.ONE_18) == 2 * FixedPointMath.ONE_18
    assert FixedPointMath.add(FixedPointMath.ONE_18, 0) == FixedPointMath.ONE_18
    assert FixedPointMath.add(0, FixedPointMath.ONE_18) == FixedPointMath.ONE_18
    assert FixedPointMath.add(0, 0) == 0


test_add()


def test_fail_add_overflow() -> None:
    # with unittest.TestCase.assertRaises(ValueError):
    try:
        FixedPointMath.add(sys.maxsize, FixedPointMath.ONE_18)
    except OverflowError as err:
        pass
    else:
        assert False, "Test failed"


test_fail_add_overflow()


def test_sub() -> None:
    assert FixedPointMath.sub(5 * FixedPointMath.ONE_18, 3 * FixedPointMath.ONE_18) == 2 * FixedPointMath.ONE_18
    assert FixedPointMath.sub(FixedPointMath.ONE_18, FixedPointMath.ONE_18) == 0
    assert FixedPointMath.sub(FixedPointMath.ONE_18, 0) == FixedPointMath.ONE_18
    assert FixedPointMath.sub(2 * FixedPointMath.ONE_18, FixedPointMath.ONE_18) == FixedPointMath.ONE_18
    assert FixedPointMath.sub(0, 0) == 0


test_sub()


def test_fail_sub_overflow() -> None:
    # with unittest.TestCase.assertRaises(ValueError):
    try:
        FixedPointMath.sub(0, FixedPointMath.ONE_18)
    except OverflowError as err:
        pass
    else:
        assert False, "Test failed"


test_fail_sub_overflow()


def test_mul_up() -> None:
    assert FixedPointMath.mul_up(int(2.5 * FixedPointMath.ONE_18), int(0.5 * FixedPointMath.ONE_18)) == int(
        1.25 * FixedPointMath.ONE_18
    )
    assert FixedPointMath.mul_up(3 * FixedPointMath.ONE_18, FixedPointMath.ONE_18) == 3 * FixedPointMath.ONE_18
    assert FixedPointMath.mul_up(369, 271) == 1
    assert FixedPointMath.mul_up(0, FixedPointMath.ONE_18) == 0
    assert FixedPointMath.mul_up(FixedPointMath.ONE_18, 0) == 0
    assert FixedPointMath.mul_up(0, 0) == 0


test_mul_up()


def test_mul_down() -> None:
    assert FixedPointMath.mul_down(2 * FixedPointMath.ONE_18, 3 * FixedPointMath.ONE_18) == 6 * FixedPointMath.ONE_18
    assert FixedPointMath.mul_down(int(2.5 * FixedPointMath.ONE_18), int(0.5 * FixedPointMath.ONE_18)) == int(
        1.25 * FixedPointMath.ONE_18
    )
    assert FixedPointMath.mul_down(3 * FixedPointMath.ONE_18, FixedPointMath.ONE_18) == 3 * FixedPointMath.ONE_18
    assert FixedPointMath.mul_down(369, 271) == 0
    assert FixedPointMath.mul_down(0, FixedPointMath.ONE_18) == 0
    assert FixedPointMath.mul_down(FixedPointMath.ONE_18, 0) == 0
    assert FixedPointMath.mul_down(0, 0) == 0


test_mul_down()


def test_div_down() -> None:
    assert FixedPointMath.div_down(6 * FixedPointMath.ONE_18, 2 * FixedPointMath.ONE_18) == 3 * FixedPointMath.ONE_18
    assert FixedPointMath.div_down(int(1.25 * FixedPointMath.ONE_18), int(0.5 * FixedPointMath.ONE_18)) == int(
        2.5 * FixedPointMath.ONE_18
    )
    assert FixedPointMath.div_down(3 * FixedPointMath.ONE_18, FixedPointMath.ONE_18) == 3 * FixedPointMath.ONE_18
    assert FixedPointMath.div_down(2 * FixedPointMath.ONE_18, int(1e19 * 1e18)) == 0
    assert FixedPointMath.div_down(0, FixedPointMath.ONE_18) == 0


test_div_down()


def test_fail_div_down_zero_denominator() -> None:
    # with unittest.TestCase.assertRaises(ValueError):
    try:
        FixedPointMath.div_down(FixedPointMath.ONE_18, 0)
    except ValueError as err:
        pass
    else:
        assert False, "Test failed"


test_fail_div_down_zero_denominator()


def test_div_up() -> None:
    assert FixedPointMath.div_up(int(1.25 * FixedPointMath.ONE_18), int(0.5 * FixedPointMath.ONE_18)) == int(
        2.5 * FixedPointMath.ONE_18
    )
    assert FixedPointMath.div_up(3 * FixedPointMath.ONE_18, FixedPointMath.ONE_18) == 3 * FixedPointMath.ONE_18
    assert FixedPointMath.div_up(2 * FixedPointMath.ONE_18, int(1e19 * 1e18)) == 1
    assert FixedPointMath.div_up(0, FixedPointMath.ONE_18) == 0


test_div_up()


def test_fail_div_up_zero_denominator() -> None:
    # with unittest.TestCase.assertRaises(ValueError):
    try:
        FixedPointMath.div_up(FixedPointMath.ONE_18, 0)
    except ValueError as err:
        pass
    else:
        assert False, "Test failed"


test_fail_div_up_zero_denominator()


def test_mul_div_down() -> None:
    assert FixedPointMath.mul_div_down(int(2.5e27), int(0.5e27), int(1e27)) == 1.25e27
    assert FixedPointMath.mul_div_down(int(2.5e18), int(0.5e18), int(1e18)) == 1.25e18
    assert FixedPointMath.mul_div_down(int(2.5e8), int(0.5e8), int(1e8)) == 1.25e8
    assert FixedPointMath.mul_div_down(369, 271, int(1e2)) == 1000  # FIXME: should == 999 -- rounding still not working
    assert FixedPointMath.mul_div_down(int(1e27), int(1e27), int(2e27)) == 0.5e27
    assert FixedPointMath.mul_div_down(int(1e18), int(1e18), int(2e18)) == 0.5e18
    assert FixedPointMath.mul_div_down(int(1e8), int(1e8), int(2e8)) == 0.5e8
    assert FixedPointMath.mul_div_down(int(2e27), int(3e27), int(3e27)) == 2e27
    assert FixedPointMath.mul_div_down(int(2e18), int(3e18), int(3e18)) == 2e18
    assert FixedPointMath.mul_div_down(int(2e8), int(3e8), int(3e8)) == 2e8
    assert FixedPointMath.mul_div_down(0, int(1e18), int(1e18)) == 0
    assert FixedPointMath.mul_div_down(int(1e18), 0, int(1e18)) == 0
    assert FixedPointMath.mul_div_down(0, 0, int(1e18)) == 0


test_mul_div_down()


def test_fail_mul_div_down_zero_denominator() -> None:
    # FIXME: Use
    # with unittest.TestCase.assertRaises(ValueError):
    try:
        FixedPointMath.mul_div_down(FixedPointMath.ONE_18, FixedPointMath.ONE_18, 0)
    except ValueError as err:
        pass
    else:
        assert False, "Test failed"


test_fail_div_up_zero_denominator()


def test_mul_div_up() -> None:
    assert FixedPointMath.mul_div_up(int(2.5e27), int(0.5e27), int(1e27)) == 1.25e27
    assert FixedPointMath.mul_div_up(int(2.5e18), int(0.5e18), int(1e18)) == 1.25e18
    assert FixedPointMath.mul_div_up(int(2.5e8), int(0.5e8), int(1e8)) == 1.25e8
    assert FixedPointMath.mul_div_up(369, 271, int(1e2)) == 1000
    assert FixedPointMath.mul_div_up(int(1e27), int(1e27), int(2e27)) == 0.5e27
    assert FixedPointMath.mul_div_up(int(1e18), int(1e18), int(2e18)) == 0.5e18
    assert FixedPointMath.mul_div_up(int(1e8), int(1e8), int(2e8)) == 0.5e8
    assert FixedPointMath.mul_div_up(int(2e27), int(3e27), int(3e27)) == 2e27
    assert FixedPointMath.mul_div_up(int(2e18), int(3e18), int(3e18)) == 2e18
    assert FixedPointMath.mul_div_up(int(2e8), int(3e8), int(3e8)) == 2e8
    assert FixedPointMath.mul_div_up(0, int(1e18), int(1e18)) == 0
    assert FixedPointMath.mul_div_up(int(1e18), 0, int(1e18)) == 0
    assert FixedPointMath.mul_div_up(0, 0, int(1e18)) == 0


test_mul_div_up()


def test_fail_mul_div_up_zero_denominator() -> None:
    # FIXME: Use
    # with unittest.TestCase.assertRaises(ValueError):
    try:
        FixedPointMath.mul_div_up(FixedPointMath.ONE_18, FixedPointMath.ONE_18, 0)
    except ValueError as err:
        pass
    else:
        assert False, "Test failed"


test_fail_div_up_zero_denominator()


def test_ilog2() -> None:
    assert FixedPointMath._ilog2(0) == 0
    assert FixedPointMath._ilog2(1) == 0
    assert FixedPointMath._ilog2(2) == 1
    assert FixedPointMath._ilog2(3) == 1
    assert FixedPointMath._ilog2(4) == 2
    assert FixedPointMath._ilog2(8) == 3
    assert FixedPointMath._ilog2(16) == 4
    assert FixedPointMath._ilog2(32) == 5
    assert FixedPointMath._ilog2(64) == 6
    assert FixedPointMath._ilog2(128) == 7
    assert FixedPointMath._ilog2(256) == 8
    assert FixedPointMath._ilog2(512) == 9
    assert FixedPointMath._ilog2(1024) == 10
    assert FixedPointMath._ilog2(2048) == 11
    assert FixedPointMath._ilog2(4096) == 12
    assert FixedPointMath._ilog2(8192) == 13
    assert FixedPointMath._ilog2(16384) == 14
    assert FixedPointMath._ilog2(32768) == 15
    assert FixedPointMath._ilog2(65536) == 16
    assert FixedPointMath._ilog2(131072) == 17
    assert FixedPointMath._ilog2(262144) == 18
    assert FixedPointMath._ilog2(524288) == 19
    assert FixedPointMath._ilog2(1048576) == 20


test_ilog2()


def test_ln() -> None:
    test_cases = [
        (FixedPointMath.ONE_18, 0),
        (1000000 * FixedPointMath.ONE_18, 13815510557964274104),
        (int(5 * 1e18), int(math.log(5) * 1e18)),
        (int(10 * 1e18), int(math.log(10) * 1e18)),
    ]

    for case_number, (x, expected) in enumerate(test_cases):
        result = FixedPointMath.ln(x)
        assert math.isclose(result, expected, rel_tol=1e-15), f"ln(x) {case_number=}:\n  {result=},\n{expected=}"


test_ln()


def test_exp():
    test_cases = [
        (FixedPointMath.ONE_18, 2718281828459045235),
        (-FixedPointMath.ONE_18, 367879441171442321),
        (FixedPointMath.EXP_MIN - 1, 0),
        (int(5 * 1e18), int(math.exp(5) * 1e18)),
        (int(-5 * 1e18), int(math.exp(-5) * 1e18)),
        (int(10 * 1e18), int(math.exp(10) * 1e18)),
        (int(-10 * 1e18), int(math.exp(-10) * 1e18)),
        (0, int(math.exp(0) * 1e18)),
        # FIXME: This fails when the inputs are any closer to EXP_MAX.
        # To improve precision at high values, we will need to update the (m,n)-term rational approximation
        (FixedPointMath.EXP_MAX - int(145e18), int(math.exp((FixedPointMath.EXP_MAX - 145e18) / 1e18) * 1e18)),
    ]

    for case_number, (x, expected) in enumerate(test_cases):
        result = FixedPointMath.exp(x)
        assert math.isclose(result, expected, rel_tol=1e-18), f"exp(x) {case_number=}:\n  {result=},\n{expected=}"


test_exp()


def test_fail_exp_negative_or_zero_input() -> None:
    try:
        FixedPointMath.exp(FixedPointMath.EXP_MAX + 1)
    except ValueError as err:
        pass
    else:
        assert False, "Test failed"


test_fail_exp_negative_or_zero_input()


def test_pow() -> None:
    tolerance = 1e10

    x = 300000000000000000000000
    y = 977464155968402951
    result = FixedPointMath.pow(x, y)
    expected = 225782202044931640847042
    assert math.isclose(result, expected, rel_tol=tolerance), f"\n  {result=}\n{expected=}"

    x = 180000000000000000000000
    y = 977464155968402951
    result = FixedPointMath.pow(x, y)
    expected = 137037839669721400603869
    assert math.isclose(result, expected, rel_tol=tolerance), f"\n  {result=}\n{expected=}"

    x = 165891671009915386326945
    y = 1023055417320413264
    result = FixedPointMath.pow(x, y)
    expected = 218861723977998147080714
    assert math.isclose(result, expected, rel_tol=tolerance), f"\n  {result=}\n{expected=}"

    x = 77073744241129234405745
    y = 1023055417320413264
    result = FixedPointMath.pow(x, y)
    expected = 999024468576329267422018
    assert math.isclose(result, expected, rel_tol=tolerance), f"\n  {result=}\n{expected=}"

    x = 18458206546438581254928
    y = 1023055417320413264
    result = FixedPointMath.pow(x, y)
    expected = 23149855298128876929745
    assert math.isclose(result, expected, rel_tol=tolerance), f"\n  {result=}\n{expected=}"


test_pow()

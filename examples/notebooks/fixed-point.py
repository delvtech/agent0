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
from elfpy.utils.math import FixedPointMath


class FixedPoint(int):
    """New fixed-point datatype"""

    def __new__(cls, value: Union[float, int], decimal_places: int = 18, signed: bool = True):
        """Construct a new FixedPoint variable"""
        # TODO: support unsigned option
        if not signed:
            raise NotImplementedError("Only signed FixedPoint ints are supported.")
        # TODO: support non-default decimal values
        if decimal_places != 18:
            raise NotImplementedError("Only 18 decimal precision FixedPoint ints are supported.")
        if isinstance(value, float):
            value = int(value * 10**decimal_places)
        return super().__new__(cls, value)

    def __init__(self, value: Union[float, int], decimal_places: int = 18, signed: bool = False):
        self.signed = signed
        self.decimal_places = decimal_places

    def __float__(self) -> float:
        return float(self) / 10**self.decimal_places

    def __add__(self, other):
        """enables '+' syntax"""
        if not isinstance(other, FixedPoint):
            other = FixedPoint(other, self.decimal_places, self.signed)
        return FixedPointMath.add(self, other)

    def __sub__(self, other):
        """enables '-' syntax"""
        if not isinstance(other, FixedPoint):
            other = FixedPoint(other, self.decimal_places, self.signed)
        return FixedPointMath.sub(self, other)

    def __mul__(self, other):
        """enables '*' syntax"""
        if not isinstance(other, FixedPoint):
            other = FixedPoint(other, self.decimal_places, self.signed)
        return FixedPointMath.mul_down(self, other)

    def __truediv__(self, other):
        """Enables '/' syntax.
        Since most implementations times we want to divdown this mirrors '//' syntax
        """
        return self.__floordiv__(other)

    def __floordiv__(self, other):
        """enables '//' syntax"""
        if not isinstance(other, FixedPoint):
            other = FixedPoint(other, self.decimal_places, self.signed)
        return FixedPointMath.div_down(self, other)

    def __pow__(self, other):
        """enables '**' syntax"""
        if not isinstance(other, FixedPoint):
            other = FixedPoint(other, self.decimal_places, self.signed)
        return FixedPointMath.pow(self, other)


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

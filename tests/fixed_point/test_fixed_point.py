"""Tests for the FixedPoint data type"""
import math
import unittest

import elfpy.errors.errors as errors
from elfpy.math import FixedPoint

# pylint: disable=too-many-public-methods


class TestFixedPoint(unittest.TestCase):
    r"""Unit tests to verify that the fixed-point integer implementations are correct.
    The tests assume everything is in 1e18 precision.

    ..note::
        Note that `ln` and `pow` require lower precision.
        Additionally, the approximations used for fixed-point arithmetic
        are less accurate the closer one gets to the maximum bounds.

        One common tripping point is that integer inputs result in different behavior than float.
        So, in Python ints and floats are designed such that `1 == 1.0 # true`.
        But with fixed-point (fp) types, `fp(1) != fp(1.0)`.
        Instead, `fp(1) == 1e-18`, while `fp(1.0) == 1e18`.

    """

    def test_init(self):
        r"""Test initialization for FixedPoint numbers"""
        # str == float
        assert FixedPoint("5") == FixedPoint("5.0")
        assert FixedPoint("50_000.0") == FixedPoint("50000.0")
        assert FixedPoint("50_000.0") == FixedPoint("50000.0")
        assert FixedPoint("5_340_070.0") == FixedPoint("5340070.0")
        assert FixedPoint("-5") == FixedPoint(-5.0)
        assert FixedPoint("5.1") == FixedPoint(5.1)
        assert FixedPoint("5.01") == FixedPoint(5.01)
        assert FixedPoint("5.000001") == FixedPoint(5.000001)
        assert FixedPoint("5.000001000") == FixedPoint(5.000001)
        # int == float
        assert FixedPoint(5) == FixedPoint(5e-18)
        assert FixedPoint(50) == FixedPoint(5e-17)
        # float == int
        assert FixedPoint(5.0) == FixedPoint(5 * 10**18)
        assert FixedPoint(5.3) == FixedPoint(53 * 10**17)
        # NOTE: floats are scaled on construction, ints are not; floats also introduce noise
        assert math.isclose(FixedPoint(1e18), FixedPoint(1 * 10**36), abs_tol=1e-18)
        # NOTE: This is true because, in Python,
        # ints and whole floats are equivalent; i.e. 5 == 5.0.
        assert int(FixedPoint(5)) == 5  # int input directly maps, cast does not rescale
        assert float(FixedPoint(5.0)) == 5.0  # scales up on init, then back down on cast to float
        assert int(FixedPoint(5)) == float(FixedPoint(5.0))

    def test_init_fail(self):
        r"""Test failure mode of FixedPoint initialization"""
        with self.assertRaises(ValueError):
            _ = FixedPoint("inf.")  # no decimal if inf/nan
        with self.assertRaises(ValueError):
            _ = FixedPoint("-nan")  # no - if nan
        with self.assertRaises(ValueError):
            _ = FixedPoint("abc")  # no letters besides (+/-)inf & nan
        with self.assertRaises(ValueError):
            _ = FixedPoint("44.5a")  # no letters next to numbers
        with self.assertRaises(ValueError):
            _ = FixedPoint("4a4.5")  # no letters next to numbers
        with self.assertRaises(ValueError):
            _ = FixedPoint("50_00.0")  # must have 3 digits before or between _
        with self.assertRaises(ValueError):
            _ = FixedPoint("1_50_000.0")  # must have 3 digits before or between _
        with self.assertRaises(ValueError):
            _ = FixedPoint("44.5_4")  # no _ on rhs of decimal
        with self.assertRaises(ValueError):
            _ = FixedPoint(".0")  # needs leading digit
        with self.assertRaises(ValueError):
            _ = FixedPoint("1.")  # needs trailing digit if there is a decimal provided

    def test_int_cast(self):
        r"""Test int casting"""
        assert int(FixedPoint(1)) == 1  # int intput directly maps
        assert int(FixedPoint(1.0)) == 1000000000000000000  # float input is rescaled by 1e18
        assert int(FixedPoint("2.0")) == 2 * 10**18  # 2 * 10**18 is int, and is equal to int(2e18)

    def test_float_cast(self):
        r"""Test float casting"""
        assert float(FixedPoint("1.5")) == 1.5
        assert float(FixedPoint("10.5")) == 10.5
        assert float(FixedPoint("1.05")) == 1.05
        assert float(FixedPoint("1.50")) == 1.5
        assert float(FixedPoint("01.5")) == 1.5
        assert float(FixedPoint("010.050")) == 10.05
        assert float(FixedPoint("-2.1")) == -2.1
        assert float(FixedPoint("-2.159178")) == -2.159178
        assert float(FixedPoint(5)) == 0.000000000000000005
        assert float(FixedPoint(50)) == 0.00000000000000005
        assert float(FixedPoint(500)) == 0.0000000000000005
        assert float(FixedPoint(1)) == 1e-18  # cast FP(small int) back to float should be tiny
        assert float(FixedPoint(1e18)) == 1e18  # even if float is large, casting back stays large
        assert float(FixedPoint(3 * 10**18)) == 3.0  # int in does not get scaled
        assert float(FixedPoint(3.8 * 10**18)) == 3.8e18  # float in gets scaled
        assert float(FixedPoint(4.0)) == 4.0  # cast FP(float) back to float should be equivalent
        assert float(FixedPoint(1.5)) == 1.5

    def test_str_cast(self):
        r"""Test str casting"""
        assert str(FixedPoint("1.5")) == "1.5"
        assert str(FixedPoint("10.5")) == "10.5"
        assert str(FixedPoint("1.05")) == "1.05"
        assert str(FixedPoint("1.50")) == "1.5"
        assert str(FixedPoint("01.5")) == "1.5"
        assert str(FixedPoint("010.050")) == "10.05"
        assert str(FixedPoint("-0.0")) == "0.0"
        assert str(FixedPoint("-2.1")) == "-2.1"
        assert str(FixedPoint("-2457.159178")) == "-2457.159178"
        assert str(FixedPoint("2_457.159178")) == "2457.159178"
        assert str(FixedPoint("24_570.0159178")) == "24570.0159178"
        assert str(FixedPoint(5)) == "0.000000000000000005"
        assert str(FixedPoint(50)) == "0.00000000000000005"
        assert str(FixedPoint(500)) == "0.0000000000000005"
        assert str(FixedPoint(-223423423)) == "-0.000000000223423423"
        assert str(FixedPoint(-223423423000000000000000000)) == "-223423423.0"
        assert str(FixedPoint(-0)) == "0.0"
        assert str(FixedPoint(3 * 10**18)) == "3.0"
        assert str(FixedPoint(5.0)) == "5.0"
        assert str(FixedPoint(1.5)) == "1.5"

    def test_add(self):
        r"""Test `+` sugar for various type combos"""
        # int + int
        assert FixedPoint(5) + FixedPoint(5) == FixedPoint(10)
        assert int(FixedPoint(5) + FixedPoint(5)) == 10
        # int + float
        assert int(FixedPoint(5) + FixedPoint(5.0)) == 5 + 5 * 10**18
        # float + float
        assert FixedPoint(5.0) + FixedPoint(5.0) == FixedPoint(10.0)
        assert float(FixedPoint(5.0) + FixedPoint(5.0)) == 10.0
        # float + int
        assert int(FixedPoint(5.0) + FixedPoint(5)) == 5 * 10**18 + 5
        # str + str
        assert FixedPoint("5.0") + FixedPoint("5.025") == FixedPoint("10.025")
        assert float(FixedPoint("5.0") + FixedPoint("5.0")) == 10.0

    def test_add_fail(self):
        r"""Test failure of `+` sugar

        We are ignoring type errors -- we know they're bad, but we're looking for failure
        """
        with self.assertRaises(OverflowError):
            _ = FixedPoint(2**256) + FixedPoint(1)
        fixed_point_value = FixedPoint(1)
        float_value = 1.0
        int_value = 1
        with self.assertRaises(TypeError):
            _ = fixed_point_value + float_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = float_value + fixed_point_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = fixed_point_value + int_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = int_value + fixed_point_value  # type: ignore

    def test_sub(self):
        r"""Test `-` sugar for various type combos"""
        # int - int
        assert FixedPoint(5) - FixedPoint(4) == FixedPoint(1)
        assert FixedPoint(5) - FixedPoint(5) == FixedPoint(0)
        assert int(FixedPoint(5) - FixedPoint(4)) == 1
        # float - float
        assert FixedPoint(5.0) - FixedPoint(4.0) == FixedPoint(1.0)
        assert FixedPoint(5.0) - FixedPoint(5.0) == FixedPoint(0.0)
        assert float(FixedPoint(5.0) - FixedPoint(4.0)) == 1.0
        # str - str
        assert FixedPoint("5.0") - FixedPoint("4.0") == FixedPoint("1.0")
        assert float(FixedPoint("5.0") - FixedPoint("0.025")) == 4.975

    def test_sub_fail(self):
        r"""Test failure of `-` sugar

        We are ignoring type errors -- we know they're bad, but we're looking for failure
        """
        fixed_point_value = FixedPoint(1)
        float_value = 1.0
        int_value = 1
        with self.assertRaises(TypeError):
            _ = fixed_point_value - float_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = float_value - fixed_point_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = fixed_point_value - int_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = int_value - fixed_point_value  # type: ignore

    def test_multiply(self):
        r"""Test `*` sugar for various type combos"""
        # int * int
        # NOTE: multiply divides by 1e18, so this is 5 * 5 / 1e18 which rounds to zero
        for scale in range(0, 8):
            assert int(FixedPoint(5 * 10**scale) * FixedPoint(5 * 10**scale)) == 0
        assert int(FixedPoint(5 * 10**9) * FixedPoint(5 * 10**9)) == 25
        assert int(FixedPoint(5 * 10**10) * FixedPoint(5 * 10**10)) == 2500
        assert int(FixedPoint(5)) * int(FixedPoint(5)) == 25
        assert int(FixedPoint(5)) * 5 == 25
        assert FixedPoint(5 * 10**18) * FixedPoint(5 * 10**18) == FixedPoint(25 * 10**18)
        # int * float
        assert int(FixedPoint(5) * FixedPoint(5.0)) == 25
        # float * float
        assert FixedPoint(0.1) * FixedPoint(0.1) == FixedPoint(0.01)
        assert FixedPoint(1e-9) * FixedPoint(1e-9) == FixedPoint(1e-18)
        assert FixedPoint(1e-10) * FixedPoint(1e-10) == FixedPoint(0)
        assert FixedPoint(5.0) * FixedPoint(5.0) == FixedPoint(25.0)
        assert float(FixedPoint(5.0) * FixedPoint(5.0)) == 25.0
        # float * int
        assert int(FixedPoint(5.0) * FixedPoint(5)) == 25  # 5e18 * 5e-18 = 25e0
        assert float(FixedPoint(5.0)) * 5 == 25.0
        # str * str * str
        assert FixedPoint("5.0") * FixedPoint("5.0") * FixedPoint("0.1") == FixedPoint("2.50")

    def test_multiply_fail(self):
        r"""Test failure of `*` sugar

        We are ignoring type errors -- we know they're bad, but we're looking for failure
        """
        fixed_point_value = FixedPoint(1)
        float_value = 1.0
        int_value = 1
        with self.assertRaises(TypeError):
            _ = fixed_point_value * float_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = float_value * fixed_point_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = fixed_point_value * int_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = int_value * fixed_point_value  # type: ignore

    def test_divide(self):
        r"""Test `/` sugar for various type combos"""
        # int / int
        assert int(FixedPoint(5) / FixedPoint(5)) == 1 * 10**18  # 1 * 10**18 is "1" in FP world
        assert int(FixedPoint(5) / FixedPoint(5)) == 1 * 10**18
        assert int(FixedPoint(5)) / 5 == 1
        assert 5 / int(FixedPoint(5)) == 1
        assert float(FixedPoint(5)) / 5 == 1 * 10**-18
        # scaling both numerator & denominator shouldn't change the outcome
        assert FixedPoint(5) / FixedPoint(7) == FixedPoint(714285714285714285)
        assert FixedPoint(50) / FixedPoint(70) == FixedPoint(714285714285714285)
        assert FixedPoint(500) / FixedPoint(700) == FixedPoint(714285714285714285)
        # int / float
        assert int(FixedPoint(5) / FixedPoint(5.0)) == 1  # 5e-18 / 5e18 = (5/5) * 10 ** (-18+18) = 1
        # float / float
        assert FixedPoint(5.0) / FixedPoint(5.0) == FixedPoint(1.0)
        assert float(FixedPoint(5.0) / FixedPoint(5.0)) == 1.0
        # float / int
        assert int(FixedPoint(1.0) / FixedPoint(1)) == 1 * 10**36  # 1e18 / 1e-18 = 1e36
        # str / str
        assert FixedPoint("5.0") / FixedPoint("5.0") == FixedPoint("1.0")
        assert float(FixedPoint("6.0") / FixedPoint("2.5")) == 2.4
        assert float(FixedPoint("6.0") / FixedPoint("100.0")) == 0.06
        assert float(FixedPoint("0.006") / FixedPoint("0.001")) == 6
        # div rounding
        assert FixedPoint(2.0) / FixedPoint(1 * 10**37) == FixedPoint(0)
        assert FixedPoint(2.0).div_up(FixedPoint(1 * 10**37)) == FixedPoint(1)

    def test_divide_fail(self):
        r"""Test failure of `/` sugar

        We are ignoring type errors -- we know they're bad, but we're looking for failure
        """
        fixed_point_value = FixedPoint(1)
        fixed_point_zero = FixedPoint(0)
        float_value = 1.0
        int_value = 1
        with self.assertRaises(TypeError):
            _ = fixed_point_value / float_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = float_value / fixed_point_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = fixed_point_value / int_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = int_value / fixed_point_value  # type: ignore
        with self.assertRaises(errors.DivisionByZero):
            _ = fixed_point_value / fixed_point_zero

    def test_floor_divide(self):
        r"""Test `//` sugar"""
        assert FixedPoint("6.3") // FixedPoint("2.0") == FixedPoint("3.0")
        assert FixedPoint("8.0") // FixedPoint("2.0") == FixedPoint("4.0")
        assert FixedPoint("8.0") // FixedPoint("5.0") == FixedPoint("1.0")
        assert FixedPoint("0.5") // FixedPoint("0.2") == FixedPoint("2.0")

    def test_power(self):
        r"""Test `**` sugar"""
        # power zero
        assert int(FixedPoint(5.0) ** FixedPoint(0)) == 1 * 10**18
        assert int(FixedPoint(5) ** FixedPoint(0)) == 1 * 10**18
        assert float(FixedPoint(5.0) ** FixedPoint(0)) == 1
        assert float(FixedPoint(5) ** FixedPoint(0)) == 1
        # power one
        self.assertAlmostEqual(int(FixedPoint(5.0) ** FixedPoint(1.0)), int(FixedPoint(5.0)), delta=5)
        self.assertAlmostEqual(
            int(FixedPoint(5 * 10**18) ** FixedPoint(1 * 10**18)), int(FixedPoint(5 * 10**18)), delta=5
        )
        # power two
        self.assertAlmostEqual(int(FixedPoint(5.0) ** FixedPoint(2.0)), int(FixedPoint(25.0)), delta=30)
        self.assertAlmostEqual(
            int(FixedPoint(5 * 10**18) ** FixedPoint(2 * 10**18)), int(FixedPoint(25.0)), delta=30
        )

    def test_modulo(self):
        r"""Test '%' syntax for various type combos"""
        # int % int
        assert FixedPoint(5) % FixedPoint(2) == FixedPoint(1)
        assert FixedPoint(9) % FixedPoint(3) == FixedPoint(0)
        assert FixedPoint(10) % FixedPoint(3) == FixedPoint(1)
        assert FixedPoint(15) % FixedPoint(4) == FixedPoint(3)
        assert FixedPoint(17) % FixedPoint(12) == FixedPoint(5)
        assert FixedPoint(240) % FixedPoint(13) == FixedPoint(6)
        assert FixedPoint(10) % FixedPoint(16) == FixedPoint(10)
        assert FixedPoint(17) % FixedPoint(12) == FixedPoint(5)
        assert FixedPoint(-17) % FixedPoint(3) == FixedPoint(1)
        assert FixedPoint(8) % FixedPoint(-3) == FixedPoint(-1)
        assert FixedPoint(37) % FixedPoint(-5) == FixedPoint(-3)
        assert FixedPoint(37) % FixedPoint(1) == FixedPoint(0)
        # int % float
        assert float(FixedPoint(5) % FixedPoint(2.0)) == 5e-18
        assert float(FixedPoint(9) % FixedPoint(3.5)) == 9e-18
        # float % float
        assert float(FixedPoint(5.0) % FixedPoint(2.0)) == 1.0
        assert float(FixedPoint(9.0) % FixedPoint(3.5)) == 2.0
        # float % int
        assert float(FixedPoint(5.0) % FixedPoint(2)) == 0.0
        assert float(FixedPoint(9.0) % FixedPoint(3)) == 0.0
        # str % str
        assert float(FixedPoint("37.0") % FixedPoint("1.0")) == 0.0
        assert float(FixedPoint("5.0") % FixedPoint("2.0")) == 1.0
        assert float(FixedPoint("9.0") % FixedPoint("3.5")) == 2.0
        assert float(FixedPoint("6.0") % FixedPoint("2.5")) == 1.0
        assert float(FixedPoint("6.0") % FixedPoint("100.0")) == 6.0
        assert float(FixedPoint("0.006") % FixedPoint("0.001")) == 0.0
        assert FixedPoint("12.5") % FixedPoint("5.5") == FixedPoint("1.5")
        assert FixedPoint("17.0") % FixedPoint("12.0") == FixedPoint("5.0")
        assert FixedPoint("13.3") % FixedPoint("1.1") == FixedPoint("0.1")
        assert FixedPoint("-17.0") % FixedPoint("3.0") == FixedPoint("1.0")
        assert FixedPoint("8.0") % FixedPoint("-3.0") == FixedPoint("-1.0")
        assert FixedPoint("37.0") % FixedPoint("-5.0") == FixedPoint("-3.0")

    def test_modulo_fail(self):
        r"""Test failure of `%` sugar

        We are ignoring type errors -- we know they're bad, but we're looking for failure
        """
        fixed_point_value = FixedPoint(1)
        fixed_point_zero = FixedPoint(0)
        float_value = 1.0
        int_value = 1
        with self.assertRaises(TypeError):
            _ = fixed_point_value % float_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = float_value % fixed_point_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = fixed_point_value % int_value  # type: ignore
        with self.assertRaises(TypeError):
            _ = int_value % fixed_point_value  # type: ignore
        with self.assertRaises(errors.DivisionByZero):
            _ = fixed_point_value % fixed_point_zero

    def test_divmod(self):
        r"""Test `divmod` support"""
        assert divmod(FixedPoint(5), FixedPoint(7)) == (FixedPoint(5) // FixedPoint(7), FixedPoint(5) % FixedPoint(7))
        assert divmod(FixedPoint(5), FixedPoint(7)) == (FixedPoint(0), FixedPoint(5))
        assert divmod(FixedPoint("6.3"), FixedPoint("2.0")) == (FixedPoint("3.0"), FixedPoint("0.3"))
        assert divmod(FixedPoint("5.5"), FixedPoint("2.2")) == (FixedPoint("2.0"), FixedPoint("1.1"))
        assert divmod(FixedPoint("-5.5"), FixedPoint("-2.2")) == (FixedPoint("2.0"), FixedPoint("-1.1"))
        assert divmod(FixedPoint("5.5"), FixedPoint("-2.2")) == (FixedPoint("-3.0"), FixedPoint("-1.1"))

    def test_divmod_fail(self):
        r"""Test `divmod` failure mode"""
        with self.assertRaises(errors.DivisionByZero):
            _ = divmod(FixedPoint("1.0"), FixedPoint(0))

    def test_floor(self):
        r"""Test floor method"""
        assert math.floor(FixedPoint("-2.1")) == FixedPoint("-2.1").floor()
        assert math.floor(FixedPoint("-2.1")) == FixedPoint("-3.0")
        assert math.floor(FixedPoint("-2.1")) == FixedPoint("-3.0")
        assert math.floor(FixedPoint("3.6")) == FixedPoint("3.0")
        assert math.floor(FixedPoint("0.5")) == FixedPoint(0)
        assert math.floor(FixedPoint(3)) == FixedPoint(0)
        assert math.floor(FixedPoint(-6)) == FixedPoint("-1.0")
        assert math.floor(FixedPoint(-6.0)) == FixedPoint(-6.0)
        assert math.floor(FixedPoint(-6.8)) == FixedPoint(-7.0)

    def test_ceil(self):
        r"""Test ceil method"""
        assert FixedPoint("3.0").ceil() == FixedPoint("3.0")
        assert FixedPoint("3.000000000000001").ceil() == FixedPoint("4.0")
        assert FixedPoint("3.1").ceil() == math.ceil(FixedPoint("3.7"))
        assert math.ceil(FixedPoint("3.6")) == FixedPoint("4.0")
        assert math.ceil(FixedPoint("0.5")) == FixedPoint("1.0")
        assert math.ceil(FixedPoint("0.0000000003")) == FixedPoint("1.0")
        assert math.ceil(FixedPoint("-0.0")) == FixedPoint(0)
        assert math.ceil(FixedPoint("0.0")) == FixedPoint(0)
        assert math.ceil(FixedPoint(3)) == FixedPoint(1.0)
        assert math.ceil(FixedPoint(-6)) == FixedPoint(0)
        assert math.ceil(FixedPoint(-6.0)) == FixedPoint(-6.0)
        assert math.ceil(FixedPoint(6.0)) == FixedPoint(6.0)
        assert math.ceil(FixedPoint(-6.8)) == FixedPoint(-6.0)
        assert math.ceil(FixedPoint(6.8)) == FixedPoint(7.0)

    def test_trunc(self):
        r"""Test trunc method"""
        assert math.trunc(FixedPoint("3.6")) == FixedPoint("3.0")
        assert math.trunc(FixedPoint("0.5")) == FixedPoint("0.0")
        assert math.trunc(FixedPoint("0.0000000003")) == FixedPoint("0.0")
        assert math.trunc(FixedPoint("-0.0")) == FixedPoint(0)
        assert math.trunc(FixedPoint("0.0")) == FixedPoint(0)
        assert math.trunc(FixedPoint(3)) == FixedPoint(0.0)
        assert math.trunc(FixedPoint(-6)) == FixedPoint(0)
        assert math.trunc(FixedPoint(-6.0)) == FixedPoint(-6.0)
        assert math.trunc(FixedPoint(6.0)) == FixedPoint(6.0)
        assert math.trunc(FixedPoint(-6.8)) == FixedPoint(-6.0)
        assert math.trunc(FixedPoint(6.8)) == FixedPoint(6.0)

    def test_round(self):
        r"""Test round method"""
        # normal round up & down behavior
        assert round(FixedPoint("3.6")) == FixedPoint("4.0")
        assert round(FixedPoint("3.48927")) == FixedPoint("3.0")
        assert round(FixedPoint("-3.6")) == FixedPoint("-4.0")
        assert round(FixedPoint("-3.4")) == FixedPoint("-3.0")
        assert round(FixedPoint("1.45")) == FixedPoint("1.0")
        assert round(FixedPoint("1.75")) == FixedPoint("2.0")
        # round half to even
        assert round(FixedPoint("0.5")) == FixedPoint("0.0")
        assert round(FixedPoint("1.5")) == FixedPoint("2.0")
        assert round(FixedPoint("2.5")) == FixedPoint("2.0")
        assert round(FixedPoint("-0.5")) == FixedPoint("0.0")
        assert round(FixedPoint("-1.5")) == FixedPoint("-2.0")
        # round with non-zero ndigits
        assert round(FixedPoint("1.75"), ndigits=1) == FixedPoint("1.8")
        assert round(FixedPoint("100.75"), ndigits=1) == FixedPoint("100.8")
        assert round(FixedPoint("1.45"), ndigits=1) == FixedPoint("1.4")
        assert round(FixedPoint("1.5"), ndigits=3) == FixedPoint("1.5")
        assert round(FixedPoint("3.5"), ndigits=1) == FixedPoint("3.5")
        assert round(FixedPoint("3.55"), ndigits=1) == FixedPoint("3.6")
        assert round(FixedPoint("3.54"), ndigits=1) == FixedPoint("3.5")
        assert round(FixedPoint("3.545"), ndigits=2) == FixedPoint("3.54")
        assert round(FixedPoint("3.545"), ndigits=4) == FixedPoint("3.545")
        assert round(FixedPoint("3.545"), ndigits=5) == FixedPoint("3.545")
        assert round(FixedPoint("-3.5459857"), ndigits=5) == FixedPoint("-3.54599")
        assert round(FixedPoint("-3.5459850"), ndigits=5) == FixedPoint("-3.54598")

    def test_hash(self):
        """Test hash method"""
        assert hash(FixedPoint(-1)) == -2
        assert hash(FixedPoint(-2)) == hash(-2)
        assert hash(FixedPoint(2)) == hash(2)
        assert hash(FixedPoint("-1.0")) == hash(-1 * 10**18)
        assert hash(FixedPoint("1.0")) == hash(1 * 10**18)
        assert hash(FixedPoint("-2.5")) == hash(-2.5 * 10**18)
        assert hash(FixedPoint("2.5")) == hash(2.5 * 10**18)
        assert hash(FixedPoint("-200.537280")) == hash(-200.537280 * 10**18)

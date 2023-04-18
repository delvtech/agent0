"""Fixed point math tests inspired from solidity hyperdrive implementation"""
import math
import unittest

from elfpy.utils.math import FixedPoint


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
        # INTS
        assert int(FixedPoint(1)) == 1  # int intput directly maps
        assert int(FixedPoint(1.0)) == 1000000000000000000  # float input is rescaled by 1e18
        assert int(FixedPoint(1.0)) == 1 * 10**18  # 1 * 10**18 is int, and is equal to int(1e18)
        # FLOATS
        assert float(FixedPoint(1)) == 1e-18  # cast FP(small int) back to float should be tiny
        assert float(FixedPoint(1.0)) == 1.0  # cast FP(float) back to float should be equivalent
        assert float(FixedPoint(1e18)) == 1e18  # even if float is large, casting back stays large
        # NOTE: floats are scaled on construction, ints are not; floats also introduce noise
        assert math.isclose(FixedPoint(1e18), FixedPoint(1 * 10**36), abs_tol=1e-18)
        # NOTE: this is true because in python 5 == 5.0.  and int output of 5 from a FixedPoint
        # number means that the value was 5e-18 and a float output of 5.0 means the output was 5e18.
        assert int(FixedPoint(5)) == float(FixedPoint(5.0))
        # STRINGS
        assert FixedPoint("5.1") == FixedPoint(5.1)
        assert FixedPoint("5.01") == FixedPoint(5.01)
        assert FixedPoint("5.000001") == FixedPoint(5.000001)

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

    def test_divide_fail(self):
        r"""Test failure of `/` sugar

        We are ignoring type errors -- we know they're bad, but we're looking for failure
        """
        fixed_point_value = FixedPoint(1)
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

    def test_power(self):
        r"""Test `**` sugar for various type combos"""
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

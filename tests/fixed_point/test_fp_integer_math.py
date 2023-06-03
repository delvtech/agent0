"""FixedPoint integer math tests inspired from solidity hyperdrive implementation"""
import math
import unittest

from elfpy.math import FixedPointIntegerMath
from elfpy.errors import errors

# pylint: disable=too-many-public-methods


class TestFixedPointIntegerMath(unittest.TestCase):
    """Unit tests to verify that the fixed-point integer implementations are correct.
    The tests assume everything is in 1e18 precision.

    ..note::
        Note that `ln` and `pow` require lower precision.
        Additionally, the approximations used for fixed-point arithmetic
        are less accurate the closer one gets to the maximum bounds.
    """

    APPROX_EQ = 1e6  # 6e-13 for FixedPoint integers with 18-decimal precision

    def test_add(self):
        """Test fixed-point add for various integer inputs"""
        self.assertEqual(
            FixedPointIntegerMath.add(FixedPointIntegerMath.ONE_18, 5 * FixedPointIntegerMath.ONE_18),
            6 * FixedPointIntegerMath.ONE_18,
        )
        self.assertEqual(
            FixedPointIntegerMath.add(FixedPointIntegerMath.ONE_18, FixedPointIntegerMath.ONE_18),
            2 * FixedPointIntegerMath.ONE_18,
        )
        self.assertEqual(FixedPointIntegerMath.add(FixedPointIntegerMath.ONE_18, 0), FixedPointIntegerMath.ONE_18)
        self.assertEqual(FixedPointIntegerMath.add(0, FixedPointIntegerMath.ONE_18), FixedPointIntegerMath.ONE_18)
        self.assertEqual(FixedPointIntegerMath.add(0, 0), 0)

    def test_fail_add_overflow(self):
        """Test fixed-point add for invalid integer inputs"""
        with self.assertRaises(OverflowError):
            FixedPointIntegerMath.add(FixedPointIntegerMath.INT_MAX, FixedPointIntegerMath.ONE_18)

    def test_sub(self):
        """Test fixed-point sub for various integer inputs"""
        self.assertEqual(
            FixedPointIntegerMath.sub(5 * FixedPointIntegerMath.ONE_18, 3 * FixedPointIntegerMath.ONE_18),
            2 * FixedPointIntegerMath.ONE_18,
        )
        self.assertEqual(FixedPointIntegerMath.sub(FixedPointIntegerMath.ONE_18, FixedPointIntegerMath.ONE_18), 0)
        self.assertEqual(FixedPointIntegerMath.sub(FixedPointIntegerMath.ONE_18, 0), FixedPointIntegerMath.ONE_18)
        self.assertEqual(
            FixedPointIntegerMath.sub(2 * FixedPointIntegerMath.ONE_18, FixedPointIntegerMath.ONE_18),
            FixedPointIntegerMath.ONE_18,
        )
        self.assertEqual(FixedPointIntegerMath.sub(0, 0), 0)

    def test_fail_sub_overflow(self):
        """Test fixed-point sub for invalid integer inputs"""
        with self.assertRaises(OverflowError):
            FixedPointIntegerMath.sub(FixedPointIntegerMath.INT_MIN, FixedPointIntegerMath.ONE_18)

    def test_mul_up(self):
        """Test multiplying two values and rounding up"""
        self.assertEqual(
            FixedPointIntegerMath.mul_up(
                int(2.5 * FixedPointIntegerMath.ONE_18), int(0.5 * FixedPointIntegerMath.ONE_18)
            ),
            int(1.25 * FixedPointIntegerMath.ONE_18),
        )
        self.assertEqual(
            FixedPointIntegerMath.mul_up(3 * FixedPointIntegerMath.ONE_18, FixedPointIntegerMath.ONE_18),
            3 * FixedPointIntegerMath.ONE_18,
        )
        self.assertEqual(FixedPointIntegerMath.mul_up(369, 271), 1)
        self.assertEqual(FixedPointIntegerMath.mul_up(0, FixedPointIntegerMath.ONE_18), 0)
        self.assertEqual(FixedPointIntegerMath.mul_up(FixedPointIntegerMath.ONE_18, 0), 0)
        self.assertEqual(FixedPointIntegerMath.mul_up(0, 0), 0)

    def test_mul_down(self):
        """Test multiplying two values and rounding down"""
        self.assertEqual(
            FixedPointIntegerMath.mul_down(2 * FixedPointIntegerMath.ONE_18, 3 * FixedPointIntegerMath.ONE_18),
            6 * FixedPointIntegerMath.ONE_18,
        )
        self.assertEqual(
            FixedPointIntegerMath.mul_down(
                int(2.5 * FixedPointIntegerMath.ONE_18), int(0.5 * FixedPointIntegerMath.ONE_18)
            ),
            int(1.25 * FixedPointIntegerMath.ONE_18),
        )
        self.assertEqual(
            FixedPointIntegerMath.mul_down(3 * FixedPointIntegerMath.ONE_18, FixedPointIntegerMath.ONE_18),
            3 * FixedPointIntegerMath.ONE_18,
        )
        self.assertEqual(FixedPointIntegerMath.mul_down(369, 271), 0)
        self.assertEqual(FixedPointIntegerMath.mul_down(0, FixedPointIntegerMath.ONE_18), 0)
        self.assertEqual(FixedPointIntegerMath.mul_down(FixedPointIntegerMath.ONE_18, 0), 0)
        self.assertEqual(FixedPointIntegerMath.mul_down(0, 0), 0)

    def test_div_down(self):
        """Test dividing two values and rounding down"""
        self.assertEqual(
            FixedPointIntegerMath.div_down(6 * FixedPointIntegerMath.ONE_18, 2 * FixedPointIntegerMath.ONE_18),
            3 * FixedPointIntegerMath.ONE_18,
        )
        self.assertEqual(
            FixedPointIntegerMath.div_down(
                int(1.25 * FixedPointIntegerMath.ONE_18), int(0.5 * FixedPointIntegerMath.ONE_18)
            ),
            int(2.5 * FixedPointIntegerMath.ONE_18),
        )
        self.assertEqual(
            FixedPointIntegerMath.div_down(3 * FixedPointIntegerMath.ONE_18, FixedPointIntegerMath.ONE_18),
            3 * FixedPointIntegerMath.ONE_18,
        )
        self.assertEqual(FixedPointIntegerMath.div_down(2 * FixedPointIntegerMath.ONE_18, int(1e19 * 1e18)), 0)
        self.assertEqual(FixedPointIntegerMath.div_down(0, FixedPointIntegerMath.ONE_18), 0)

    def test_fail_div_down_zero_denominator(self):
        """Test error when dividing by zero"""
        with self.assertRaises(ValueError):
            FixedPointIntegerMath.div_down(FixedPointIntegerMath.ONE_18, 0)

    def test_div_up(self):
        """Test dividing two values and rounding up"""
        self.assertEqual(
            FixedPointIntegerMath.div_up(
                int(1.25 * FixedPointIntegerMath.ONE_18), int(0.5 * FixedPointIntegerMath.ONE_18)
            ),
            int(2.5 * FixedPointIntegerMath.ONE_18),
        )
        self.assertEqual(
            FixedPointIntegerMath.div_up(3 * FixedPointIntegerMath.ONE_18, FixedPointIntegerMath.ONE_18),
            3 * FixedPointIntegerMath.ONE_18,
        )
        self.assertEqual(FixedPointIntegerMath.div_up(2 * FixedPointIntegerMath.ONE_18, int(1e19 * 1e18)), 1)
        self.assertEqual(FixedPointIntegerMath.div_up(0, FixedPointIntegerMath.ONE_18), 0)

    def test_fail_div_up_zero_denominator(self):
        """Test error when dividing by zero"""
        with self.assertRaises(ValueError):
            FixedPointIntegerMath.div_up(FixedPointIntegerMath.ONE_18, 0)

    def test_mul_div_down(self):
        """Test multiplying two numbers, dividing a third, and then rounding down"""
        self.assertEqual(FixedPointIntegerMath.mul_div_down(int(2.5e27), int(0.5e27), int(1e27)), 1.25e27)
        self.assertEqual(FixedPointIntegerMath.mul_div_down(int(2.5e18), int(0.5e18), int(1e18)), 1.25e18)
        self.assertEqual(FixedPointIntegerMath.mul_div_down(int(2.5e8), int(0.5e8), int(1e8)), 1.25e8)
        self.assertEqual(FixedPointIntegerMath.mul_div_down(369, 271, int(1e2)), 999)
        self.assertEqual(FixedPointIntegerMath.mul_div_down(int(1e27), int(1e27), int(2e27)), 0.5e27)
        self.assertEqual(FixedPointIntegerMath.mul_div_down(int(1e18), int(1e18), int(2e18)), 0.5e18)
        self.assertEqual(FixedPointIntegerMath.mul_div_down(int(1e8), int(1e8), int(2e8)), 0.5e8)
        self.assertEqual(FixedPointIntegerMath.mul_div_down(int(2e27), int(3e27), int(3e27)), 2e27)
        self.assertEqual(FixedPointIntegerMath.mul_div_down(int(2e18), int(3e18), int(3e18)), 2e18)
        self.assertEqual(FixedPointIntegerMath.mul_div_down(int(2e8), int(3e8), int(3e8)), 2e8)
        self.assertEqual(FixedPointIntegerMath.mul_div_down(0, int(1e18), int(1e18)), 0)
        self.assertEqual(FixedPointIntegerMath.mul_div_down(int(1e18), 0, int(1e18)), 0)
        self.assertEqual(FixedPointIntegerMath.mul_div_down(0, 0, int(1e18)), 0)

    def test_fail_mul_div_down_zero_denominator(self):
        """Test failure for multiplying two numbers, then dividing by zero"""
        with self.assertRaises(ValueError):
            FixedPointIntegerMath.mul_div_down(FixedPointIntegerMath.ONE_18, FixedPointIntegerMath.ONE_18, 0)

    def test_mul_div_up(self):
        """Test multiplying two numbers, dividing a third, and then rounding up"""
        self.assertEqual(FixedPointIntegerMath.mul_div_up(int(2.5e27), int(0.5e27), int(1e27)), 1.25e27)
        self.assertEqual(FixedPointIntegerMath.mul_div_up(int(2.5e18), int(0.5e18), int(1e18)), 1.25e18)
        self.assertEqual(FixedPointIntegerMath.mul_div_up(int(2.5e8), int(0.5e8), int(1e8)), 1.25e8)
        self.assertEqual(FixedPointIntegerMath.mul_div_up(369, 271, int(1e2)), 1000)
        self.assertEqual(FixedPointIntegerMath.mul_div_up(int(1e27), int(1e27), int(2e27)), 0.5e27)
        self.assertEqual(FixedPointIntegerMath.mul_div_up(int(1e18), int(1e18), int(2e18)), 0.5e18)
        self.assertEqual(FixedPointIntegerMath.mul_div_up(int(1e8), int(1e8), int(2e8)), 0.5e8)
        self.assertEqual(FixedPointIntegerMath.mul_div_up(int(2e27), int(3e27), int(3e27)), 2e27)
        self.assertEqual(FixedPointIntegerMath.mul_div_up(int(2e18), int(3e18), int(3e18)), 2e18)
        self.assertEqual(FixedPointIntegerMath.mul_div_up(int(2e8), int(3e8), int(3e8)), 2e8)
        self.assertEqual(FixedPointIntegerMath.mul_div_up(0, int(1e18), int(1e18)), 0)
        self.assertEqual(FixedPointIntegerMath.mul_div_up(int(1e18), 0, int(1e18)), 0)
        self.assertEqual(FixedPointIntegerMath.mul_div_up(0, 0, int(1e18)), 0)

    def test_fail_mul_div_up_zero_denominator(self):
        """Test failure for multiplying two numbers, then dividing by zero"""
        with self.assertRaises(ValueError):
            FixedPointIntegerMath.mul_div_up(FixedPointIntegerMath.ONE_18, FixedPointIntegerMath.ONE_18, 0)

    def test_ilog2(self):
        """Test integer log base 2"""
        # pylint: disable=protected-access
        self.assertEqual(FixedPointIntegerMath.ilog2(0), 0)
        self.assertEqual(FixedPointIntegerMath.ilog2(1), 0)
        self.assertEqual(FixedPointIntegerMath.ilog2(2), 1)
        self.assertEqual(FixedPointIntegerMath.ilog2(3), 1)
        self.assertEqual(FixedPointIntegerMath.ilog2(4), 2)
        self.assertEqual(FixedPointIntegerMath.ilog2(8), 3)
        self.assertEqual(FixedPointIntegerMath.ilog2(16), 4)
        self.assertEqual(FixedPointIntegerMath.ilog2(32), 5)
        self.assertEqual(FixedPointIntegerMath.ilog2(64), 6)
        self.assertEqual(FixedPointIntegerMath.ilog2(128), 7)
        self.assertEqual(FixedPointIntegerMath.ilog2(256), 8)
        self.assertEqual(FixedPointIntegerMath.ilog2(512), 9)
        self.assertEqual(FixedPointIntegerMath.ilog2(1024), 10)
        self.assertEqual(FixedPointIntegerMath.ilog2(2048), 11)
        self.assertEqual(FixedPointIntegerMath.ilog2(4096), 12)
        self.assertEqual(FixedPointIntegerMath.ilog2(8192), 13)
        self.assertEqual(FixedPointIntegerMath.ilog2(16384), 14)
        self.assertEqual(FixedPointIntegerMath.ilog2(32768), 15)
        self.assertEqual(FixedPointIntegerMath.ilog2(65536), 16)
        self.assertEqual(FixedPointIntegerMath.ilog2(131072), 17)
        self.assertEqual(FixedPointIntegerMath.ilog2(262144), 18)
        self.assertEqual(FixedPointIntegerMath.ilog2(524288), 19)
        self.assertEqual(FixedPointIntegerMath.ilog2(1048576), 20)

    def test_ln(self):
        """Test integer natural log"""
        result = FixedPointIntegerMath.ln(FixedPointIntegerMath.ONE_18)
        expected = 0
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"ln(x)\n  {result=},\n{expected=}")
        result = FixedPointIntegerMath.ln(1000000 * FixedPointIntegerMath.ONE_18)
        expected = 13815510557964274104
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"ln(x)\n  {result=},\n{expected=}")
        result = FixedPointIntegerMath.ln(int(5 * 1e18))
        expected = int(math.log(5) * 1e18)
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"ln(x)\n  {result=},\n{expected=}")
        result = FixedPointIntegerMath.ln(int(10 * 1e18))
        expected = int(math.log(10) * 1e18)
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"ln(x)\n  {result=},\n{expected=}")

    def test_exp(self):
        """Test integer exp"""
        result = FixedPointIntegerMath.exp(FixedPointIntegerMath.ONE_18)
        expected = 2718281828459045235
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"exp(x):\n  {result=},\n{expected=}")
        result = FixedPointIntegerMath.exp(-FixedPointIntegerMath.ONE_18)
        expected = 367879441171442321
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"exp(x):\n  {result=},\n{expected=}")
        result = FixedPointIntegerMath.exp(FixedPointIntegerMath.EXP_MIN - 1)
        expected = 0
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"exp(x):\n  {result=},\n{expected=}")
        result = FixedPointIntegerMath.exp(int(5 * 1e18))
        expected = int(math.exp(5) * 1e18)
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"exp(x):\n  {result=},\n{expected=}")
        result = FixedPointIntegerMath.exp(int(-5 * 1e18))
        expected = int(math.exp(-5) * 1e18)
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"exp(x):\n  {result=},\n{expected=}")
        result = FixedPointIntegerMath.exp(int(10 * 1e18))
        expected = int(math.exp(10) * 1e18)
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"exp(x):\n  {result=},\n{expected=}")
        result = FixedPointIntegerMath.exp(int(-10 * 1e18))
        expected = int(math.exp(-10) * 1e18)
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"exp(x):\n  {result=},\n{expected=}")
        result = FixedPointIntegerMath.exp(0)
        expected = int(math.exp(0) * 1e18)
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"exp(x):\n  {result=},\n{expected=}")

        # TODO: This fails when the inputs are any closer to EXP_MAX.
        # To improve precision at high values, we will need to update the (m,n)-term rational approximation
        result = FixedPointIntegerMath.exp(FixedPointIntegerMath.EXP_MAX - int(145e18))
        expected = int(math.exp((FixedPointIntegerMath.EXP_MAX - 145e18) / 1e18) * 1e18)
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"exp(x):\n  {result=},\n{expected=}")

    def test_fail_exp_negative_or_zero_input(self):
        """Test integer exp fails if the input is too large"""
        with self.assertRaises(ValueError):
            FixedPointIntegerMath.exp(FixedPointIntegerMath.EXP_MAX + 1)

    def test_pow(self):
        """Test integer pow"""
        result = FixedPointIntegerMath.pow(300000000000000000000000, 977464155968402951)
        expected = 225782202044931640847042
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"\n  {result=}\n{expected=}")
        result = FixedPointIntegerMath.pow(180000000000000000000000, 977464155968402951)
        expected = 137037839669721400603869
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"\n  {result=}\n{expected=}")
        result = FixedPointIntegerMath.pow(165891671009915386326945, 1023055417320413264)
        expected = 218861723977998147080714
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"\n  {result=}\n{expected=}")
        result = FixedPointIntegerMath.pow(77073744241129234405745, 1023055417320413264)
        expected = 99902446857632926742201
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"\n  {result=}\n{expected=}")
        result = FixedPointIntegerMath.pow(18458206546438581254928, 1023055417320413264)
        expected = 23149855298128876929745
        self.assertAlmostEqual(result, expected, delta=self.APPROX_EQ, msg=f"\n  {result=}\n{expected=}")

    def test_sqrt(self):
        """Test integer square root"""
        # pylint: disable=invalid-name
        self.assertAlmostEqual(FixedPointIntegerMath.sqrt(0), 0, delta=self.APPROX_EQ)
        self.assertAlmostEqual(
            FixedPointIntegerMath.sqrt(FixedPointIntegerMath.ONE_18), FixedPointIntegerMath.ONE_18, delta=self.APPROX_EQ
        )
        self.assertAlmostEqual(
            FixedPointIntegerMath.sqrt(9 * FixedPointIntegerMath.ONE_18),
            3 * FixedPointIntegerMath.ONE_18,
            delta=self.APPROX_EQ,
        )
        self.assertAlmostEqual(
            FixedPointIntegerMath.sqrt(16 * FixedPointIntegerMath.ONE_18),
            4 * FixedPointIntegerMath.ONE_18,
            delta=self.APPROX_EQ,
        )
        self.assertAlmostEqual(
            FixedPointIntegerMath.sqrt(100 * FixedPointIntegerMath.ONE_18),
            10 * FixedPointIntegerMath.ONE_18,
            delta=self.APPROX_EQ,
        )
        # Compare with math.isqrt for additional verification
        for i in range(10000):
            x = i * FixedPointIntegerMath.ONE_18
            self.assertAlmostEqual(
                FixedPointIntegerMath.sqrt(i),
                math.isqrt(x),
                delta=self.APPROX_EQ,
                msg=f"isqrt comparison for {i=} failed",
            )

    def test_sqrt_fail(self):
        """Test failure mode of square root"""
        with self.assertRaises(errors.DivisionByZero):
            _ = FixedPointIntegerMath.sqrt(-1)

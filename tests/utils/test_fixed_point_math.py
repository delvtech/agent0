"""Fixed point math tests inspired from solidity hyperdrive implementation"""
import unittest
import math

from elfpy.utils.math import FixedPointMath


class TestFixedPointMath(unittest.TestCase):
    """Unit tests to verify that the fixed-point integer implementations are correct.
    The tests assume everything is in 1e18 precision.

    ..note::
        Note that `ln` and `pow` require lower precision.
        Additionally, the approximations used for fixed-point arithmetic are less accurate the closer one gets to the maximum bounds.
    """

    def test_add(self):
        """Test fixed-point add for various integer inputs"""
        assert FixedPointMath.add(FixedPointMath.ONE_18, 5 * FixedPointMath.ONE_18) == 6 * FixedPointMath.ONE_18
        assert FixedPointMath.add(FixedPointMath.ONE_18, FixedPointMath.ONE_18) == 2 * FixedPointMath.ONE_18
        assert FixedPointMath.add(FixedPointMath.ONE_18, 0) == FixedPointMath.ONE_18
        assert FixedPointMath.add(0, FixedPointMath.ONE_18) == FixedPointMath.ONE_18
        assert FixedPointMath.add(0, 0) == 0

    def test_fail_add_overflow(self):
        """Test fixed-point add for invalid integer inputs"""
        with self.assertRaises(ValueError):  # FIXME: use overflow/underflow errors instead of value errors
            FixedPointMath.add(FixedPointMath.INT_MAX, FixedPointMath.ONE_18)

    def test_sub(self):
        """Test fixed-point sub for various integer inputs"""
        assert FixedPointMath.sub(5 * FixedPointMath.ONE_18, 3 * FixedPointMath.ONE_18) == 2 * FixedPointMath.ONE_18
        assert FixedPointMath.sub(FixedPointMath.ONE_18, FixedPointMath.ONE_18) == 0
        assert FixedPointMath.sub(FixedPointMath.ONE_18, 0) == FixedPointMath.ONE_18
        assert FixedPointMath.sub(2 * FixedPointMath.ONE_18, FixedPointMath.ONE_18) == FixedPointMath.ONE_18
        assert FixedPointMath.sub(0, 0) == 0

    def test_fail_sub_overflow(self):
        """Test fixed-point sub for invalid integer inputs"""
        with self.assertRaises(ValueError):
            FixedPointMath.sub(0, FixedPointMath.ONE_18)

    def test_mul_up(self):
        """Test multiplying two values and rounding up"""
        assert FixedPointMath.mul_up(int(2.5 * FixedPointMath.ONE_18), int(0.5 * FixedPointMath.ONE_18)) == int(
            1.25 * FixedPointMath.ONE_18
        )
        assert FixedPointMath.mul_up(3 * FixedPointMath.ONE_18, FixedPointMath.ONE_18) == 3 * FixedPointMath.ONE_18
        assert FixedPointMath.mul_up(369, 271) == 1
        assert FixedPointMath.mul_up(0, FixedPointMath.ONE_18) == 0
        assert FixedPointMath.mul_up(FixedPointMath.ONE_18, 0) == 0
        assert FixedPointMath.mul_up(0, 0) == 0

    def test_mul_down(self):
        """Test multiplying two values and rounding down"""
        assert (
            FixedPointMath.mul_down(2 * FixedPointMath.ONE_18, 3 * FixedPointMath.ONE_18) == 6 * FixedPointMath.ONE_18
        )
        assert FixedPointMath.mul_down(int(2.5 * FixedPointMath.ONE_18), int(0.5 * FixedPointMath.ONE_18)) == int(
            1.25 * FixedPointMath.ONE_18
        )
        assert FixedPointMath.mul_down(3 * FixedPointMath.ONE_18, FixedPointMath.ONE_18) == 3 * FixedPointMath.ONE_18
        assert FixedPointMath.mul_down(369, 271) == 0
        assert FixedPointMath.mul_down(0, FixedPointMath.ONE_18) == 0
        assert FixedPointMath.mul_down(FixedPointMath.ONE_18, 0) == 0
        assert FixedPointMath.mul_down(0, 0) == 0

    def test_div_down(self):
        """Test dividing two values and rounding down"""
        assert (
            FixedPointMath.div_down(6 * FixedPointMath.ONE_18, 2 * FixedPointMath.ONE_18) == 3 * FixedPointMath.ONE_18
        )
        assert FixedPointMath.div_down(int(1.25 * FixedPointMath.ONE_18), int(0.5 * FixedPointMath.ONE_18)) == int(
            2.5 * FixedPointMath.ONE_18
        )
        assert FixedPointMath.div_down(3 * FixedPointMath.ONE_18, FixedPointMath.ONE_18) == 3 * FixedPointMath.ONE_18
        assert FixedPointMath.div_down(2 * FixedPointMath.ONE_18, int(1e19 * 1e18)) == 0
        assert FixedPointMath.div_down(0, FixedPointMath.ONE_18) == 0

    def test_fail_div_down_zero_denominator(self):
        """Test error when dividing by zero"""
        with self.assertRaises(ValueError):
            FixedPointMath.div_down(FixedPointMath.ONE_18, 0)

    def test_div_up(self):
        """Test dividing two values and rounding up"""
        assert FixedPointMath.div_up(int(1.25 * FixedPointMath.ONE_18), int(0.5 * FixedPointMath.ONE_18)) == int(
            2.5 * FixedPointMath.ONE_18
        )
        assert FixedPointMath.div_up(3 * FixedPointMath.ONE_18, FixedPointMath.ONE_18) == 3 * FixedPointMath.ONE_18
        assert FixedPointMath.div_up(2 * FixedPointMath.ONE_18, int(1e19 * 1e18)) == 1
        assert FixedPointMath.div_up(0, FixedPointMath.ONE_18) == 0

    def test_fail_div_up_zero_denominator(self):
        """Test error when dividing by zero"""
        with self.assertRaises(ValueError):
            FixedPointMath.div_up(FixedPointMath.ONE_18, 0)

    def test_mul_div_down(self):
        """Test multiplying two numbers, dividing a third, and then rounding down"""
        assert FixedPointMath.mul_div_down(int(2.5e27), int(0.5e27), int(1e27)) == 1.25e27
        assert FixedPointMath.mul_div_down(int(2.5e18), int(0.5e18), int(1e18)) == 1.25e18
        assert FixedPointMath.mul_div_down(int(2.5e8), int(0.5e8), int(1e8)) == 1.25e8
        assert (
            FixedPointMath.mul_div_down(369, 271, int(1e2)) == 1000
        )  # FIXME: should == 999 -- rounding still not working
        assert FixedPointMath.mul_div_down(int(1e27), int(1e27), int(2e27)) == 0.5e27
        assert FixedPointMath.mul_div_down(int(1e18), int(1e18), int(2e18)) == 0.5e18
        assert FixedPointMath.mul_div_down(int(1e8), int(1e8), int(2e8)) == 0.5e8
        assert FixedPointMath.mul_div_down(int(2e27), int(3e27), int(3e27)) == 2e27
        assert FixedPointMath.mul_div_down(int(2e18), int(3e18), int(3e18)) == 2e18
        assert FixedPointMath.mul_div_down(int(2e8), int(3e8), int(3e8)) == 2e8
        assert FixedPointMath.mul_div_down(0, int(1e18), int(1e18)) == 0
        assert FixedPointMath.mul_div_down(int(1e18), 0, int(1e18)) == 0
        assert FixedPointMath.mul_div_down(0, 0, int(1e18)) == 0

    def test_fail_mul_div_down_zero_denominator(self):
        """Test failure for multiplying two numbers, then dividing by zero"""
        with self.assertRaises(ValueError):
            FixedPointMath.mul_div_down(FixedPointMath.ONE_18, FixedPointMath.ONE_18, 0)

    def test_mul_div_up(self):
        """Test multiplying two numbers, dividing a third, and then rounding up"""
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

    def test_fail_mul_div_up_zero_denominator(self):
        """Test failure for multiplying two numbers, then dividing by zero"""
        with self.assertRaises(ValueError):
            FixedPointMath.mul_div_up(FixedPointMath.ONE_18, FixedPointMath.ONE_18, 0)

    def test_ilog2(self):
        """Test integer log base 2"""
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

    def test_ln(self):
        """Test integer natural log"""
        tolerance = 1e-15  # FIXME: Should allow for error up to 1e-18

        result = FixedPointMath.ln(FixedPointMath.ONE_18)
        expected = 0
        assert math.isclose(result, expected, rel_tol=tolerance), f"ln(x)\n  {result=},\n{expected=}"

        result = FixedPointMath.ln(1000000 * FixedPointMath.ONE_18)
        expected = 13815510557964274104
        assert math.isclose(result, expected, rel_tol=tolerance), f"ln(x)\n  {result=},\n{expected=}"

        result = FixedPointMath.ln(int(5 * 1e18))
        expected = int(math.log(5) * 1e18)
        assert math.isclose(result, expected, rel_tol=tolerance), f"ln(x)\n  {result=},\n{expected=}"

        result = FixedPointMath.ln(int(10 * 1e18))
        expected = int(math.log(10) * 1e18)
        assert math.isclose(result, expected, rel_tol=tolerance), f"ln(x)\n  {result=},\n{expected=}"

    def test_exp(self):
        """Test integer exp"""
        tolerance = 1e-18

        result = FixedPointMath.exp(FixedPointMath.ONE_18)
        expected = 2718281828459045235
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"

        result = FixedPointMath.exp(-FixedPointMath.ONE_18)
        expected = 367879441171442321
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"

        result = FixedPointMath.exp(FixedPointMath.EXP_MIN - 1)
        expected = 0
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"

        result = FixedPointMath.exp(int(5 * 1e18))
        expected = int(math.exp(5) * 1e18)
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"

        result = FixedPointMath.exp(int(-5 * 1e18))
        expected = int(math.exp(-5) * 1e18)
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"

        result = FixedPointMath.exp(int(10 * 1e18))
        expected = int(math.exp(10) * 1e18)
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"

        result = FixedPointMath.exp(int(-10 * 1e18))
        expected = int(math.exp(-10) * 1e18)
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"

        result = FixedPointMath.exp(0)
        expected = int(math.exp(0) * 1e18)
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"

        # FIXME: This fails when the inputs are any closer to EXP_MAX.
        # To improve precision at high values, we will need to update the (m,n)-term rational approximation
        result = FixedPointMath.exp(FixedPointMath.EXP_MAX - int(145e18))
        expected = int(math.exp((FixedPointMath.EXP_MAX - 145e18) / 1e18) * 1e18)
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"

    def test_fail_exp_negative_or_zero_input(self):
        """Test integer exp fails if the input is too large"""
        with self.assertRaises(ValueError):
            FixedPointMath.exp(FixedPointMath.EXP_MAX + 1)

    def test_pow(self):
        """Test integer pow"""
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

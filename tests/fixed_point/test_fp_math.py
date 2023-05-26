"""FixedPoint class math tests inspired from solidity hyperdrive implementation"""
import math
import unittest

from elfpy.math import FixedPointMath, FixedPoint

# pylint: disable=unneeded-not


class TestFixedPointMath(unittest.TestCase):
    """Unit tests to verify that the fixed-point math implementations are correct."""

    ONE = FixedPoint("1.0")
    NEG_ONE = FixedPoint("-1.0")
    INF = FixedPoint("inf")
    NEG_INF = FixedPoint("-inf")
    NAN = FixedPoint("nan")

    def test_minimum(self):
        """Test minimum function"""
        assert FixedPointMath.minimum(0, 1) == 0
        assert FixedPointMath.minimum(-1, 1) == -1
        assert FixedPointMath.minimum(-1, -3) == -3
        assert FixedPointMath.minimum(-1.0, -3.0) == -3.0
        assert FixedPointMath.minimum(1.0, 3.0) == 1.0
        assert FixedPointMath.minimum(FixedPoint(1.0), FixedPoint(3.0)) == FixedPoint(1.0)
        assert FixedPointMath.minimum(FixedPoint("3.0"), FixedPoint(scaled_value=int(3e18 - 1e-17))) == FixedPoint(
            scaled_value=int(3e18 - 1e-17)
        )

    def test_minimum_nonfinite(self):
        """Test minimum method"""
        assert FixedPointMath.minimum(self.NAN, self.NEG_ONE).is_nan() is True
        assert FixedPointMath.minimum(self.NAN, self.INF).is_nan() is True
        assert FixedPointMath.minimum(self.ONE, self.INF) == self.ONE
        assert FixedPointMath.minimum(self.NEG_ONE, self.NEG_INF) == self.NEG_INF
        assert FixedPointMath.minimum(self.INF, self.NEG_INF) == self.NEG_INF

    def test_maximum(self):
        """Test maximum function"""
        assert FixedPointMath.maximum(0, 1) == 1
        assert FixedPointMath.maximum(-1, 1) == 1
        assert FixedPointMath.maximum(-1, -3) == -1
        assert FixedPointMath.maximum(-1.0, -3.0) == -1.0
        assert FixedPointMath.maximum(1.0, 3.0) == 3.0
        assert FixedPointMath.maximum(FixedPoint(1.0), FixedPoint(3.0)) == FixedPoint(3.0)
        assert FixedPointMath.maximum(FixedPoint("3.0"), FixedPoint(scaled_value=int(3e18 - 1e-17))) == FixedPoint(3.0)

    def test_maximum_nonfinite(self):
        """Test maximum method"""
        assert FixedPointMath.maximum(self.NAN, self.NEG_ONE).is_nan() is True
        assert FixedPointMath.maximum(self.NAN, self.INF).is_nan() is True
        assert FixedPointMath.maximum(self.ONE, self.INF) == self.INF
        assert FixedPointMath.maximum(self.NEG_ONE, self.NEG_INF) == self.NEG_ONE
        assert FixedPointMath.maximum(self.INF, self.NEG_INF) == self.INF

    def test_exp(self):
        """Test exp function"""
        tolerance = 1e-18
        result = FixedPointMath.exp(FixedPoint("1.0"))
        expected = FixedPoint(2718281828459045235)
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"
        result = FixedPointMath.exp(FixedPoint("-1.0"))
        expected = FixedPoint(367879441171442321)
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"
        result = FixedPointMath.exp(1)
        expected = int(math.exp(1))
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"
        result = FixedPointMath.exp(-1)
        expected = int(math.exp(-1))
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"
        result = FixedPointMath.exp(1.0)
        expected = math.exp(1.0)
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"
        result = FixedPointMath.exp(-1.0)
        expected = math.exp(-1.0)
        assert math.isclose(result, expected, rel_tol=tolerance), f"exp(x):\n  {result=},\n{expected=}"

    def test_exp_nonfinite(self):
        """Test exp method"""
        assert FixedPointMath.exp(self.NAN).is_nan() is True
        assert FixedPointMath.exp(self.INF) == self.INF
        assert FixedPointMath.exp(self.NEG_INF) == self.NEG_INF

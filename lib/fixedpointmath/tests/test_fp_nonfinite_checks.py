"""Tests for non-finite (inf or nan) operations with the FixedPoint datatype"""
import unittest

from fixedpointmath import FixedPoint


class TestFixedPointNonFinite(unittest.TestCase):
    r"""Unit tests to verify that the fixed-point non-finite implementations are correct.

    Unlike normal integers, the FixedPoint type
    """
    ZERO = FixedPoint("0.0")
    ONE = FixedPoint("1.0")
    NEG_ONE = FixedPoint("-1.0")
    EVEN_FINITE = FixedPoint("8.0")
    ODD_FINITE = FixedPoint("9.0")
    SMALL_FINITE = FixedPoint(999)
    INF = FixedPoint("inf")
    NEG_INF = FixedPoint("-inf")
    NAN = FixedPoint("nan")

    def test_is_nan(self):
        """Test that FixedPoint can detect if it is nan"""
        assert self.NAN.is_nan() is True
        assert self.INF.is_nan() is False
        assert self.NEG_INF.is_nan() is False
        assert self.EVEN_FINITE.is_nan() is False
        assert self.ONE.is_nan() is False

    def test_is_inf(self):
        """Test that FixedPoint can detect if it is + or - inf"""
        assert self.INF.is_inf() is True
        assert self.NEG_INF.is_inf() is True
        assert self.NAN.is_inf() is False
        assert self.EVEN_FINITE.is_inf() is False
        assert self.ONE.is_inf() is False

    def test_is_zero(self):
        """Test that FixedPoint can detect if it is 0"""
        assert self.ZERO.is_zero() is True
        assert self.ONE.is_zero() is False
        assert self.NAN.is_zero() is False
        assert self.INF.is_zero() is False
        assert self.NEG_INF.is_zero() is False

    def test_is_finite(self):
        """Test that FixedPoint can detect if it is not inf or nan"""
        assert self.ZERO.is_finite() is True
        assert self.SMALL_FINITE.is_finite() is True
        assert self.NAN.is_finite() is False
        assert self.INF.is_finite() is False
        assert self.NEG_INF.is_finite() is False

    def test_sign_nonfinite(self):
        """Test that FixedPoint knows its sign"""
        assert self.ONE.sign() == FixedPoint("1.0")
        assert self.NEG_ONE.sign() == FixedPoint("-1.0")
        assert self.INF.sign() == FixedPoint("1.0")
        assert self.NEG_INF.sign() == FixedPoint("-1.0")
        assert self.NAN.sign().is_nan() is True
        assert self.ZERO.sign() == self.ZERO

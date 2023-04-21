"""Tests for non-finite (inf or nan) operations with the FixedPoint datatype"""

import unittest

from elfpy.utils.math import FixedPoint

# pylint: disable=unneeded-not


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
    NAN = FixedPoint("nan")
    INF = FixedPoint("inf")
    NEG_INF = FixedPoint("-inf")

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

    def test_sign(self):
        """Test that FixedPoint knows its sign"""
        assert self.ONE.sign() == FixedPoint("1.0")
        assert self.NEG_ONE.sign() == FixedPoint("-1.0")
        assert self.INF.sign() == FixedPoint("1.0")
        assert self.NEG_INF.sign() == FixedPoint("-1.0")
        assert self.NAN.sign().is_nan() is True
        assert self.ZERO.sign() == self.ZERO

    def test_eq(self):
        """Test that FixedPoint non-finite values can be equal"""
        assert not self.NAN == self.NAN
        assert self.INF == self.INF
        assert self.NEG_INF == self.NEG_INF

    def test_ne(self):
        """Test that FixedPoint non-finite values can be non-equal"""
        assert self.NAN != self.NAN
        assert not self.INF != self.INF
        assert not self.NEG_INF != self.NEG_INF
        assert self.NEG_INF != self.INF

    def test_lt(self):
        """Test that FixedPoint non-finite values handle less than"""
        assert not self.NAN < self.NAN
        assert not self.NAN < self.ODD_FINITE
        assert not self.ODD_FINITE < self.NAN
        assert not self.INF < self.NAN
        assert not self.NAN < self.INF
        assert not self.INF < self.ODD_FINITE
        assert not self.INF < self.INF
        assert not self.INF < self.NEG_INF
        assert not self.NEG_INF < self.NEG_INF
        assert self.NEG_INF < self.INF
        assert self.NEG_INF < self.ODD_FINITE
        assert self.ODD_FINITE < self.INF

    def test_le(self):
        """Test that FixedPoint non-finite values handle less than"""
        assert not self.NAN <= self.NAN
        assert not self.NAN <= self.ODD_FINITE
        assert not self.ODD_FINITE <= self.NAN
        assert not self.INF <= self.NAN
        assert not self.NAN <= self.INF
        assert not self.INF <= self.ODD_FINITE
        assert not self.INF <= self.NEG_INF
        assert self.INF <= self.INF
        assert self.NEG_INF <= self.NEG_INF
        assert self.NEG_INF <= self.INF
        assert self.NEG_INF <= self.ODD_FINITE
        assert self.ODD_FINITE <= self.INF

    def test_gt(self):
        """Test that FixedPoint non-finite values handle less than"""
        assert not self.NAN > self.NAN
        assert not self.ODD_FINITE > self.NAN
        assert not self.NAN > self.ODD_FINITE
        assert not self.NAN > self.INF
        assert not self.INF > self.NAN
        assert not self.ODD_FINITE > self.INF
        assert not self.NEG_INF > self.INF
        assert not self.INF > self.INF
        assert not self.NEG_INF > self.NEG_INF
        assert self.INF > self.NEG_INF
        assert self.ODD_FINITE > self.NEG_INF
        assert self.INF > self.ODD_FINITE

    def test_ge(self):
        """Test that FixedPoint non-finite values handle less than"""
        assert not self.NAN >= self.NAN
        assert not self.ODD_FINITE >= self.NAN
        assert not self.NAN >= self.ODD_FINITE
        assert not self.NAN >= self.INF
        assert not self.INF >= self.NAN
        assert not self.ODD_FINITE >= self.INF
        assert not self.NEG_INF >= self.INF
        assert self.INF >= self.INF
        assert self.NEG_INF >= self.NEG_INF
        assert self.INF >= self.NEG_INF
        assert self.ODD_FINITE >= self.NEG_INF
        assert self.INF >= self.ODD_FINITE

    def test_add(self):
        """Test rules for non-finite addition"""
        # nan + anything is nan
        assert (self.NAN + self.ZERO).is_nan() is True
        assert (self.NAN + self.ONE).is_nan() is True
        assert (self.NAN + self.EVEN_FINITE).is_nan() is True
        assert (self.NAN + self.NAN).is_nan() is True
        assert (self.NAN + self.INF).is_nan() is True
        assert (self.NAN + self.NEG_INF).is_nan() is True
        # anything + nan is nan
        assert (self.ZERO + self.NAN).is_nan() is True
        assert (self.ONE + self.NAN).is_nan() is True
        assert (self.EVEN_FINITE + self.NAN).is_nan() is True
        assert (self.NAN + self.NAN).is_nan() is True
        assert (self.INF + self.NAN).is_nan() is True
        assert (self.NEG_INF + self.NAN).is_nan() is True
        # inf + -inf is nan
        assert (self.INF + self.NEG_INF).is_nan() is True
        assert (self.NEG_INF + self.INF).is_nan() is True
        # inf + finite is inf
        assert self.INF + self.EVEN_FINITE == self.INF
        assert self.EVEN_FINITE + self.INF == self.INF
        assert self.NEG_INF + self.EVEN_FINITE == self.NEG_INF
        assert self.EVEN_FINITE + self.NEG_INF == self.NEG_INF
        # inf + inf is inf
        assert self.INF + self.INF == self.INF
        # -inf + -inf is -inf
        assert self.NEG_INF + self.NEG_INF == self.NEG_INF

    def test_sub(self):
        """Test rules for non-finite subtraction"""
        # nan - anything is nan
        assert (self.NAN - self.ZERO).is_nan() is True
        assert (self.NAN - self.ONE).is_nan() is True
        assert (self.NAN - self.EVEN_FINITE).is_nan() is True
        assert (self.NAN - self.NAN).is_nan() is True
        assert (self.NAN - self.INF).is_nan() is True
        assert (self.NAN - self.NEG_INF).is_nan() is True
        # anything - nan is nan
        assert (self.ZERO - self.NAN).is_nan() is True
        assert (self.ONE - self.NAN).is_nan() is True
        assert (self.EVEN_FINITE - self.NAN).is_nan() is True
        assert (self.NAN - self.NAN).is_nan() is True
        assert (self.INF - self.NAN).is_nan() is True
        assert (self.NEG_INF - self.NAN).is_nan() is True
        # same sign is nan
        assert (self.INF - self.INF).is_nan() is True
        assert (self.NEG_INF - self.NEG_INF).is_nan() is True
        # opposite sign take the sign of the minuend
        assert self.INF - self.NEG_INF == self.INF
        assert self.NEG_INF - self.INF == self.NEG_INF
        # inf wins over finite values
        assert self.EVEN_FINITE - self.INF == self.NEG_INF
        assert self.INF - self.EVEN_FINITE == self.INF
        assert self.EVEN_FINITE - self.NEG_INF == self.INF
        assert self.NEG_INF - self.EVEN_FINITE == self.NEG_INF

    def test_mul(self):
        """Test rules for non-finite multiplication"""
        # nan * anything is nan
        assert (self.NAN * self.ZERO).is_nan() is True
        assert (self.NAN * self.ONE).is_nan() is True
        assert (self.NAN * self.EVEN_FINITE).is_nan() is True
        assert (self.NAN * self.NAN).is_nan() is True
        assert (self.NAN * self.INF).is_nan() is True
        assert (self.NAN * self.NEG_INF).is_nan() is True
        # anything * nan is nan
        assert (self.ZERO * self.NAN).is_nan() is True
        assert (self.ONE * self.NAN).is_nan() is True
        assert (self.EVEN_FINITE * self.NAN).is_nan() is True
        assert (self.NAN * self.NAN).is_nan() is True
        assert (self.INF * self.NAN).is_nan() is True
        assert (self.NEG_INF * self.NAN).is_nan() is True
        # anything (besides -inf, zero) * inf = inf
        assert self.ONE * self.INF == self.INF
        assert self.EVEN_FINITE * self.INF == self.INF
        assert self.INF * self.ONE == self.INF
        assert self.INF * self.EVEN_FINITE == self.INF
        assert self.INF * self.INF == self.INF
        # anything (besides -inf, zero) * -inf = -inf
        assert self.ONE * self.NEG_INF == self.NEG_INF
        assert self.EVEN_FINITE * self.NEG_INF == self.NEG_INF
        assert self.INF * self.NEG_INF == self.NEG_INF
        assert self.NEG_INF * self.ONE == self.NEG_INF
        assert self.NEG_INF * self.EVEN_FINITE == self.NEG_INF
        assert self.NEG_INF * self.INF == self.NEG_INF
        # -inf * -inf = inf
        assert self.NEG_INF * self.NEG_INF == self.INF
        # inf * 0 is nan; -inf * 0 is nan
        assert (self.INF * self.ZERO).is_nan() is True
        assert (self.NEG_INF * self.ZERO).is_nan() is True

    def test_div(self):
        """Test rules for non-finite division"""
        # nan / anything is nan
        assert (self.NAN / self.ONE).is_nan() is True
        assert (self.NAN / self.EVEN_FINITE).is_nan() is True
        assert (self.NAN / self.NAN).is_nan() is True
        assert (self.NAN / self.INF).is_nan() is True
        assert (self.NAN / self.NEG_INF).is_nan() is True
        # anything / nan is nan
        assert (self.ZERO / self.NAN).is_nan() is True
        assert (self.ONE / self.NAN).is_nan() is True
        assert (self.EVEN_FINITE / self.NAN).is_nan() is True
        assert (self.NAN / self.NAN).is_nan() is True
        assert (self.INF / self.NAN).is_nan() is True
        assert (self.NEG_INF / self.NAN).is_nan() is True
        # inf / inf is nan, regardless of sign
        assert (self.INF / self.INF).is_nan() is True
        assert (self.NEG_INF / self.NEG_INF).is_nan() is True
        assert (self.NEG_INF / self.INF).is_nan() is True
        assert (self.INF / self.NEG_INF).is_nan() is True
        # inf wins over finite
        assert self.INF / self.EVEN_FINITE == self.INF
        assert self.NEG_INF / self.EVEN_FINITE == self.NEG_INF
        # div by inf is zero
        assert self.EVEN_FINITE / self.INF == self.ZERO
        assert self.EVEN_FINITE / self.NEG_INF == self.ZERO

    def test_pow(self):
        """Test rules for non-finite division"""
        # nan ** anything (besides zero) is nan
        assert (self.NAN**self.ONE).is_nan() is True
        assert (self.NAN**self.EVEN_FINITE).is_nan() is True
        assert (self.NAN**self.NAN).is_nan() is True
        assert (self.NAN**self.INF).is_nan() is True
        assert (self.NAN**self.NEG_INF).is_nan() is True
        # anything ** nan is nan
        assert (self.ZERO**self.NAN).is_nan() is True
        assert (self.EVEN_FINITE**self.NAN).is_nan() is True
        assert (self.NAN**self.NAN).is_nan() is True
        assert (self.INF**self.NAN).is_nan() is True
        assert (self.NEG_INF**self.NAN).is_nan() is True
        # 1 ** anything is 1
        assert self.ONE**self.INF == self.ONE
        assert self.ONE**self.NEG_INF == self.ONE
        assert self.ONE**self.NAN == self.ONE
        assert self.ONE**self.EVEN_FINITE == self.ONE
        # -1 ** inf or neg inf is 1
        assert self.NEG_ONE**self.INF == self.ONE
        assert self.NEG_ONE**self.NEG_INF == self.ONE
        # anything ** 0 is 1
        assert self.ZERO**self.ZERO == self.ONE
        assert self.EVEN_FINITE**self.ZERO == self.ONE
        assert self.NAN**self.ZERO == self.ONE
        assert self.INF**self.ZERO == self.ONE
        assert self.NEG_INF**self.ZERO == self.ONE
        # 0 ** finite is 0
        assert self.ZERO**self.EVEN_FINITE == self.ZERO
        # inf base
        assert self.INF**self.ONE == self.INF
        assert self.INF**self.NEG_ONE == self.ZERO
        # -inf base
        assert self.NEG_INF ** (self.ONE * self.ODD_FINITE) == self.NEG_INF
        assert self.NEG_INF ** (self.ONE * self.EVEN_FINITE) == self.INF
        assert self.NEG_INF ** (self.NEG_ONE * self.ODD_FINITE) == self.ZERO
        assert self.NEG_INF ** (self.NEG_ONE * self.EVEN_FINITE) == self.ZERO
        # small base, -inf exp
        assert self.SMALL_FINITE**self.NEG_INF == self.INF
        assert self.SMALL_FINITE**self.INF == self.ZERO

    def test_modulo(self):
        """Test rules for non-finite modulo operation"""
        # nan % anything is nan
        assert (self.NAN % self.ONE).is_nan() is True
        assert (self.NAN % self.EVEN_FINITE).is_nan() is True
        assert (self.NAN % self.NAN).is_nan() is True
        assert (self.NAN % self.INF).is_nan() is True
        assert (self.NAN % self.NEG_INF).is_nan() is True
        # anything % nan is nan
        assert (self.ZERO % self.NAN).is_nan() is True
        assert (self.ONE % self.NAN).is_nan() is True
        assert (self.EVEN_FINITE % self.NAN).is_nan() is True
        assert (self.NAN % self.NAN).is_nan() is True
        assert (self.INF % self.NAN).is_nan() is True
        assert (self.NEG_INF % self.NAN).is_nan() is True
        # finite % (+/-) inf is finite
        assert self.EVEN_FINITE % self.INF == self.EVEN_FINITE
        assert self.EVEN_FINITE % self.NEG_INF == self.EVEN_FINITE
        # (+/-) inf % anything is nan
        assert (self.INF % self.EVEN_FINITE).is_nan() is True
        assert (self.INF % self.INF).is_nan() is True
        assert (self.INF % self.SMALL_FINITE).is_nan() is True
        assert (self.INF % self.NEG_INF).is_nan() is True
        assert (self.NEG_INF % self.EVEN_FINITE).is_nan() is True
        assert (self.NEG_INF % self.INF).is_nan() is True
        assert (self.NEG_INF % self.NEG_INF).is_nan() is True

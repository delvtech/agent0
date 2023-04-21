"""Tests for non-finite (inf or nan) operations with the FixedPoint datatype"""

import unittest

from elfpy.utils.math import FixedPoint


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

    def test_add(self):
        """Test rules for non-finite addition"""
        # nan + anything is nan
        assert self.NAN + self.ZERO == self.NAN
        assert self.NAN + self.ONE == self.NAN
        assert self.NAN + self.EVEN_FINITE == self.NAN
        assert self.NAN + self.NAN == self.NAN
        assert self.NAN + self.INF == self.NAN
        assert self.NAN + self.NEG_INF == self.NAN
        # anything + nan is nan
        assert self.ZERO + self.NAN == self.NAN
        assert self.ONE + self.NAN == self.NAN
        assert self.EVEN_FINITE + self.NAN == self.NAN
        assert self.NAN + self.NAN == self.NAN
        assert self.INF + self.NAN == self.NAN
        assert self.NEG_INF + self.NAN == self.NAN
        # inf + -inf is nan
        assert self.INF + self.NEG_INF == self.NAN
        assert self.NEG_INF + self.INF == self.NAN
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
        assert self.NAN - self.ZERO == self.NAN
        assert self.NAN - self.ONE == self.NAN
        assert self.NAN - self.EVEN_FINITE == self.NAN
        assert self.NAN - self.NAN == self.NAN
        assert self.NAN - self.INF == self.NAN
        assert self.NAN - self.NEG_INF == self.NAN
        # anything - nan is nan
        assert self.ZERO - self.NAN == self.NAN
        assert self.ONE - self.NAN == self.NAN
        assert self.EVEN_FINITE - self.NAN == self.NAN
        assert self.NAN - self.NAN == self.NAN
        assert self.INF - self.NAN == self.NAN
        assert self.NEG_INF - self.NAN == self.NAN
        # same sign is nan
        assert self.INF - self.INF == self.NAN
        assert self.NEG_INF - self.NEG_INF == self.NAN
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
        assert self.NAN * self.ZERO == self.NAN
        assert self.NAN * self.ONE == self.NAN
        assert self.NAN * self.EVEN_FINITE == self.NAN
        assert self.NAN * self.NAN == self.NAN
        assert self.NAN * self.INF == self.NAN
        assert self.NAN * self.NEG_INF == self.NAN
        # anything * nan is nan
        assert self.ZERO * self.NAN == self.NAN
        assert self.ONE * self.NAN == self.NAN
        assert self.EVEN_FINITE * self.NAN == self.NAN
        assert self.NAN * self.NAN == self.NAN
        assert self.INF * self.NAN == self.NAN
        assert self.NEG_INF * self.NAN == self.NAN
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
        assert self.INF * self.ZERO == self.NAN
        assert self.NEG_INF * self.ZERO == self.NAN

    def test_div(self):
        """Test rules for non-finite division"""
        # nan / anything is nan
        assert self.NAN / self.ONE == self.NAN
        assert self.NAN / self.EVEN_FINITE == self.NAN
        assert self.NAN / self.NAN == self.NAN
        assert self.NAN / self.INF == self.NAN
        assert self.NAN / self.NEG_INF == self.NAN
        # anything / nan is nan
        assert self.ZERO / self.NAN == self.NAN
        assert self.ONE / self.NAN == self.NAN
        assert self.EVEN_FINITE / self.NAN == self.NAN
        assert self.NAN / self.NAN == self.NAN
        assert self.INF / self.NAN == self.NAN
        assert self.NEG_INF / self.NAN == self.NAN
        # inf / inf is nan, regardless of sign
        assert self.INF / self.INF == self.NAN
        assert self.NEG_INF / self.NEG_INF == self.NAN
        assert self.NEG_INF / self.INF == self.NAN
        assert self.INF / self.NEG_INF == self.NAN
        # inf wins over finite
        assert self.INF / self.EVEN_FINITE == self.INF
        assert self.NEG_INF / self.EVEN_FINITE == self.NEG_INF
        # div by inf is zero
        assert self.EVEN_FINITE / self.INF == self.ZERO
        assert self.EVEN_FINITE / self.NEG_INF == self.ZERO

    def test_pow(self):
        """Test rules for non-finite division"""
        # nan ** anything (besides zero) is nan
        assert self.NAN**self.ONE == self.NAN
        assert self.NAN**self.EVEN_FINITE == self.NAN
        assert self.NAN**self.NAN == self.NAN
        assert self.NAN**self.INF == self.NAN
        assert self.NAN**self.NEG_INF == self.NAN
        # anything ** nan is nan
        assert self.ZERO**self.NAN == self.NAN
        assert self.EVEN_FINITE**self.NAN == self.NAN
        assert self.NAN**self.NAN == self.NAN
        assert self.INF**self.NAN == self.NAN
        assert self.NEG_INF**self.NAN == self.NAN
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

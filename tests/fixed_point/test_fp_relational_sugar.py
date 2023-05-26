"""Tests for relational (comparison) syntax sugar with the FixedPoint class"""
import unittest

from elfpy.math import FixedPoint

# pylint: disable=unneeded-not


class TestFixedPointNonFinite(unittest.TestCase):
    r"""Unit tests to verify that the fixed-point non-finite implementations are correct.

    Unlike normal integers, the FixedPoint type
    """
    ONE = FixedPoint("1.0")
    NEG_ONE = FixedPoint("-1.0")
    ODD_FINITE = FixedPoint("9.0")
    SMALL_FINITE = FixedPoint(scaled_value=999)
    INF = FixedPoint("inf")
    NEG_INF = FixedPoint("-inf")
    NAN = FixedPoint("nan")

    def test_eq(self):
        r"""Test `==` sugar"""
        assert self.NEG_ONE == FixedPoint("-1.0")
        assert not self.NEG_ONE == self.ONE

    def test_eq_nonfinite(self):
        """Test that FixedPoint non-finite values can be equal"""
        assert not self.NAN == self.NAN
        assert self.INF == self.INF
        assert self.NEG_INF == self.NEG_INF

    def test_ne(self):
        r"""Test `!=` sugar"""
        assert self.NEG_ONE != self.ONE
        assert not self.ONE != FixedPoint("1.0")

    def test_ne_nonfinite(self):
        """Test that FixedPoint non-finite values can be non-equal"""
        assert self.NAN != self.NAN
        assert not self.INF != self.INF
        assert not self.NEG_INF != self.NEG_INF
        assert self.NEG_INF != self.INF

    def test_lt(self):
        r"""Test `<` sugar"""
        assert self.SMALL_FINITE < self.ONE
        assert not self.ONE < self.SMALL_FINITE

    def test_lt_nonfinite(self):
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
        r"""Test `<=` sugar"""
        assert self.SMALL_FINITE <= self.SMALL_FINITE
        assert self.SMALL_FINITE <= self.ONE
        assert not self.ONE <= self.SMALL_FINITE

    def test_le_nonfinite(self):
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
        r"""Test `>` sugar"""
        assert self.ONE > self.SMALL_FINITE
        assert not self.SMALL_FINITE > self.ONE

    def test_gt_nonfinite(self):
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
        r"""Test `>=` sugar"""
        assert self.ONE >= self.ONE
        assert self.ONE >= self.SMALL_FINITE
        assert not self.SMALL_FINITE >= self.ONE

    def test_ge_nonfinite(self):
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

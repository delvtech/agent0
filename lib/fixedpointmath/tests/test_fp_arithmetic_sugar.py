"""Tests for arethmetic syntax sugar with the FixedPoint class"""
import unittest

from fixedpointmath import errors
from fixedpointmath import FixedPoint


# pylint: disable=unneeded-not


class TestFixedPoint(unittest.TestCase):
    r"""Unit tests to verify that syntactic sugar for the FixedPoint class is correct.

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
    ZERO = FixedPoint("0.0")
    ONE = FixedPoint("1.0")
    NEG_ONE = FixedPoint("-1.0")
    EVEN_FINITE = FixedPoint("8.0")
    ODD_FINITE = FixedPoint("9.0")
    SMALL_FINITE = FixedPoint(999e-18)
    INF = FixedPoint("inf")
    NEG_INF = FixedPoint("-inf")
    NAN = FixedPoint("nan")

    def test_add(self):
        r"""Test `+` sugar for various type combos"""
        # int + int
        assert FixedPoint(5) + FixedPoint(5) == FixedPoint(10)
        assert int(FixedPoint(5) + FixedPoint(5)) == 10
        # int + float
        assert int(FixedPoint(5) + FixedPoint(5.0)) == 5 + 5.0
        # float + float
        assert FixedPoint(5.0) + FixedPoint(5.0) == FixedPoint(10.0)
        assert float(FixedPoint(5.0) + FixedPoint(5.0)) == 10.0
        # float + int
        assert int(FixedPoint(5.0) + FixedPoint(5)) == 5.0 + 5
        # str + str
        assert FixedPoint("5.0") + FixedPoint("5.025") == FixedPoint("10.025")
        assert float(FixedPoint("5.0") + FixedPoint("5.0")) == 10.0
        # bool + FP and FP + bool
        assert False + self.ONE == self.ONE
        assert True + self.ONE == self.ONE + self.ONE
        assert self.ONE + False == self.ONE
        assert self.ONE + True == self.ONE + self.ONE
        # mixed type
        assert self.ONE + 1 == FixedPoint("2.0")
        assert 1 + self.ONE == FixedPoint("2.0")

    def test_add_fail(self):
        r"""Test failure of `+` sugar

        We are ignoring type errors -- we know they're bad, but we're looking for failure
        """
        with self.assertRaises(OverflowError):
            _ = FixedPoint(2**256) + FixedPoint(1)
        with self.assertRaises(TypeError):
            _ = self.ONE + 1.0  # type: ignore
        with self.assertRaises(TypeError):
            _ = 1.0 + self.ONE  # type: ignore

    def test_add_nonfinite(self):
        """Test rules for non-finite addition"""
        # nan + anything is nan
        assert (self.NAN + self.ZERO).is_nan() is True
        assert (self.NAN + self.ONE).is_nan() is True
        assert (self.NAN + self.EVEN_FINITE).is_nan() is True
        assert (self.NAN + self.NAN).is_nan() is True
        assert (self.NAN + self.INF).is_nan() is True
        assert (self.NAN + self.NEG_INF).is_nan() is True
        assert (self.NAN + True).is_nan() is True
        assert (self.NAN + False).is_nan() is True
        # anything + nan is nan
        assert (self.ZERO + self.NAN).is_nan() is True
        assert (self.ONE + self.NAN).is_nan() is True
        assert (self.EVEN_FINITE + self.NAN).is_nan() is True
        assert (self.NAN + self.NAN).is_nan() is True
        assert (self.INF + self.NAN).is_nan() is True
        assert (self.NEG_INF + self.NAN).is_nan() is True
        assert (True + self.NAN).is_nan() is True
        assert (False + self.NAN).is_nan() is True
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
        # bool + inf
        assert False + self.INF == self.INF
        assert True + self.INF == self.INF
        assert False + self.NEG_INF == self.NEG_INF
        assert True + self.NEG_INF == self.NEG_INF
        assert not bool((self.EVEN_FINITE == self.INF) + self.INF)

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
        # bool - FP
        assert False - self.ONE == self.NEG_ONE
        assert True - self.ONE == self.ZERO
        assert self.ONE - False == self.ONE
        assert self.ONE - True == self.ZERO
        # mixed type
        assert self.ONE - 1 == self.ZERO
        assert 1 - self.ONE == self.ZERO
        assert True - self.ONE == self.ZERO

    def test_sub_fail(self):
        r"""Test failure of `-` sugar

        We are ignoring type errors -- we know they're bad, but we're looking for failure
        """
        with self.assertRaises(OverflowError):
            _ = FixedPoint(-(2**255)) - FixedPoint(1)
        with self.assertRaises(TypeError):
            _ = self.ONE - 1.0  # type: ignore
            _ = 1.0 - self.ONE  # type: ignore

    def test_sub_nonfinite(self):
        """Test rules for non-finite subtraction"""
        # nan - anything is nan
        assert (self.NAN - self.ZERO).is_nan() is True
        assert (self.NAN - self.ONE).is_nan() is True
        assert (self.NAN - self.EVEN_FINITE).is_nan() is True
        assert (self.NAN - self.NAN).is_nan() is True
        assert (self.NAN - self.INF).is_nan() is True
        assert (self.NAN - self.NEG_INF).is_nan() is True
        assert (self.NAN - True).is_nan() is True
        assert (self.NAN - False).is_nan() is True
        # anything - nan is nan
        assert (self.ZERO - self.NAN).is_nan() is True
        assert (self.ONE - self.NAN).is_nan() is True
        assert (self.EVEN_FINITE - self.NAN).is_nan() is True
        assert (self.NAN - self.NAN).is_nan() is True
        assert (self.INF - self.NAN).is_nan() is True
        assert (self.NEG_INF - self.NAN).is_nan() is True
        assert (True - self.NAN).is_nan() is True
        assert (False - self.NAN).is_nan() is True
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
        # bool - inf
        assert False - self.INF == self.NEG_INF
        assert True - self.INF == self.NEG_INF

    def test_multiply(self):
        r"""Test `*` sugar for various type combos"""
        # int * int
        # NOTE: multiply divides by 1e18, so this is 5 * 5 / 1e18 which rounds to zero
        for scale in range(0, 8):
            assert int(FixedPoint(scaled_value=5 * 10**scale) * FixedPoint(scaled_value=5 * 10**scale)) == 0
        assert int(FixedPoint(5)) * int(FixedPoint(5)) == 25
        assert int(FixedPoint(5)) * 5 == 25
        assert FixedPoint(5 * 10**9) * FixedPoint(5 * 10**9) == FixedPoint(25 * 10**18)
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
        # bool * FP and FP * bool
        assert False * self.ONE == self.ZERO
        assert True * self.ONE == self.ONE
        assert self.ONE * False == self.ZERO
        assert self.ONE * True == self.ONE
        # mixed type
        assert self.ONE * 1 == self.ONE
        assert 1 * self.ONE == self.ONE
        assert self.ONE * True == self.ONE
        assert True * self.ONE == self.ONE
        assert self.ONE * False == self.ZERO
        assert False * self.ONE == self.ZERO

    def test_multiply_fail(self):
        r"""Test failure of `*` sugar

        We are ignoring type errors -- we know they're bad, but we're looking for failure
        """
        with self.assertRaises(TypeError):
            _ = self.ONE * 1.0  # type: ignore
        with self.assertRaises(TypeError):
            _ = 1.0 * self.ONE  # type: ignore

    def test_multiply_nonfinite(self):
        """Test rules for non-finite multiplication"""
        # nan * anything is nan
        assert (self.NAN * self.ZERO).is_nan() is True
        assert (self.NAN * self.ONE).is_nan() is True
        assert (self.NAN * self.EVEN_FINITE).is_nan() is True
        assert (self.NAN * self.NAN).is_nan() is True
        assert (self.NAN * self.INF).is_nan() is True
        assert (self.NAN * self.NEG_INF).is_nan() is True
        assert (self.NAN * True).is_nan() is True
        assert (self.NAN * False).is_nan() is True
        # anything * nan is nan
        assert (self.ZERO * self.NAN).is_nan() is True
        assert (self.ONE * self.NAN).is_nan() is True
        assert (self.EVEN_FINITE * self.NAN).is_nan() is True
        assert (self.NAN * self.NAN).is_nan() is True
        assert (self.INF * self.NAN).is_nan() is True
        assert (self.NEG_INF * self.NAN).is_nan() is True
        assert (True * self.NAN).is_nan() is True
        assert (False * self.NAN).is_nan() is True
        # anything (besides -inf, zero) * inf = inf
        assert self.ONE * self.INF == self.INF
        assert self.EVEN_FINITE * self.INF == self.INF
        assert self.INF * self.ONE == self.INF
        assert self.INF * self.EVEN_FINITE == self.INF
        assert self.INF * self.INF == self.INF
        assert self.INF * self.NEG_INF == self.NEG_INF
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
        assert (self.INF * False).is_nan() is True
        assert (self.NEG_INF * self.ZERO).is_nan() is True
        assert (self.NEG_INF * False).is_nan() is True
        # True does not affect inf or -inf
        assert self.INF * True == self.INF
        assert self.NEG_INF * True == self.NEG_INF
        assert True * self.INF == self.INF
        assert True * self.NEG_INF == self.NEG_INF

    def test_divide(self):
        r"""Test `/` sugar for various type combos"""
        # int / int
        assert int(FixedPoint(5) / FixedPoint(5)) == 1
        assert int(FixedPoint(5)) / 5 == 1
        assert 5 / int(FixedPoint(5)) == 1
        assert float(FixedPoint(5)) / 5 == 1
        # scaling both numerator & denominator shouldn't change the outcome
        assert FixedPoint(5) / FixedPoint(7) == FixedPoint(scaled_value=714285714285714285)
        assert FixedPoint(50) / FixedPoint(70) == FixedPoint(scaled_value=714285714285714285)
        assert FixedPoint(500) / FixedPoint(700) == FixedPoint(scaled_value=714285714285714285)
        # int / float
        assert int(FixedPoint(5) / FixedPoint(5.0)) == 1
        # float / float
        assert FixedPoint(5.0) / FixedPoint(5.0) == FixedPoint(1.0)
        assert float(FixedPoint(5.0) / FixedPoint(5.0)) == 1.0
        # float / int
        assert int(FixedPoint(1.0) / FixedPoint(1)) == 1
        # str / str
        assert FixedPoint("5.0") / FixedPoint("5.0") == FixedPoint("1.0")
        assert float(FixedPoint("6.0") / FixedPoint("2.5")) == 2.4
        assert float(FixedPoint("6.0") / FixedPoint("100.0")) == 0.06
        assert float(FixedPoint("0.006") / FixedPoint("0.001")) == 6
        # div rounding
        assert FixedPoint(scaled_value=2 * 10**18) / FixedPoint(scaled_value=1 * 10**37) == FixedPoint(
            scaled_value=0
        )
        assert FixedPoint(scaled_value=2 * 10**18).div_up(FixedPoint(scaled_value=1 * 10**37)) == FixedPoint(
            scaled_value=1
        )
        # bool / FP and FP / bool
        assert False / self.ONE == self.ZERO
        assert True / self.ONE == self.ONE
        assert self.ONE / True == self.ONE
        # mixed type
        assert self.ONE / 1 == self.ONE
        assert 1 / self.ONE == self.ONE
        assert self.ONE / True == self.ONE
        assert True / self.ONE == self.ONE

    def test_divide_fail(self):
        r"""Test failure of `/` sugar

        We are ignoring type errors -- we know they're bad, but we're looking for failure
        """
        with self.assertRaises(errors.DivisionByZero):
            _ = self.ONE / self.ZERO
        with self.assertRaises(errors.DivisionByZero):
            _ = self.ONE / False
        with self.assertRaises(TypeError):
            _ = self.ONE / 1.0  # type: ignore
        with self.assertRaises(TypeError):
            _ = 1.0 / self.ONE  # type: ignore

    def test_divide_nonfinite(self):
        """Test rules for non-finite division"""
        # nan / anything is nan (except 0, which throws an error)
        assert (self.NAN / self.ONE).is_nan() is True
        assert (self.NAN / self.EVEN_FINITE).is_nan() is True
        assert (self.NAN / self.NAN).is_nan() is True
        assert (self.NAN / self.INF).is_nan() is True
        assert (self.NAN / self.NEG_INF).is_nan() is True
        assert (self.NAN / True).is_nan() is True
        # anything / nan is nan
        assert (self.ZERO / self.NAN).is_nan() is True
        assert (self.ONE / self.NAN).is_nan() is True
        assert (self.EVEN_FINITE / self.NAN).is_nan() is True
        assert (self.NAN / self.NAN).is_nan() is True
        assert (self.INF / self.NAN).is_nan() is True
        assert (self.NEG_INF / self.NAN).is_nan() is True
        assert (True / self.NAN).is_nan() is True
        assert (False / self.NAN).is_nan() is True
        # inf / inf is nan, regardless of sign
        assert (self.INF / self.INF).is_nan() is True
        assert (self.NEG_INF / self.NEG_INF).is_nan() is True
        assert (self.NEG_INF / self.INF).is_nan() is True
        assert (self.INF / self.NEG_INF).is_nan() is True
        # inf wins over finite
        assert self.INF / self.EVEN_FINITE == self.INF
        assert self.NEG_INF / self.EVEN_FINITE == self.NEG_INF
        assert self.INF / True == self.INF
        assert self.NEG_INF / True == self.NEG_INF
        # div by inf is zero
        assert self.EVEN_FINITE / self.INF == self.ZERO
        assert self.EVEN_FINITE / self.NEG_INF == self.ZERO
        assert True / self.NEG_INF == self.ZERO

    def test_floor_divide(self):
        r"""Test `//` sugar"""
        assert FixedPoint("6.3") // FixedPoint("2.0") == FixedPoint("3.0")
        assert FixedPoint("8.0") // FixedPoint("2.0") == FixedPoint("4.0")
        assert FixedPoint("8.0") // FixedPoint("5.0") == FixedPoint("1.0")
        assert FixedPoint("0.5") // FixedPoint("0.2") == FixedPoint("2.0")

    def test_power(self):
        r"""Test `**` sugar"""
        # power zero
        assert int(FixedPoint(5.0) ** FixedPoint(0)) == 1
        assert int(FixedPoint(5) ** FixedPoint(0)) == 1
        assert float(FixedPoint(5.0) ** FixedPoint(0)) == 1.0
        assert float(FixedPoint(5) ** FixedPoint(0)) == 1.0
        assert FixedPoint(5) ** False == FixedPoint(1.0)
        # power one
        self.assertAlmostEqual(int(FixedPoint(5.0) ** FixedPoint(1.0)), int(FixedPoint(5.0)), delta=5)
        self.assertAlmostEqual(
            int(FixedPoint(scaled_value=5 * 10**18) ** FixedPoint(scaled_value=1 * 10**18)),
            int(FixedPoint(scaled_value=5 * 10**18)),
            delta=5,
        )
        self.assertAlmostEqual(int(FixedPoint(5.0) ** True), int(FixedPoint(5.0)), delta=5)
        # power two
        self.assertAlmostEqual(int(FixedPoint(5.0) ** FixedPoint(2.0)), int(FixedPoint(25.0)), delta=30)
        self.assertAlmostEqual(
            int(FixedPoint(scaled_value=5 * 10**18) ** FixedPoint(scaled_value=2 * 10**18)),
            int(FixedPoint(25.0)),
            delta=30,
        )

    def test_power_nonfinite(self):
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
        assert self.NEG_INF ** (self.ODD_FINITE) == self.NEG_INF
        assert self.NEG_INF ** (self.EVEN_FINITE) == self.INF
        assert self.NEG_INF ** (self.NEG_ONE * self.ODD_FINITE) == self.ZERO
        assert self.NEG_INF ** (self.NEG_ONE * self.EVEN_FINITE) == self.ZERO
        # small base, -inf exp
        assert self.SMALL_FINITE**self.NEG_INF == self.INF
        assert self.SMALL_FINITE**self.INF == self.ZERO

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
        assert float(FixedPoint(5e-18) % FixedPoint(2e-18)) == 1e-18
        assert float(FixedPoint(9e-18) % FixedPoint(3.5e-18)) == 0.0
        # float % float
        assert float(FixedPoint(5.0) % FixedPoint(2.0)) == 1.0
        assert float(FixedPoint(9.0) % FixedPoint(3.5)) == 2.0
        # float % int
        assert float(FixedPoint(5.0) % FixedPoint(2)) == 1.0
        assert float(FixedPoint(9.0) % FixedPoint(3)) == 0.0
        # float % 1
        assert float(FixedPoint(3.2) % FixedPoint(1)) == 0.2
        assert float(FixedPoint(0.4) % FixedPoint(1)) == 0.4
        assert float(FixedPoint(-1.2) % FixedPoint(1)) == 0.8
        assert float(FixedPoint(1) % FixedPoint(1)) == 0
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
        # str % bool
        assert FixedPoint("5.0") % True == FixedPoint(0)
        # mixed type
        assert self.ONE % 1 == self.ZERO
        assert 1 % self.ONE == self.ZERO
        assert self.ONE % True == self.ZERO
        assert True % self.ONE == self.ZERO
        assert False % self.ONE == self.ZERO

    def test_modulo_fail(self):
        r"""Test failure of `%` sugar

        We are ignoring type errors -- we know they're bad, but we're looking for failure
        """
        with self.assertRaises(errors.DivisionByZero):
            _ = self.ONE % self.ZERO
        with self.assertRaises(errors.DivisionByZero):
            _ = self.ONE % False
        with self.assertRaises(TypeError):
            _ = self.ONE % 1.0  # type: ignore
        with self.assertRaises(TypeError):
            _ = 1.0 % self.ONE  # type: ignore
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

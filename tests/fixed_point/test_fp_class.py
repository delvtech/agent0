"""Tests for the FixedPoint class methods"""
import math
import unittest

import elfpy.errors.errors as errors
from elfpy.math import FixedPoint


class TestFixedPoint(unittest.TestCase):
    r"""Unit tests to verify that the FixedPoint class methods are correct."""

    INF = FixedPoint("inf")
    NEG_INF = FixedPoint("-inf")
    NAN = FixedPoint("nan")

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
        assert FixedPoint(5) == FixedPoint(5.0)
        # float == int
        assert FixedPoint(5.0) == FixedPoint(5)
        assert int(FixedPoint(5)) == 5  # int input directly maps, cast does not rescale
        assert float(FixedPoint(5.0)) == 5.0  # scales up on init, then back down on cast to float
        assert int(FixedPoint(5)) == float(FixedPoint(5.0))
        # bool
        assert FixedPoint(True) == FixedPoint(1.0)
        assert FixedPoint(False) == FixedPoint(0.0)
        # internal representation
        assert FixedPoint("5_340_070.0").scaled_value == 5340070000000000000000000
        assert FixedPoint(scaled_value=5) == FixedPoint(5e-18)
        assert FixedPoint(scaled_value=50) == FixedPoint(5e-17)

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

    # FIXME: def test_immutable_attribs(self):

    def test_int_cast(self):
        r"""Test int casting"""
        assert int(FixedPoint(1)) == 1  # int intput directly maps
        assert int(FixedPoint("2.0")) == 2  # float input directly maps
        assert int(FixedPoint("2.9")) == 2
        assert int(FixedPoint("0.9")) == 0
        assert int(FixedPoint(scaled_value=1)) == 0  # scaled value gets unmapped by decimal_places
        assert int(FixedPoint(scaled_value=1000000000000000000)) == 1

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
        assert float(FixedPoint(3.8 * 10**18)) == 3.8e18  # float in gets scaled
        assert float(FixedPoint(4.0)) == 4.0  # cast FP(float) back to float should be equivalent
        assert float(FixedPoint(1.5)) == 1.5
        assert float(FixedPoint(scaled_value=5)) == 0.000000000000000005
        assert float(FixedPoint(scaled_value=50)) == 0.00000000000000005
        assert float(FixedPoint(scaled_value=500)) == 0.0000000000000005
        assert float(FixedPoint(scaled_value=1)) == 1e-18  # cast FP(small int) back to float should be tiny
        assert float(FixedPoint(scaled_value=1 * 10**36)) == 1e18  # even if float is large, casting back stays large
        assert float(FixedPoint(scaled_value=3 * 10**18)) == 3.0

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
        assert str(FixedPoint(scaled_value=5)) == "0.000000000000000005"
        assert str(FixedPoint(scaled_value=50)) == "0.00000000000000005"
        assert str(FixedPoint(scaled_value=500)) == "0.0000000000000005"
        assert str(FixedPoint(scaled_value=-223423423)) == "-0.000000000223423423"
        assert str(FixedPoint(scaled_value=-223423423000000000000000000)) == "-223423423.0"
        assert str(FixedPoint(scaled_value=3 * 10**18)) == "3.0"
        assert str(FixedPoint(-0)) == "0.0"
        assert str(FixedPoint(5.0)) == "5.0"
        assert str(FixedPoint(1.5)) == "1.5"

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
        assert math.floor(FixedPoint(-6.3)) == FixedPoint(-7.0)
        assert math.floor(FixedPoint(-6.9)) == FixedPoint(-7.0)
        assert math.floor(FixedPoint(scaled_value=3)) == FixedPoint(0)
        assert math.floor(FixedPoint(scaled_value=-6)) == FixedPoint(-1)

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
        assert math.ceil(FixedPoint(-6.0)) == FixedPoint(-6.0)
        assert math.ceil(FixedPoint(6.0)) == FixedPoint(6.0)
        assert math.ceil(FixedPoint(-6.8)) == FixedPoint(-6.0)
        assert math.ceil(FixedPoint(6.8)) == FixedPoint(7.0)
        assert math.ceil(FixedPoint(scaled_value=3)) == FixedPoint(1.0)
        assert math.ceil(FixedPoint(scaled_value=-6)) == FixedPoint(0)

    def test_trunc(self):
        r"""Test trunc method"""
        assert math.trunc(FixedPoint("3.6")) == FixedPoint("3.0")
        assert math.trunc(FixedPoint("0.5")) == FixedPoint("0.0")
        assert math.trunc(FixedPoint("0.0000000003")) == FixedPoint("0.0")
        assert math.trunc(FixedPoint("-0.0")) == FixedPoint(0)
        assert math.trunc(FixedPoint("0.0")) == FixedPoint(0)
        assert math.trunc(FixedPoint(-6.0)) == FixedPoint(-6.0)
        assert math.trunc(FixedPoint(6.0)) == FixedPoint(6.0)
        assert math.trunc(FixedPoint(-6.8)) == FixedPoint(-6.0)
        assert math.trunc(FixedPoint(6.8)) == FixedPoint(6.0)
        assert math.trunc(FixedPoint(scaled_value=3)) == FixedPoint(0.0)
        assert math.trunc(FixedPoint(scaled_value=-6)) == FixedPoint(0)

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
        assert hash(FixedPoint(-2)) == hash((-2 * 10**18, "FixedPoint"))
        assert hash(FixedPoint(2)) == hash((2 * 10**18, "FixedPoint"))
        assert hash(FixedPoint("-1.0")) == hash((-1.0e18, "FixedPoint"))
        assert hash(FixedPoint("1.0")) == hash((1e18, "FixedPoint"))
        assert hash(FixedPoint("-2.5")) == hash((-2.5 * 10**18, "FixedPoint"))
        assert hash(FixedPoint("2.5")) == hash((2.5 * 10**18, "FixedPoint"))
        assert hash(FixedPoint("-200.537280")) == hash((-200.537280 * 10**18, "FixedPoint"))
        # last test, use FixedPoint as the key in a dictionary
        _ = {FixedPoint(1): "test_value"}  # if this works then the test passes
        assert {FixedPoint("-2"): "value"} == {FixedPoint(-2): "value"}
        assert {FixedPoint("-2"): "value"} != {FixedPoint(-2): "other_value"}
        assert {FixedPoint("2"): "value"} != {2: "value"}
        my_dict = {FixedPoint(1): "value"}
        my_dict[FixedPoint("1.0")] = "other_value"
        assert my_dict == {FixedPoint("1.0"): "other_value"}

    def test_hash_nonfinite(self):
        """Test the hash method with nonfinite values"""
        assert hash(self.INF) == hash((float("inf"), "FixedPoint"))
        assert hash(self.NEG_INF) == hash((float("-inf"), "FixedPoint"))
        assert hash(self.NAN) == hash((float("nan"), "FixedPoint"))

    def test_repr(self):
        """Test the repr method"""
        # pylint: disable=unnecessary-dunder-call
        assert self.INF.__repr__() == 'FixedPoint("inf")'
        assert self.NEG_INF.__repr__() == 'FixedPoint("-inf")'
        assert self.NAN.__repr__() == 'FixedPoint("nan")'
        assert FixedPoint(1).__repr__() == 'FixedPoint("1.0")'
        assert FixedPoint("-1.0").__repr__() == 'FixedPoint("-1.0")'
        assert FixedPoint(-1.0).__repr__() == 'FixedPoint("-1.0")'
        assert FixedPoint(-1).__repr__() == 'FixedPoint("-1.0")'

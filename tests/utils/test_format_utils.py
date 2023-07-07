"""Unit tests for formatting utilities."""
import logging

import numpy as np

from elfpy.utils.format import format_numeric_string


class TestFormatFloatAsString:
    """Unit tests for format_numeric_string."""

    def test_positive_values(self):
        """Test positive values"""
        assert format_numeric_string(123.456, precision=7) == "123.4560"
        assert format_numeric_string(123.456, precision=6) == "123.456"
        assert format_numeric_string(123.456, precision=5) == "123.46"
        assert format_numeric_string(123.456, precision=3) == "123"
        assert format_numeric_string(0.12345, precision=3) == "0.123"
        assert format_numeric_string(1000000, precision=7) == "1,000,000"

    def test_negative_values(self):
        """Test negative values"""
        assert format_numeric_string(-123.456, precision=6) == "-123.456"
        assert format_numeric_string(-0.12345, precision=3) == "-0.123"
        assert format_numeric_string(-1000000, precision=7) == "-1,000,000"

    def test_values_less_than_one(self):
        """Test values less than 1"""
        assert format_numeric_string(0.0000123, precision=7) == "0.0000123"
        assert format_numeric_string(0.000001, precision=7) == "0.0000010"
        assert format_numeric_string(0.0000001, precision=7) == "0.0000001"

    def test_large_values(self):
        """Test large values"""
        assert format_numeric_string(1e12, precision=13) == "1,000,000,000,000"
        assert format_numeric_string(1e9, precision=10) == "1,000,000,000"
        assert format_numeric_string(1e6, precision=7) == "1,000,000"

    def test_zero_value(self):
        """Test zero value"""
        assert format_numeric_string(0) == "0"

    def test_inf_value(self):
        """Test infinity"""
        assert format_numeric_string(np.inf) == "inf"

    def test_nan_value(self):
        """Test NaN"""
        assert format_numeric_string(np.nan) == "nan"

    def test_debug_mode(self, caplog):
        """Test debug mode"""
        with caplog.at_level(logging.ERROR):
            format_numeric_string(123.456, debug=True)
            assert "value: 123.456, type: <class 'float'>, precision: 3, min_digits: 0" in caplog.text

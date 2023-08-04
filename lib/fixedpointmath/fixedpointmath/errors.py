"""Define Python user-defined exceptions"""
from __future__ import annotations


class DivisionByZero(Exception):
    """
    For FixedPoint type; thrown if trying to divide any FixedPoint number by zero.
    """

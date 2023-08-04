"""Utility functions for doing special math"""
# Modules imported here are simply for easier namespace resolution, e.g.,
# from fixedpointmath import FixedPoint
# instead of
# from fixedpointmath.fixed_point import FixedPoint
# So these are more interfaces to this library, and hence, no need to check if these are accessed

# pyright: reportUnusedImport=false

from .fixed_point import FixedPoint
from .fixed_point_integer_math import FixedPointIntegerMath
from .fixed_point_math import FixedPointMath

"""Functions for storing Hyperdrive state."""
from __future__ import annotations

from dataclasses import dataclass

from fixedpointmath import FixedPoint

# TODO: These dataclasses are similar to pypechain except for
#  - snake_case attributes instead of camelCase
#  - FixedPoint types instead of int
#  - nested dataclasses (PoolConfig) include a __post_init__ that allows for
#  instantiation with a nested dictionary
#
# We'd like to rely on the pypechain classes as much as possible.
# One solution could be to build our own interface wrapper that pulls in the pypechain
# dataclass and makes this fixed set of changes?
# pylint: disable=too-many-instance-attributes


@dataclass
class Fees:
    """Fees struct."""

    curve: FixedPoint
    flat: FixedPoint
    governance: FixedPoint

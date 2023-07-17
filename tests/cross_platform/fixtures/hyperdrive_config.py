"""Hyperdrive market config fixture"""
from dataclasses import dataclass

import pytest
from fixedpointmath import FixedPoint


@dataclass
class HyperdriveConfig:
    """Configuration variables to setup hyperdrive fixtures."""

    # pylint: disable=too-many-instance-attributes

    initial_apr: FixedPoint = FixedPoint("0.05")
    share_price: FixedPoint = FixedPoint(1)
    checkpoint_duration_seconds: int = 86400
    checkpoints: int = 182
    time_stretch: int = 22186877016851913475
    curve_fee: FixedPoint = FixedPoint(0)
    flat_fee: FixedPoint = FixedPoint(0)
    gov_fee: FixedPoint = FixedPoint(0)
    position_duration_seconds: int = checkpoint_duration_seconds * checkpoints
    target_liquidity = FixedPoint(1 * 10**6)
    minimum_share_reserves: FixedPoint = FixedPoint(1)


@pytest.fixture(scope="function")
def hyperdrive_config() -> HyperdriveConfig:
    """Returns a hyperdrive configuration dataclass with default values.  This fixture should be
    overridden as needed in test classes."""
    return HyperdriveConfig()

"""Fixture for the python implementation of the Hyperdrive market."""
import pytest

from elfpy.markets.hyperdrive import HyperdriveMarket, HyperdriveMarketState, HyperdrivePricingModel
from elfpy.math import FixedPoint
from elfpy.time.time import BlockTime, StretchedTime

from .hyperdrive_config import HyperdriveConfig


@pytest.fixture(scope="function")
def hyperdrive_sim(hyperdrive_config: HyperdriveConfig) -> HyperdriveMarket:
    """Returns an elfpy hyperdrive Market."""
    position_duration_days = FixedPoint(float(hyperdrive_config.position_duration_seconds)) / FixedPoint(
        float(24 * 60 * 60)
    )
    pricing_model = HyperdrivePricingModel()
    position_duration = StretchedTime(
        days=position_duration_days,
        time_stretch=pricing_model.calc_time_stretch(FixedPoint(hyperdrive_config.initial_apr)),
        normalizing_constant=position_duration_days,
    )
    market = HyperdriveMarket(
        pricing_model=HyperdrivePricingModel(),
        market_state=HyperdriveMarketState(),
        position_duration=position_duration,
        block_time=BlockTime(),
    )
    return market

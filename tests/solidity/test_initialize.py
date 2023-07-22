"""Market initialization tests that match those being executed in the solidity repo"""
import unittest

from fixedpointmath import FixedPoint

import elfpy.time as time
from elfpy.agents.agent import Agent
from elfpy.agents.policies import NoActionPolicy
from elfpy.markets.hyperdrive import HyperdriveMarket, HyperdriveMarketState, HyperdrivePricingModel
from elfpy.time.time import BlockTime

# pylint: disable=too-many-instance-attributes


class TestInitialize(unittest.TestCase):
    """Test case for initializing the market"""

    # TODO: Switching to fixed point or 64 bit float should allow us to increase this to WEI
    # issue #112
    APPROX_EQ: FixedPoint = FixedPoint(1e-5)

    contribution: FixedPoint
    target_apr: FixedPoint
    position_duration: FixedPoint
    alice: Agent
    bob: Agent
    celine: Agent
    hyperdrive: HyperdriveMarket
    block_time: BlockTime
    pricing_model: HyperdrivePricingModel

    def __init__(
        self,
        contribution: FixedPoint = FixedPoint("1_000.0"),
        target_apr: FixedPoint = FixedPoint("0.5"),
        position_duration: int = 180,
        **kwargs,
    ):
        """Set up agent, pricing model, & market for the subsequent tests."""
        self.contribution = contribution
        self.target_apr = target_apr
        self.position_duration = FixedPoint(position_duration)
        self.alice = Agent(wallet_address=0, policy=NoActionPolicy(budget=self.contribution))
        self.bob = Agent(wallet_address=1, policy=NoActionPolicy(budget=self.contribution))
        self.celine = Agent(wallet_address=2, policy=NoActionPolicy(budget=self.contribution))
        self.block_time = BlockTime()
        self.pricing_model = HyperdrivePricingModel()
        market_state = HyperdriveMarketState()
        self.hyperdrive = HyperdriveMarket(
            pricing_model=self.pricing_model,
            market_state=market_state,
            block_time=self.block_time,
            position_duration=time.StretchedTime(
                days=self.position_duration,
                time_stretch=self.pricing_model.calc_time_stretch(self.target_apr),
                normalizing_constant=self.position_duration,
            ),
        )
        _, wallet_deltas = self.hyperdrive.initialize(self.contribution, self.target_apr)
        self.alice.wallet.update(wallet_deltas)
        super().__init__(**kwargs)


def test_initialize_failure():
    """Markets should not be able to be initialized twice.
    Since setUp initializes it, we can check the assert by trying again here."""
    test = TestInitialize()
    with test.assertRaises(AssertionError):
        _ = test.hyperdrive.initialize(
            contribution=test.contribution,
            target_apr=test.target_apr,
        )


def test_initialize_success():
    """Verify that the initialized market has the correct APR & reserve levels"""
    test = TestInitialize()
    init_apr = test.pricing_model.calc_apr_from_reserves(
        market_state=test.hyperdrive.market_state,
        time_remaining=test.hyperdrive.position_duration,
    )
    test.assertAlmostEqual(init_apr, test.target_apr, delta=test.APPROX_EQ)
    test.assertEqual(test.alice.wallet.balance.amount, FixedPoint(0))
    test.assertEqual(
        test.hyperdrive.market_state.share_reserves, test.contribution * test.hyperdrive.market_state.share_price
    )
    test.assertEqual(
        test.hyperdrive.market_state.lp_total_supply, test.contribution + test.hyperdrive.market_state.bond_reserves
    )


def test_initialize_bots_on_solidity_success():
    """Numerical test to ensure exact same outcome as Solidity, using params from bots_on_solidity.ipynb"""
    test = TestInitialize(
        contribution=FixedPoint("500_000_000.0"), target_apr=FixedPoint("0.05"), position_duration=365
    )
    init_apr = test.pricing_model.calc_apr_from_reserves(
        market_state=test.hyperdrive.market_state,
        time_remaining=test.hyperdrive.position_duration,
    )
    test.assertAlmostEqual(init_apr, test.target_apr, delta=test.APPROX_EQ)
    test.assertEqual(test.alice.wallet.balance.amount, FixedPoint(0))
    test.assertAlmostEqual(
        test.hyperdrive.market_state.share_reserves, FixedPoint("500_000_000.0"), delta=test.APPROX_EQ
    )
    test.assertEqual(test.hyperdrive.market_state.share_price, FixedPoint("1.0"))
    virtual_liquidity = (
        test.hyperdrive.market_state.share_reserves * test.hyperdrive.market_state.share_price
        + FixedPoint("2.0") * test.hyperdrive.market_state.bond_reserves
    )
    test.assertAlmostEqual(virtual_liquidity, FixedPoint("1_476_027_255.06539"), delta=test.APPROX_EQ)
    test.assertAlmostEqual(
        test.hyperdrive.market_state.lp_total_supply, FixedPoint("988_013_627.532698"), delta=test.APPROX_EQ
    )

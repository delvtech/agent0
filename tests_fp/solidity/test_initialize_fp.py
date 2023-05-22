"""Market initialization tests that match those being executed in the solidity repo"""
import unittest

import elfpy.agents.agent as elf_agent
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time
from elfpy.time.time import BlockTimeFP
from elfpy.math import FixedPoint

# pylint: disable=too-many-instance-attributes


class TestInitialize(unittest.TestCase):
    """Test case for initializing the market"""

    # TODO: Switching to fixed point or 64 bit float should allow us to increase this to WEI
    # issue #112
    APPROX_EQ: FixedPoint = FixedPoint(1e-5)

    contribution: FixedPoint
    target_apr: FixedPoint
    position_duration: FixedPoint
    alice: elf_agent.AgentFP
    bob: elf_agent.AgentFP
    celine: elf_agent.AgentFP
    hyperdrive: hyperdrive_market.MarketFP
    block_time: BlockTimeFP
    pricing_model: hyperdrive_pm.HyperdrivePricingModelFP

    def __init__(self, contribution: float = 1_000.0, target_apr: float = 0.5, position_duration: int = 180, **kwargs):
        """
        Set up agent, pricing model, & market for the subsequent tests.
        """
        self.contribution = FixedPoint(float(contribution))
        self.target_apr = FixedPoint(float(target_apr))
        self.position_duration = FixedPoint(position_duration * 10**18)
        self.alice = elf_agent.AgentFP(wallet_address=0, budget=self.contribution)
        self.bob = elf_agent.AgentFP(wallet_address=1, budget=self.contribution)
        self.celine = elf_agent.AgentFP(wallet_address=2, budget=self.contribution)
        self.block_time = BlockTimeFP()
        self.pricing_model = hyperdrive_pm.HyperdrivePricingModelFP()
        market_state = hyperdrive_market.MarketStateFP()
        self.hyperdrive = hyperdrive_market.MarketFP(
            pricing_model=self.pricing_model,
            market_state=market_state,
            block_time=self.block_time,
            position_duration=time.StretchedTimeFP(
                days=self.position_duration,
                time_stretch=self.pricing_model.calc_time_stretch(self.target_apr),
                normalizing_constant=self.position_duration,
            ),
        )
        _, wallet_deltas = self.hyperdrive.initialize(
            wallet_address=self.alice.wallet.address,
            contribution=self.contribution,
            target_apr=self.target_apr,
        )
        self.alice.wallet.update(wallet_deltas)
        super().__init__(**kwargs)


def test_initialize_failure():
    """Markets should not be able to be initialized twice.
    Since setUp initializes it, we can check the assert by trying again here."""
    test = TestInitialize()
    with test.assertRaises(AssertionError):
        _ = test.hyperdrive.initialize(
            wallet_address=test.bob.wallet.address,
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
    test = TestInitialize(contribution=500_000_000, target_apr=0.05, position_duration=365)
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

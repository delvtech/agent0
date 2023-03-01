"""Market initialization tests that match those being executed in the solidity repo"""
import unittest

import elfpy.agents.agent as agent
import elfpy.markets.hyperdrive as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time


class TestInitialize(unittest.TestCase):
    """Test case for initializing the market

    .. todo: this is a mirror of the tests in test_markets.py; need to unify
    """

    # TODO: Switching to fixed point or 64 bit float should allow us to increase this to WEI
    # issue #112
    APPROX_EQ: float = 1e-15
    contribution: float = 1_000
    target_apr: float = 0.5
    position_duration: int = 180
    alice: agent.Agent
    bob: agent.Agent
    celine: agent.Agent
    hyperdrive: hyperdrive_market.Market
    pricing_model: hyperdrive_pm.HyperdrivePricingModel

    def setUp(self):
        """Set up agent, pricing model, & market for the subsequent tests.
        This function is run before each test method.
        """
        self.alice = agent.Agent(wallet_address=0, budget=self.contribution)
        self.bob = agent.Agent(wallet_address=1, budget=self.contribution)
        self.celine = agent.Agent(wallet_address=2, budget=self.contribution)
        self.pricing_model = hyperdrive_pm.HyperdrivePricingModel()
        market_state = hyperdrive_market.MarketState()
        self.hyperdrive = hyperdrive_market.Market(
            pricing_model=self.pricing_model,
            market_state=market_state,
            position_duration=time.StretchedTime(
                days=self.position_duration,
                time_stretch=self.pricing_model.calc_time_stretch(self.target_apr),
                normalizing_constant=self.position_duration,
            ),
        )
        wallet_deltas, _ = self.hyperdrive.initialize_market(
            wallet_address=self.alice.wallet.address,
            contribution=self.contribution,
            target_apr=self.target_apr,
        )
        self.alice.update_wallet(wallet_deltas)

    def test_initialize_failure(self):
        """Markets should not be able to be initialized twice.
        Since setUp initializes it, we can check the assert by trying again here."""
        with self.assertRaises(AssertionError):
            _ = self.hyperdrive.initialize_market(
                wallet_address=self.bob.wallet.address,
                contribution=self.contribution,
                target_apr=self.target_apr,
            )

    def test_initialize_success(self):
        """Verify that the initialized market has the correct APR & reserve levels"""
        init_apr = self.pricing_model.calc_apr_from_reserves(
            market_state=self.hyperdrive.market_state,
            time_remaining=self.hyperdrive.position_duration,
        )
        self.assertAlmostEqual(init_apr, self.target_apr, delta=self.APPROX_EQ)
        self.assertEqual(self.alice.wallet.balance.amount, 0.0)
        self.assertEqual(
            self.hyperdrive.market_state.share_reserves, self.contribution * self.hyperdrive.market_state.share_price
        )
        self.assertEqual(
            self.hyperdrive.market_state.lp_total_supply, self.contribution + self.hyperdrive.market_state.bond_reserves
        )

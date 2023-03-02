"""Testing the Borrow Market"""

import unittest

import elfpy.agents.agent as agent
import elfpy.markets.hyperdrive as hyperdrive_markets
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel

from elfpy.time import StretchedTime
from elfpy.time.time import BlockTime


class TestAddLiquidity(unittest.TestCase):
    """Test adding liquidity to hyperdrive"""

    contribution = 500_000_000
    target_apr = 0.05
    alice: agent.Agent
    bob: agent.Agent
    celine: agent.Agent
    hyperdrive: hyperdrive_markets.Market
    block_time: BlockTime

    def setUp(self):

        self.alice = agent.Agent(wallet_address=0, budget=self.contribution)
        self.bob = agent.Agent(wallet_address=1, budget=self.contribution)
        self.celine = agent.Agent(wallet_address=1, budget=self.contribution)
        self.block_time = BlockTime()

        pricing_model = HyperdrivePricingModel()
        market_state = hyperdrive_markets.MarketState()

        self.hyperdrive = hyperdrive_markets.Market(
            pricing_model=pricing_model,
            market_state=market_state,
            block_time=self.block_time,
            position_duration=StretchedTime(
                days=365, time_stretch=pricing_model.calc_time_stretch(self.target_apr), normalizing_constant=365
            ),
        )
        _, wallet_deltas = self.hyperdrive.initialize(self.alice.wallet.address, self.contribution, 0.05)
        self.alice.update_wallet(wallet_deltas)

    def test_add_liquidity_failure_zero_amount(self):
        """Test adding zero liquidity fails"""
        with self.assertRaises(AssertionError):
            self.hyperdrive.add_liquidity(self.bob.wallet.address, 0)

    def test_add_liquidity_identical_lp_shares(self):
        """Test adding liquidity equal to the total liquidity of the pool creates the same number of
        shares that are in the pool."""
        lp_supply_before = self.hyperdrive.market_state.lp_total_supply

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(self.bob.wallet.address, self.contribution)
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.bob.update_wallet(wallet_deltas)

        # Ensure that the contribution was transferred to Hyperdrive.
        self.assertEqual(market_deltas.d_base_asset, -wallet_deltas.balance.amount)

        # Ensure that the new LP receives the same amount of LP shares as the initializer.
        self.assertAlmostEqual(market_deltas.d_lp_total_supply, lp_supply_before, 6)
        self.assertEqual(self.hyperdrive.market_state.lp_total_supply, lp_supply_before * 2)

        # Ensure the pool APR is still approximately equal to the target APR.
        pool_apr = self.hyperdrive.pricing_model.calc_apr_from_reserves(
            self.hyperdrive.market_state, self.hyperdrive.position_duration
        )
        self.assertAlmostEqual(pool_apr, self.target_apr, 5)

    def test_add_liquidity_with_long_immediately(self):
        """Test adding liquidity when there is a long open.  LP should still get the same number of
        shares as if there weren't any longs open."""
        lp_supply_before = self.hyperdrive.market_state.lp_total_supply

        # Celine opens a long.
        market_deltas, wallet_deltas = self.hyperdrive.open_long(self.celine.wallet.address, 50_000_000)
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.celine.update_wallet(wallet_deltas)

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(self.bob.wallet.address, self.contribution)
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.bob.update_wallet(wallet_deltas)

        # Ensure that the contribution was transferred to Hyperdrive.
        self.assertEqual(market_deltas.d_base_asset, -wallet_deltas.balance.amount)

        # Ensure that the new LP receives the same amount of LP shares as the initializer.
        self.assertAlmostEqual(market_deltas.d_lp_total_supply, lp_supply_before, 6)
        self.assertEqual(self.hyperdrive.market_state.lp_total_supply, lp_supply_before * 2)

        # Ensure the pool APR is still approximately equal to the target APR.
        pool_apr = self.hyperdrive.pricing_model.calc_apr_from_reserves(
            self.hyperdrive.market_state, self.hyperdrive.position_duration
        )
        self.assertAlmostEqual(pool_apr, self.target_apr, 1)

    def test_add_liquidity_with_short_immediately(self):
        """Test adding liquidity when there is a long short.  LP should still get the same number of
        shares as if there weren't any shorts open."""
        self.assertEqual(True, True)
        lp_supply_before = self.hyperdrive.market_state.lp_total_supply

        # Celine opens a short.
        market_deltas, wallet_deltas = self.hyperdrive.open_short(self.celine.wallet.address, 50_000_000)
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.celine.update_wallet(wallet_deltas)

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(self.bob.wallet.address, self.contribution)
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.bob.update_wallet(wallet_deltas)

        # Ensure that the contribution was transferred to Hyperdrive.
        self.assertEqual(market_deltas.d_base_asset, -wallet_deltas.balance.amount)

        # Ensure that the new LP receives the same amount of LP shares as the initializer.
        self.assertAlmostEqual(market_deltas.d_lp_total_supply, lp_supply_before, 6)
        self.assertEqual(self.hyperdrive.market_state.lp_total_supply, lp_supply_before * 2)

        # Ensure the pool APR is still approximately equal to the target APR.
        pool_apr = self.hyperdrive.pricing_model.calc_apr_from_reserves(
            self.hyperdrive.market_state, self.hyperdrive.position_duration
        )
        self.assertAlmostEqual(pool_apr, self.target_apr, 1)

    def test_add_liquidity_with_long_at_maturity(self):
        """Test adding liquidity with a long at maturity."""
        # Celine opens a long.
        market_deltas, wallet_deltas = self.hyperdrive.open_long(self.celine.wallet.address, 50_000_000)
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.celine.update_wallet(wallet_deltas)

        self.block_time.tick(1)

        # Mock having Celine's long auto closed from checkpointing.
        market_deltas_close_long, _ = self.hyperdrive.close_long(self.celine.wallet.address, 50_000_000, 0)
        self.hyperdrive.market_state.apply_delta(market_deltas_close_long)

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(self.bob.wallet.address, self.contribution)
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.bob.update_wallet(wallet_deltas)

        # Ensure that the contribution was transferred to Hyperdrive.
        self.assertEqual(market_deltas.d_base_asset, -wallet_deltas.balance.amount)

        # Ensure the pool APR is still approximately equal to the target APR.
        pool_apr = self.hyperdrive.pricing_model.calc_apr_from_reserves(
            self.hyperdrive.market_state, self.hyperdrive.position_duration
        )
        self.assertAlmostEqual(pool_apr, self.target_apr, 1)

        # Ensure that if the new LP withdraws, they get their money back.
        market_deltas, wallet_deltas = self.hyperdrive.remove_liquidity(
            self.bob.wallet.address, self.bob.wallet.lp_tokens
        )
        self.assertAlmostEqual(wallet_deltas.balance.amount, self.contribution, 6)

    def test_add_liquidity_with_short_at_maturity(self):
        """Test adding liquidity with a short at maturity."""
        # Celine opens a short.
        market_deltas, wallet_deltas = self.hyperdrive.open_short(self.celine.wallet.address, 50_000_000)
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.celine.update_wallet(wallet_deltas)

        self.block_time.tick(1)

        # Mock having Celine's long auto closed from checkpointing.
        market_deltas_close_short, _ = self.hyperdrive.close_short(self.celine.wallet.address, 1, 50_000_000, 0)
        self.hyperdrive.market_state.apply_delta(market_deltas_close_short)

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(self.bob.wallet.address, self.contribution)
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.bob.update_wallet(wallet_deltas)

        # Ensure that the contribution was transferred to Hyperdrive.
        self.assertEqual(market_deltas.d_base_asset, -wallet_deltas.balance.amount)

        # Ensure the pool APR is still approximately equal to the target APR.
        pool_apr = self.hyperdrive.pricing_model.calc_apr_from_reserves(
            self.hyperdrive.market_state, self.hyperdrive.position_duration
        )
        self.assertAlmostEqual(pool_apr, self.target_apr, 1)

        # Ensure that if the new LP withdraws, they get their money back.
        market_deltas, wallet_deltas = self.hyperdrive.remove_liquidity(
            self.bob.wallet.address, self.bob.wallet.lp_tokens
        )
        self.assertAlmostEqual(wallet_deltas.balance.amount, self.contribution)

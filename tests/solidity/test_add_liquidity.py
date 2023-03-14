"""Testing the Borrow Market"""

import unittest

import elfpy.agents.agent as agent
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_markets
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time


class TestAddLiquidity(unittest.TestCase):
    """Test adding liquidity to hyperdrive"""

    contribution = 500_000_000
    target_apr = 0.05
    alice: agent.Agent
    bob: agent.Agent
    celine: agent.Agent
    hyperdrive: hyperdrive_markets.Market
    block_time: time.BlockTime

    def setUp(self):
        self.alice = agent.Agent(wallet_address=0, budget=self.contribution)
        self.bob = agent.Agent(wallet_address=1, budget=self.contribution)
        self.celine = agent.Agent(wallet_address=1, budget=self.contribution)
        self.block_time = time.BlockTime()

        pricing_model = hyperdrive_pm.HyperdrivePricingModel()
        market_state = hyperdrive_markets.MarketState()

        self.hyperdrive = hyperdrive_markets.Market(
            pricing_model=pricing_model,
            market_state=market_state,
            block_time=self.block_time,
            position_duration=time.StretchedTime(
                days=365, time_stretch=pricing_model.calc_time_stretch(self.target_apr), normalizing_constant=365
            ),
        )
        _, wallet_deltas = self.hyperdrive.initialize(self.alice.wallet.address, self.contribution, 0.05)
        self.alice.wallet.update(wallet_deltas)

    def test_add_liquidity_failure_zero_amount(self):
        """Test adding zero liquidity fails"""
        with self.assertRaises(AssertionError):
            self.hyperdrive.add_liquidity(self.bob.wallet, 0)

    def test_add_liquidity_identical_lp_shares(self):
        """Test adding liquidity equal to the total liquidity of the pool creates the same number of
        shares that are in the pool."""
        lp_supply_before = self.hyperdrive.market_state.lp_total_supply

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(self.bob.wallet, self.contribution)

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
        market_deltas, wallet_deltas = hyperdrive_actions.calc_open_long(
            wallet_address=self.celine.wallet.address,
            base_amount=50_000_000,
            market=self.hyperdrive,
        )
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.celine.wallet.update(wallet_deltas)

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(self.bob.wallet, self.contribution)

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
        market_deltas, wallet_deltas = hyperdrive_actions.calc_open_short(
            wallet_address=self.celine.wallet.address,
            bond_amount=50_000_000,
            market=self.hyperdrive,
        )
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.celine.wallet.update(wallet_deltas)

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(self.bob.wallet, self.contribution)

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
        market_deltas, wallet_deltas = self.hyperdrive.open_long(
            agent_wallet=self.celine.wallet,
            base_amount=50_000_000,
        )

        self.block_time.tick(1)

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(self.bob.wallet, self.contribution)

        # Ensure that the contribution was transferred to Hyperdrive.
        self.assertEqual(market_deltas.d_base_asset, -wallet_deltas.balance.amount)

        # Ensure the pool APR is still approximately equal to the target APR.
        pool_apr = self.hyperdrive.pricing_model.calc_apr_from_reserves(
            self.hyperdrive.market_state, self.hyperdrive.position_duration
        )
        self.assertAlmostEqual(pool_apr, self.target_apr, 1)

        # Ensure that if the new LP withdraws, they get their money back.
        market_deltas, wallet_deltas = self.hyperdrive.remove_liquidity(
            agent_wallet=self.bob.wallet,
            bond_amount=self.bob.wallet.lp_tokens,
        )
        self.assertAlmostEqual(wallet_deltas.balance.amount, self.contribution, places=6)

    def test_add_liquidity_with_short_at_maturity(self):
        """Test adding liquidity with a short at maturity."""
        # Celine opens a short.
        market_deltas, wallet_deltas = self.hyperdrive.open_short(
            agent_wallet=self.celine.wallet,
            bond_amount=50_000_000,
        )

        self.block_time.tick(1)

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(
            agent_wallet=self.bob.wallet,
            trade_amount=self.contribution,
        )

        # Ensure that the contribution was transferred to Hyperdrive.
        self.assertEqual(market_deltas.d_base_asset, -wallet_deltas.balance.amount)

        # Ensure the pool APR is still approximately equal to the target APR.
        pool_apr = self.hyperdrive.pricing_model.calc_apr_from_reserves(
            self.hyperdrive.market_state, self.hyperdrive.position_duration
        )
        self.assertAlmostEqual(pool_apr, self.target_apr, 1)

        # Ensure that if the new LP withdraws, they get their money back.
        market_deltas, wallet_deltas = self.hyperdrive.remove_liquidity(
            agent_wallet=self.bob.wallet,
            bond_amount=self.bob.wallet.lp_tokens,
        )
        self.assertAlmostEqual(wallet_deltas.balance.amount, self.contribution)

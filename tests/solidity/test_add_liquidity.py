"""Testing the Borrow Market"""

import unittest

import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_markets
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.agents.agent as agent
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
        market_deltas, wallet_deltas = hyperdrive_actions.calc_open_long(
            wallet_address=self.celine.wallet.address,
            base_amount=50_000_000,
            market=self.hyperdrive,
        )
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.celine.wallet.update(wallet_deltas)

        self.block_time.tick(1)

        # Mock having Celine's long auto closed from checkpointing.
        market_deltas_close_long, _ = hyperdrive_actions.calc_close_long(
            wallet_address=self.celine.wallet.address,
            bond_amount=50_000_000,
            market=self.hyperdrive,
            mint_time=0,
        )
        self.hyperdrive.market_state.apply_delta(market_deltas_close_long)

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
        market_deltas, wallet_deltas = hyperdrive_actions.calc_remove_liquidity(
            wallet_address=self.bob.wallet.address,
            bond_amount=self.bob.wallet.lp_tokens,
            market=self.hyperdrive,
        )
        self.assertAlmostEqual(wallet_deltas.balance.amount, self.contribution, 6)

    def test_add_liquidity_with_short_at_maturity(self):
        """Test adding liquidity with a short at maturity."""
        # Celine opens a short.
        market_deltas, wallet_deltas = hyperdrive_actions.calc_open_short(
            wallet_address=self.celine.wallet.address,
            bond_amount=50_000_000,
            market=self.hyperdrive,
        )
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.celine.wallet.update(wallet_deltas)

        self.block_time.tick(1)

        # Mock having Celine's long auto closed from checkpointing.
        market_deltas_close_short, _ = hyperdrive_actions.calc_close_short(
            wallet_address=self.celine.wallet.address,
            bond_amount=50_000_000,
            market=self.hyperdrive,
            mint_time=0,
            open_share_price=1,
        )
        self.hyperdrive.market_state.apply_delta(market_deltas_close_short)

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = hyperdrive_actions.calc_add_liquidity(
            wallet_address=self.bob.wallet.address,
            bond_amount=self.contribution,
            market=self.hyperdrive,
        )
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.bob.wallet.update(wallet_deltas)

        # Ensure that the contribution was transferred to Hyperdrive.
        self.assertEqual(market_deltas.d_base_asset, -wallet_deltas.balance.amount)

        # Ensure the pool APR is still approximately equal to the target APR.
        pool_apr = self.hyperdrive.pricing_model.calc_apr_from_reserves(
            self.hyperdrive.market_state, self.hyperdrive.position_duration
        )
        self.assertAlmostEqual(pool_apr, self.target_apr, 1)

        # Ensure that if the new LP withdraws, they get their money back.
        market_deltas, wallet_deltas = hyperdrive_actions.calc_remove_liquidity(
            wallet_address=self.bob.wallet.address,
            bond_amount=self.bob.wallet.lp_tokens,
            market=self.hyperdrive,
        )
        self.assertAlmostEqual(wallet_deltas.balance.amount, self.contribution)
"""Testing the Borrow Market"""

import logging
import itertools
import unittest

import numpy as np

import elfpy.types as types
import elfpy.utils.outputs as output_utils
from elfpy.markets.borrow import Market as BorrowMarket
from elfpy.markets.borrow import MarketState as BorrowMarketState


class TestAddLiquidity(unittest.TestCase):
    """Test add liquidity to """

    def test_add_liquidity_failure_zero_amount(self):
        # uint256 apr = 0.05e18;

        # // Initialize the pool with a large amount of capital.
        # uint256 contribution = 500_000_000e18;
        # initialize(alice, apr, contribution);

        # // Attempt to purchase bonds with zero base. This should fail.
        # vm.stopPrank();
        # vm.startPrank(bob);
        # vm.expectRevert(Errors.ZeroAmount.selector);
        # hyperdrive.addLiquidity(0, 0, bob, true);

    def test_add_liquidity_identical_lp_shares(self):
        # uint256 apr = 0.05e18;

        # // Initialize the pool with a large amount of capital.
        # uint256 contribution = 500_000_000e18;
        # initialize(alice, apr, contribution);
        # uint256 lpSupplyBefore = hyperdrive.totalSupply(AssetId._LP_ASSET_ID);
        # uint256 baseBalance = baseToken.balanceOf(address(hyperdrive));

        # // Add liquidity with the same amount as the original contribution.
        # uint256 lpShares = addLiquidity(bob, contribution);

        # // Ensure that the contribution was transferred to Hyperdrive.
        # assertEq(baseToken.balanceOf(bob), 0);
        # assertEq(
        #     baseToken.balanceOf(address(hyperdrive)),
        #     baseBalance.add(contribution)
        # );

        # // Ensure that the new LP receives the same amount of LP shares as
        # // the initializer.
        # assertEq(lpShares, lpSupplyBefore);
        # assertEq(
        #     hyperdrive.totalSupply(AssetId._LP_ASSET_ID),
        #     lpSupplyBefore * 2
        # );

        # // Ensure the pool APR is still approximately equal to the target APR.
        # uint256 poolApr = HyperdriveMath.calculateAPRFromReserves(
        #     hyperdrive.shareReserves(),
        #     hyperdrive.bondReserves(),
        #     hyperdrive.totalSupply(AssetId._LP_ASSET_ID),
        #     hyperdrive.initialSharePrice(),
        #     hyperdrive.positionDuration(),
        #     hyperdrive.timeStretch()
        # );
        # assertApproxEqAbs(poolApr, apr, 1);

    def test_add_liquidity_with_long_immediately(self):
        # uint256 apr = 0.05e18;

        # // Initialize the pool with a large amount of capital.
        # uint256 contribution = 500_000_000e18;
        # initialize(alice, apr, contribution);
        # uint256 lpSupplyBefore = hyperdrive.totalSupply(AssetId._LP_ASSET_ID);

        # // Celine opens a long.
        # openLong(celine, 50_000_000e18);

        # // Add liquidity with the same amount as the original contribution.
        # uint256 aprBefore = calculateAPRFromReserves(hyperdrive);
        # uint256 baseBalance = baseToken.balanceOf(address(hyperdrive));
        # uint256 lpShares = addLiquidity(bob, contribution);

        # // Ensure that the contribution was transferred to Hyperdrive.
        # assertEq(baseToken.balanceOf(bob), 0);
        # assertEq(
        #     baseToken.balanceOf(address(hyperdrive)),
        #     baseBalance.add(contribution)
        # );

        # // Ensure that the new LP receives the same amount of LP shares as
        # // the initializer.
        # assertEq(lpShares, lpSupplyBefore);
        # assertEq(
        #     hyperdrive.totalSupply(AssetId._LP_ASSET_ID),
        #     lpSupplyBefore * 2
        # );

        # // Ensure the pool APR is still approximately equal to the target APR.
        # uint256 aprAfter = calculateAPRFromReserves(hyperdrive);
        # assertApproxEqAbs(aprAfter, aprBefore, 1);

    def test_add_liquidity_with_short_immediately():
        # uint256 apr = 0.05e18;

        # // Initialize the pool with a large amount of capital.
        # uint256 contribution = 500_000_000e18;
        # initialize(alice, apr, contribution);
        # uint256 lpSupplyBefore = hyperdrive.totalSupply(AssetId._LP_ASSET_ID);

        # // Celine opens a short.
        # openShort(celine, 50_000_000e18);

        # // Add liquidity with the same amount as the original contribution.
        # uint256 aprBefore = calculateAPRFromReserves(hyperdrive);
        # uint256 baseBalance = baseToken.balanceOf(address(hyperdrive));
        # uint256 lpShares = addLiquidity(bob, contribution);

        # // Ensure that the contribution was transferred to Hyperdrive.
        # assertEq(baseToken.balanceOf(bob), 0);
        # assertEq(
        #     baseToken.balanceOf(address(hyperdrive)),
        #     baseBalance.add(contribution)
        # );

        # // Ensure that the new LP receives the same amount of LP shares as
        # // the initializer.
        # assertEq(lpShares, lpSupplyBefore);
        # assertEq(
        #     hyperdrive.totalSupply(AssetId._LP_ASSET_ID),
        #     lpSupplyBefore * 2
        # );

        # // Ensure the pool APR is still approximately equal to the target APR.
        # uint256 aprAfter = calculateAPRFromReserves(hyperdrive);
        # assertApproxEqAbs(aprAfter, aprBefore, 1);

    def test_add_liquidity_with_long_at_maturity():
        # uint256 apr = 0.05e18;

        # // Initialize the pool with a large amount of capital.
        # uint256 contribution = 500_000_000e18;
        # initialize(alice, apr, contribution);
        # hyperdrive.totalSupply(AssetId._LP_ASSET_ID);

        # // Celine opens a long.
        # openLong(celine, 50_000_000e18);

        # // The term passes.
        # vm.warp(block.timestamp + POSITION_DURATION);

        # // Add liquidity with the same amount as the original contribution.
        # uint256 aprBefore = calculateAPRFromReserves(hyperdrive);
        # uint256 baseBalance = baseToken.balanceOf(address(hyperdrive));
        # uint256 lpShares = addLiquidity(bob, contribution);

        # // TODO: This suggests an issue with the flat+curve usage in the
        # //       checkpointing mechanism. These APR figures should be the same.
        # //
        # // Ensure the pool APR hasn't decreased after adding liquidity.
        # uint256 aprAfter = calculateAPRFromReserves(hyperdrive);
        # assertGe(aprAfter, aprBefore);

        # // Ensure that the contribution was transferred to Hyperdrive.
        # assertEq(baseToken.balanceOf(bob), 0);
        # assertEq(
        #     baseToken.balanceOf(address(hyperdrive)),
        #     baseBalance.add(contribution)
        # );

        # // Ensure that if the new LP withdraws, they get their money back.
        # uint256 withdrawalProceeds = removeLiquidity(bob, lpShares);
        # assertApproxEqAbs(withdrawalProceeds, contribution, 1e9);

    def test_add_liquidity_with_short_at_maturity():
        # uint256 apr = 0.05e18;

        # // Initialize the pool with a large amount of capital.
        # uint256 contribution = 500_000_000e18;
        # initialize(alice, apr, contribution);

        # // Celine opens a short.
        # openShort(celine, 50_000_000e18);

        # // The term passes.
        # vm.warp(block.timestamp + POSITION_DURATION);

        # // Add liquidity with the same amount as the original contribution.
        # uint256 aprBefore = calculateAPRFromReserves(hyperdrive);
        # uint256 baseBalance = baseToken.balanceOf(address(hyperdrive));
        # uint256 lpShares = addLiquidity(bob, contribution);

        # // TODO: This suggests an issue with the flat+curve usage in the
        # //       checkpointing mechanism. These APR figures should be the same.
        # //
        # // Ensure the pool APR hasn't increased after adding liquidity.
        # uint256 aprAfter = calculateAPRFromReserves(hyperdrive);
        # assertLe(aprAfter, aprBefore);

        # // Ensure that the contribution was transferred to Hyperdrive.
        # assertEq(baseToken.balanceOf(bob), 0);
        # assertEq(
        #     baseToken.balanceOf(address(hyperdrive)),
        #     baseBalance.add(contribution)
        # );

        # // Ensure that if the new LP withdraws, they get their money back.
        # uint256 withdrawalProceeds = removeLiquidity(bob, lpShares);

    def test_open_borrow():
        # self.assertEqual(expected_d_borrow_shares, market_deltas.d_borrow_shares)
        # self.assertEqual(expected_d_collateral, market_deltas.d_collateral)
        # self.assertEqual(expected_d_borrow_shares, market_deltas.d_borrow_shares)
        # self.assertEqual(expected_d_borrow_closed_interest, market_deltas.d_borrow_closed_interest)

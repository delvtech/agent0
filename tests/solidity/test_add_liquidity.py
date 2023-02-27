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

"""Open long market trade tests that match those being executed in the solidity repo"""
import unittest

import elfpy
import elfpy.agents.agent as agent
import elfpy.markets.hyperdrive as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.types as types
import elfpy.time as time

# pylint: disable=too-many-arguments
# pylint: disable=duplicate-code


class TestOpenLong(unittest.TestCase):
    """Test opening a long in hyperdrive"""

    contribution: float = 500_000_000
    target_apr: float = 0.05
    position_duration: int = 180
    alice: agent.Agent
    bob: agent.Agent
    celine: agent.Agent
    hyperdrive: hyperdrive_market.Market

    def setUp(self):
        """Set up agent, pricing model, & market for the subsequent tests.
        This function is run before each test method.
        """
        self.alice = agent.Agent(wallet_address=0, budget=self.contribution)
        self.bob = agent.Agent(wallet_address=1, budget=self.contribution)
        self.celine = agent.Agent(wallet_address=2, budget=self.contribution)
        pricing_model = hyperdrive_pm.HyperdrivePricingModel()
        market_state = hyperdrive_market.MarketState()
        self.hyperdrive = hyperdrive_market.Market(  # TODO: is this going to reset for each test func?
            pricing_model=pricing_model,
            market_state=market_state,
            position_duration=time.StretchedTime(
                days=365, time_stretch=pricing_model.calc_time_stretch(self.target_apr), normalizing_constant=365
            ),
        )
        _, wallet_deltas = self.hyperdrive.initialize(self.alice.wallet.address, self.contribution, 0.05)
        self.alice.update_wallet(wallet_deltas)

    def verify_open_long(
        self,
        user: agent.Agent,
        market_state_before: hyperdrive_market.MarketState,
        contribution: float,
        base_amount: float,
        unsigned_bond_amount: float,
        maturity_time: float,
        apr_before: float,
    ):
        """Open a long then make sure the market state is correct"""
        # verify the base transfers
        self.assertEqual(
            user.wallet.balance.amount,
            0,
            msg=f"{user.wallet.balance.amount=} is not correct",
        )
        hyperdrive_base_amount = self.hyperdrive.market_state.share_reserves * self.hyperdrive.market_state.share_price
        self.assertEqual(
            hyperdrive_base_amount,
            contribution + base_amount,
            msg=f"{hyperdrive_base_amount=} is not correct",
        )
        # verify that opening a long doesn't make the APR go up
        # TODO: The above comment is from the solidity code; but I think it means to say "DOES" make the apr go up?
        self.assertGreater(
            apr_before,
            self.hyperdrive.fixed_apr,
            msg=f"{apr_before=} should be greater than {self.hyperdrive.fixed_apr=}",
        )
        # verify that the reserves were updated correctly
        share_amount = base_amount / self.hyperdrive.market_state.share_price
        self.assertEqual(
            self.hyperdrive.market_state.share_reserves,
            market_state_before.share_reserves + share_amount,
            msg=f"{self.hyperdrive.market_state.share_price=} is not correct",
        )
        # TODO: why is this approx?
        # if we have a rounding error then we should be handling it internally
        # so the final outputs are exactly as expected
        # issue #112
        # issue #57
        self.assertAlmostEqual(
            self.hyperdrive.market_state.bond_reserves,
            market_state_before.bond_reserves - unsigned_bond_amount,
            delta=10 * elfpy.WEI,
            msg=f"{self.hyperdrive.market_state.bond_reserves=} is not correct",
        )
        self.assertEqual(
            self.hyperdrive.market_state.lp_total_supply,
            market_state_before.lp_total_supply,
            msg=f"{self.hyperdrive.market_state.lp_total_supply=} is not correct",
        )
        self.assertEqual(
            self.hyperdrive.market_state.share_price,
            market_state_before.share_price,
            msg=f"{self.hyperdrive.market_state.share_price=} is not correct",
        )
        self.assertAlmostEqual(
            self.hyperdrive.market_state.longs_outstanding,
            market_state_before.longs_outstanding + unsigned_bond_amount,
            delta=10 * elfpy.WEI,
            msg=f"{self.hyperdrive.market_state.longs_outstanding=} is not correct",
        )
        # self.assertAlmostEqual(
        #    self.hyperdrive.market_state.long_average_maturity_time,
        #    maturity_time,
        #    delta=100 * elfpy.WEI,
        #    msg=f"{self.hyperdrive.market_state.long_average_maturity_time=} is not correct",
        # )
        self.assertEqual(
            self.hyperdrive.market_state.long_base_volume,
            base_amount,
            msg=f"{self.hyperdrive.market_state.long_base_volume=} is not correct",
        )
        # checkpoint_time = maturity_time - self.position_duration
        # self.assertEqual(
        #    self.hyperdrive.long_base_volume_checkpoints(checkpoint_time),
        #    base_amount,
        # )
        self.assertEqual(
            self.hyperdrive.market_state.shorts_outstanding,
            market_state_before.shorts_outstanding,
            msg=f"{self.hyperdrive.market_state.shorts_outstanding=} is not correct",
        )
        self.assertEqual(
            self.hyperdrive.market_state.short_average_maturity_time,
            0,
            msg=f"{self.hyperdrive.market_state.short_average_maturity_time=} is not correct",
        )
        self.assertEqual(
            self.hyperdrive.market_state.short_base_volume,
            0,
            msg=f"{self.hyperdrive.market_state.short_base_volume=} is not correct",
        )
        # self.assertEqual(
        #    self.hyperdrive.market_state.short_base_volume_checkpoints(checkpoint_time),
        #    0,
        # )

    def test_open_long_failure_zero_amount(self):
        """Purchasing bonds with zero base fails"""
        with self.assertRaises(AssertionError):
            self.hyperdrive.open_long(self.bob.wallet.address, 0)

    def test_open_long_failure_extreme_amount(self):
        """Purchasing more bonds than exist fails"""
        base_amount = self.hyperdrive.market_state.bond_reserves
        with self.assertRaises(AssertionError):
            self.hyperdrive.open_long(self.bob.wallet.address, base_amount)

    def test_open_long(self):
        """Open a long & check that accounting is done correctly"""
        base_amount = 10
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
        market_state_before = self.hyperdrive.market_state.copy()
        apr_before = self.hyperdrive.fixed_apr
        market_deltas, agent_deltas = self.hyperdrive.open_long(self.bob.wallet.address, base_amount)
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.bob.update_wallet(agent_deltas)
        # TODO: maturity time in solidity is be latest_checkpoint() + position_duration,
        # where latest_checkpoint:
        #    block.timestamp - (block.timestamp % CHECKPOINT_DURATION);
        # That being said, in this case I think that all comes out to position_duration,
        # so the value for long_average_maturity_time is still incorrect
        self.verify_open_long(
            user=self.bob,
            market_state_before=market_state_before,
            contribution=self.contribution,
            base_amount=base_amount,
            unsigned_bond_amount=abs(market_deltas.d_bond_asset),
            maturity_time=self.position_duration,
            apr_before=apr_before,
        )


#
#    function test_open_long() external {
#        uint256 apr = 0.05e18;
#
#        // Initialize the pools with a large amount of capital.
#        uint256 contribution = 500_000_000e18;
#        initialize(alice, apr, contribution);
#
#        // Get the reserves before opening the long.
#        PoolInfo memory poolInfoBefore = getPoolInfo();
#
#        // Open a long.
#        uint256 baseAmount = 10e18;
#        (uint256 maturityTime, uint256 bondAmount) = openLong(bob, baseAmount);
#
#        // Verify that the open long updated the state correctly.
#        verifyOpenLong(
#            poolInfoBefore,
#            contribution,
#            baseAmount,
#            bondAmount,
#            maturityTime,
#            apr
#        );
#    }
#
#    function test_open_long_with_small_amount() external {
#        uint256 apr = 0.05e18;
#
#        // Initialize the pool with a large amount of capital.
#        uint256 contribution = 500_000_000e18;
#        initialize(alice, apr, contribution);
#
#        // Get the reserves before opening the long.
#        PoolInfo memory poolInfoBefore = getPoolInfo();
#
#        // Purchase a small amount of bonds.
#        uint256 baseAmount = .01e18;
#        (uint256 maturityTime, uint256 bondAmount) = openLong(bob, baseAmount);
#
#        // Verify that the open long updated the state correctly.
#        verifyOpenLong(
#            poolInfoBefore,
#            contribution,
#            baseAmount,
#            bondAmount,
#            maturityTime,
#            apr
#        );
#    }
#
#    function verifyOpenLong(
#        PoolInfo memory poolInfoBefore,
#        uint256 contribution,
#        uint256 baseAmount,
#        uint256 bondAmount,
#        uint256 maturityTime,
#        uint256 apr
#    ) internal {
#        // Verify that the open long updated the state correctly.
#        _verifyOpenLong(
#            bob,
#            poolInfoBefore,
#            contribution,
#            baseAmount,
#            bondAmount,
#            maturityTime,
#            apr
#        );
#
#        // Deploy and initialize a new pool with fees.
#        deploy(alice, apr, 0.1e18, 0.1e18);
#        initialize(alice, apr, contribution);
#
#        // Open a long with fees.
#        PoolInfo memory poolInfoBeforeWithFees = getPoolInfo();
#        (, uint256 bondAmountWithFees) = openLong(celine, baseAmount);
#
#        _verifyOpenLong(
#            celine,
#            poolInfoBeforeWithFees,
#            contribution,
#            baseAmount,
#            bondAmountWithFees,
#            maturityTime,
#            apr
#        );
#
#        // let's manually check that the fees are collected appropriately
#        // curve fee = ((1 / p) - 1) * phi * c * d_z * t
#        // p = 1 / (1 + r)
#        // roughly ((1/.9523 - 1) * .1) * 10e18 * 1 = 5e16, or 10% of the 5% bond - base spread.
#        uint256 p = (uint256(1 ether)).divDown(1 ether + 0.05 ether);
#        uint256 phi = hyperdrive.curveFee();
#        uint256 curveFeeAmount = (uint256(1 ether).divDown(p) - 1 ether)
#            .mulDown(phi)
#            .mulDown(baseAmount);
#
#        PoolInfo memory poolInfoAfterWithFees = getPoolInfo();
#        // bondAmount is from the hyperdrive without the curve fee
#        assertApproxEqAbs(
#            poolInfoAfterWithFees.bondReserves,
#            poolInfoBeforeWithFees.bondReserves - bondAmount + curveFeeAmount,
#            10
#        );
#        // bondAmount is from the hyperdrive without the curve fee
#        assertApproxEqAbs(
#            poolInfoAfterWithFees.longsOutstanding,
#            poolInfoBeforeWithFees.longsOutstanding +
#                bondAmount -
#                curveFeeAmount,
#            10
#        );
#    }
#

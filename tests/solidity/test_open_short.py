"""Test opening a short in hyperdrive"""
import unittest

import elfpy
import elfpy.agents.agent as agent
import elfpy.markets.hyperdrive as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.types as types
import elfpy.time as time


class TestOpenLong(unittest.TestCase):
    """
    Test opening a short in hyperdrive, with the following cases:
        open a short of 0 size (failure)
        open a short of extreme size (failure)
    """

    contribution: float = 500_000_000
    target_apr: float = 0.05
    position_duration: int = 180
    alice: agent.Agent
    bob: agent.Agent
    celine: agent.Agent
    hyperdrive: hyperdrive_market.Market

    def setUp(self):
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
        market_deltas, agent_deltas = self.hyperdrive.initialize(self.alice.wallet.address, self.contribution, 0.05)
        self.alice.update_wallet(agent_deltas)

    def verify_open_short(
        self,
        user: agent.Agent,
        market_state_before: hyperdrive_market.MarketState,
        contribution: float,  # budget given to the agents
        base_amount: float,  # max loss in base transferred from user to hyperdrive
        bond_amount: float,  # number of PTs shorted
        maturity_time: int,  # maturity of the opened short
        apr_before: float,
    ):  # pylint: disable=too-many-arguments
        """
        Verify that the market state is updated correctly after opening a short.
        Contains the following checks:
        - Hyperdrive received the max loss and that Bob received the short tokens
        - initializing the pool to the target APR worked
        - opening a short doesn't make the APR go down
        - reserves are updated correctly for: shares, bonds, LP tokens, share price
            longs_outstanding, long_average_maturity_time, long_base_volume, long_base_volume_checkpoints,
            shorts_outstanding, short_average_maturity_time, short_base_volume, short_base_volume_checkpoints
        """
        print(f"{user.wallet=}")
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
        # Initializing the pool to the target APR worked
        self.assertEqual(
            apr_before,
            self.hyperdrive.fixed_apr,
            msg=f"{apr_before=} should be lower than {self.hyperdrive.fixed_apr=}",
        )
        # The pool's APR didn't go down
        self.assertLess(
            apr_before,
            self.hyperdrive.fixed_apr,
            msg=f"{apr_before=} should be lower than {self.hyperdrive.fixed_apr=}",
        )
        # The reserves were updated correctly
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
            market_state_before.bond_reserves + bond_amount,
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
        # TODO:
        # self.assertAlmostEqual(
        #      self.hyperdrive.market_state.longs_outstanding,
        #      market_state_before.longs_outsstanding + bond_amount,
        #      places=10
        # )
        #
        # self.assertAlmostEqual(
        #     self.hyperdrive.market_state.long_average_maturity_time,
        #     maturity_time,
        #     100,
        # )
        # self.assertEqual(
        #     self.hyperdrive.market_state.long_base_volume,
        #     base_amount,
        # )
        # checkpoint_time = maturity_time - self.position_duration
        # self.assertEqual(
        #     self.hyperdrive.long_base_volume_checkpoints(checkpoint_time),
        #     base_amount
        # )
        # self.assertEqual(
        #     self.hyperdrive.market_state.shorts_outstanding,
        #     market_state_before.shorts_outstanding,
        # )
        # self.assertEqual(
        #     self.hyperdrive.market_state.short_average_maturity_time,
        #     0,
        # )
        # self.assertEqual(
        #     self.hyperdrive.market_state.short_base_volume,
        #     0,
        # )
        # self.assertEqual(
        #     self.hyperdrive.market_state.short_base_volume_checkpoints(checkpoint_time),
        #     0,
        # )

    def test_open_short_failure_zero_amount(self):
        """Purchasing bonds with zero base fails"""
        with self.assertRaises(AssertionError):
            self.hyperdrive.open_short(self.bob.wallet.address, 0)

    def test_open_long_failure_extreme_amount(self):
        """Purchasing more bonds than exist fails"""
        # TODO: Shouldn't this be a function of the contribution amount?
        # The max amount of base does not equal the amount of bonds, it is the result of base_pm.get_max_long
        with self.assertRaises(ValueError):
            self.hyperdrive.open_short(self.bob.wallet.address, self.hyperdrive.market_state.bond_reserves * 2)

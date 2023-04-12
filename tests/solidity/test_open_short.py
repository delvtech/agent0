"""Test opening a short in hyperdrive"""
import decimal
import unittest

import elfpy.agents.agent as agent
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time
import elfpy.types as types


class TestOpenShort(unittest.TestCase):
    """
    Test opening a short in hyperdrive, with the following cases:
        success cases:
            open a short of of 10 bonds
            open a short of of 0.01 bonds
        failure cases:
            open a short of 0 size
            open a short of extreme size
    """

    contribution: float = 500_000_000
    target_apr: float = 0.05
    term_length: int = 365
    alice: agent.Agent
    bob: agent.Agent
    celine: agent.Agent
    hyperdrive: hyperdrive_market.Market
    block_time: time.BlockTime = time.BlockTime()

    def setUp(self):
        self.alice = agent.Agent(wallet_address=0, budget=self.contribution)
        self.bob = agent.Agent(wallet_address=1, budget=self.contribution)
        self.celine = agent.Agent(wallet_address=2, budget=self.contribution)
        pricing_model = hyperdrive_pm.HyperdrivePricingModel()
        market_state = hyperdrive_market.MarketState()
        self.hyperdrive = hyperdrive_market.Market(
            pricing_model=pricing_model,
            market_state=market_state,
            block_time=self.block_time,
            position_duration=time.StretchedTime(
                days=self.term_length,
                time_stretch=pricing_model.calc_time_stretch(self.target_apr),
                normalizing_constant=self.term_length,
            ),
        )
        _, agent_deltas = self.hyperdrive.initialize(self.alice.wallet.address, self.contribution, 0.05)
        self.alice.wallet.update(agent_deltas)

    def verify_open_short(
        self,
        user: agent.Agent,
        market_state_before: hyperdrive_market.MarketState,
        base_amount: float,  # max loss in base transferred from user to hyperdrive
        unsigned_bond_amount: float,  # number of PTs shorted
        market_bond_delta: float,
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
        # TODO: this can be enabled if we add a metric that measures total TVL deposited into the smart contract
        # Total amount of base tokens locked in Hyperdrive
        # hyperdrive_base_amount
        #     = self.hyperdrive.market_state.share_reserves * self.hyperdrive.market_state.share_price
        # self.assertEqual(
        #     hyperdrive_base_amount,
        #     contribution + base_amount,
        #     msg=f"{hyperdrive_base_amount=} is not correct",
        # )
        # Bob received the short tokens
        user_wallet_shorts_amount = sum(short.balance for short in user.wallet.shorts.values())
        print(f"{user_wallet_shorts_amount=}")
        print(f"{unsigned_bond_amount=}")
        self.assertEqual(
            user_wallet_shorts_amount,
            unsigned_bond_amount,
            msg=f"{user_wallet_shorts_amount=} is not correct",
        )
        # The pool's APR didn't go down: new APR greater than old APR
        self.assertGreater(
            self.hyperdrive.fixed_apr,
            apr_before,
            msg=f"new APR={self.hyperdrive.fixed_apr=} should be greater than old APR={apr_before=} ",
        )
        # The reserves were updated correctly
        share_amount = base_amount / self.hyperdrive.market_state.share_price
        self.assertEqual(  # share reserves
            self.hyperdrive.market_state.share_reserves,
            market_state_before.share_reserves + share_amount,
            msg=f"{self.hyperdrive.market_state.share_reserves=} is not correct",
        )

        self.assertEqual(  # bond reserves
            self.hyperdrive.market_state.bond_reserves,
            market_state_before.bond_reserves + market_bond_delta,
            msg=f"{self.hyperdrive.market_state.bond_reserves=} is not correct",
        )
        self.assertEqual(  # lp total supply
            self.hyperdrive.market_state.lp_total_supply,
            market_state_before.lp_total_supply,
            msg=f"{self.hyperdrive.market_state.lp_total_supply=} is not correct",
        )
        self.assertEqual(  # share price
            self.hyperdrive.market_state.share_price,
            market_state_before.share_price,
            msg=f"{self.hyperdrive.market_state.share_price=} is not correct",
        )
        self.assertEqual(  # longs outstanding
            self.hyperdrive.market_state.longs_outstanding,
            market_state_before.longs_outstanding,
            msg=f"{self.hyperdrive.market_state.longs_outstanding=} is not correct",
        )
        self.assertEqual(  # long average maturity time
            self.hyperdrive.market_state.long_average_maturity_time,
            0,
            msg=f"{self.hyperdrive.market_state.long_average_maturity_time=} is not correct",
        )
        self.assertEqual(  # long base volume
            self.hyperdrive.market_state.long_base_volume,
            0,
            msg=f"{self.hyperdrive.market_state.long_base_volume=} is not correct",
        )
        # TODO: once we add checkpointing we will need to switch to this
        # self.hyperdrive.market_state.long_base_volume_checkpoints(checkpoint_time),
        # checkpoint_time = maturity_time - self.position_duration
        self.assertEqual(  # shorts outstanding
            self.hyperdrive.market_state.shorts_outstanding,
            market_state_before.shorts_outstanding + unsigned_bond_amount,
            msg=f"{self.hyperdrive.market_state.shorts_outstanding=} is not correct",
        )
        self.assertEqual(  # short average maturity time
            self.hyperdrive.market_state.short_average_maturity_time,
            maturity_time,
            msg=f"{self.hyperdrive.market_state.short_average_maturity_time=} is not correct",
        )
        self.assertEqual(  # short base volume
            self.hyperdrive.market_state.short_base_volume,
            abs(base_amount),
            msg=f"{self.hyperdrive.market_state.short_base_volume=} is not correct",
        )
        # TODO: once we add checkpointing we will need to switch to this
        # self.hyperdrive.market_state.short_base_volume_checkpoints(checkpoint_time),

    def test_open_short_failure_zero_amount(self):
        """shorting bonds with zero base fails"""
        with self.assertRaises(AssertionError):
            self.hyperdrive.open_short(self.bob.wallet, 0)

    def test_open_short_failure_extreme_amount(self):
        """shorting more bonds than there is base in the market fails"""
        # The max amount of base does not equal the amount of bonds, it is the result of base_pm.get_max_long
        bond_amount = self.hyperdrive.market_state.share_reserves * 2
        with self.assertRaises(decimal.InvalidOperation):
            self.hyperdrive.open_short(self.bob.wallet, bond_amount)

    def test_open_short(self):
        """Open a short & check that accounting is done correctly"""
        print("test_open_short")
        bond_amount = 10
        self.bob.budget = bond_amount
        self.bob.wallet.balance = types.Quantity(amount=bond_amount, unit=types.TokenType.PT)
        market_state_before = self.hyperdrive.market_state.copy()
        apr_before = self.hyperdrive.fixed_apr
        market_deltas, agent_deltas = self.hyperdrive.open_short(self.bob.wallet, bond_amount)
        unsigned_bond_amount = agent_deltas.shorts[self.hyperdrive.latest_checkpoint_time].balance
        print(f"  {unsigned_bond_amount=}")
        self.verify_open_short(
            user=self.bob,
            market_state_before=market_state_before,
            base_amount=market_deltas.d_base_asset,
            unsigned_bond_amount=unsigned_bond_amount,
            market_bond_delta=market_deltas.d_bond_asset,
            maturity_time=int(self.term_length / 365),
            apr_before=apr_before,
        )

    def test_open_short_with_small_amount(self):
        """Open a tiny short & check that accounting is done correctly"""
        print("test_open_short_with_small_amount")
        bond_amount = 0.01
        self.bob.budget = bond_amount
        self.bob.wallet.balance = types.Quantity(amount=bond_amount, unit=types.TokenType.PT)
        market_state_before = self.hyperdrive.market_state.copy()
        apr_before = self.hyperdrive.fixed_apr
        market_deltas, agent_deltas = self.hyperdrive.open_short(self.bob.wallet, bond_amount)
        unsigned_bond_amount = agent_deltas.shorts[self.hyperdrive.latest_checkpoint_time].balance
        self.verify_open_short(
            user=self.bob,
            market_state_before=market_state_before,
            base_amount=market_deltas.d_base_asset,
            unsigned_bond_amount=unsigned_bond_amount,
            market_bond_delta=market_deltas.d_bond_asset,
            maturity_time=int(self.term_length / 365),
            apr_before=apr_before,
        )

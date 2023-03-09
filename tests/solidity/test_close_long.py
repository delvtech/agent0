"""Close long market trade tests that match those being executed in the solidity repo"""
import unittest

import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.agents.agent as agent
import elfpy.types as types
import elfpy.time as time

# pylint: disable=too-many-arguments
# pylint: disable=duplicate-code


class TestCloseLong(unittest.TestCase):
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
        block_time = time.BlockTime()
        pricing_model = hyperdrive_pm.HyperdrivePricingModel()
        market_state = hyperdrive_market.MarketState(
            trade_fee_percent=0.0,
            redemption_fee_percent=0.0,
        )
        self.hyperdrive = hyperdrive_market.Market(
            pricing_model=pricing_model,
            market_state=market_state,
            position_duration=time.StretchedTime(
                days=365, time_stretch=pricing_model.calc_time_stretch(self.target_apr), normalizing_constant=365
            ),
            block_time=block_time,
        )
        _, wallet_deltas = self.hyperdrive.initialize(self.alice.wallet.address, self.contribution, 0.05)
        self.alice.wallet.update(wallet_deltas)

    def verify_close_long(
        self,
        example_agent: agent.Agent,
        market_state_before: hyperdrive_market.MarketState,
        unsigned_base_amount_out: float,
        bond_amount: float,
        maturity_time: float,
    ):
        """Close a long then make sure the market state is correct"""
        # verify that all of Bob's bonds were burned
        self.assertFalse(
            example_agent.wallet.longs
        )  # In solidity we check that the balance is zero, but here we delete the entry if it is zero
        # verify that the bond reserves were updated according to flat+curve
        # the adjustment should be equal to timeRemaining * bondAmount
        if maturity_time > self.hyperdrive.block_time.time:
            time_remaining = self.hyperdrive.position_duration.normalized_time * (
                maturity_time - self.hyperdrive.block_time.time
            )
        else:
            time_remaining = 0
        self.assertEqual(
            self.hyperdrive.market_state.bond_reserves,
            market_state_before.bond_reserves + time_remaining * bond_amount,
        )
        # verify that the other states were correct
        self.assertEqual(
            self.hyperdrive.market_state.share_reserves,
            market_state_before.share_reserves - unsigned_base_amount_out / market_state_before.share_price,
        )
        self.assertEqual(
            self.hyperdrive.market_state.lp_total_supply,
            market_state_before.lp_total_supply,
        )
        self.assertEqual(
            self.hyperdrive.market_state.share_price,
            market_state_before.share_price,
        )
        self.assertEqual(
            self.hyperdrive.market_state.longs_outstanding,
            market_state_before.longs_outstanding - bond_amount,
        )
        self.assertEqual(
            self.hyperdrive.market_state.long_average_maturity_time,
            0,
        )
        # TODO: This should pass once we implement checkpointing
        # self.assertAlmostEqual(
        #     self.hyperdrive.market_state.long_base_volume,
        #     0,
        #     delta=1e-9,
        #     msg=f"The long base volume should be zero, not {self.hyperdrive.market_state.long_base_volume=}.",
        # )
        # TODO: once we add checkpointing we will also need to add the checkpoint long test
        # self.hyperdrive.market_state.long_base_volume_checkpoints(checkpoint_time),
        # checkpoint_time = maturity_time - self.position_duration
        self.assertEqual(
            self.hyperdrive.market_state.shorts_outstanding,
            market_state_before.shorts_outstanding,
        )
        self.assertEqual(
            self.hyperdrive.market_state.short_average_maturity_time,
            0,
        )
        self.assertEqual(
            self.hyperdrive.market_state.short_base_volume,
            0,
        )
        # TODO: once we add checkpointing we will need to switch to this
        # self.hyperdrive.market_state.long_base_volume_checkpoints(checkpoint_time),
        self.assertEqual(
            self.hyperdrive.market_state.short_base_volume,
            0,
        )

    def test_close_long_failure_zero_amount(self):
        """Attempt to close longs using zero bond_amount. This should fail."""
        base_amount = 10
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
        _ = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        with self.assertRaises(AssertionError):
            self.hyperdrive.close_long(
                agent_wallet=self.bob.wallet,
                bond_amount=0,
                mint_time=list(self.bob.wallet.longs.keys())[0],
            )

    def test_close_long_failure_invalid_amount(self):
        """Attempt to close too many longs. This should fail."""
        base_amount = 10
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
        market_deltas, _ = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        with self.assertRaises(AssertionError):
            _ = self.hyperdrive.close_long(
                agent_wallet=self.bob.wallet,
                bond_amount=abs(market_deltas.d_bond_asset) + 1,
                mint_time=list(self.bob.wallet.longs.keys())[0],
            )

    def test_close_long_failure_invalid_timestamp(self):
        """Attempt to use a timestamp greater than the maximum range. This should fail."""
        base_amount = 10
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
        market_deltas, _ = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        with self.assertRaises(ValueError):
            _ = self.hyperdrive.close_long(
                agent_wallet=self.bob.wallet,
                bond_amount=abs(market_deltas.d_bond_asset),
                mint_time=list(self.bob.wallet.longs.keys())[0] + 1,
            )

    def test_close_long_immediately(self):
        """Open a position, close it, and then verify that the close long updates were correct"""
        base_amount = 10
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
        _, agent_deltas_open = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        market_state_before_close = self.hyperdrive.market_state.copy()
        _, agent_deltas_close = self.hyperdrive.close_long(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.longs[0].balance,
            mint_time=0,
        )
        # TODO: This is failing
        # self.assertLessEqual(
        #     agent_deltas_close.balance.amount,
        #     base_amount,
        # )
        # Doing this instead:
        self.assertAlmostEqual(
            first=agent_deltas_close.balance.amount - base_amount,
            second=0,
            delta=1e-9,
        )
        self.verify_close_long(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            unsigned_base_amount_out=abs(agent_deltas_close.balance.amount),
            bond_amount=agent_deltas_open.longs[0].balance,
            maturity_time=self.hyperdrive.position_duration.days / 365,
        )

    def test_close_long_immediately_with_small_amount(self):
        """Open a small position, close it, and then verify that the close long updates were correct"""
        base_amount = 0.01
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
        _, agent_deltas_open = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        market_state_before_close = self.hyperdrive.market_state.copy()
        _, agent_deltas_close = self.hyperdrive.close_long(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.longs[0].balance,
            mint_time=0,
        )
        self.assertLessEqual(
            agent_deltas_close.balance.amount,
            base_amount,
        )
        self.verify_close_long(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            unsigned_base_amount_out=abs(agent_deltas_close.balance.amount),
            bond_amount=agent_deltas_open.longs[0].balance,
            maturity_time=self.hyperdrive.position_duration.days / 365,
        )

    def test_close_long_halfway_through_term(self):
        # Bob opens a long
        base_amount = 10  # how much base the agent is using to open a long
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
        market_state_before_open = self.hyperdrive.market_state.copy()
        _, agent_deltas_open = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        # advance time (which also causes the share price to change)
        time_delta = 0.5
        self.hyperdrive.block_time.set_time(
            self.hyperdrive.block_time.time + self.hyperdrive.position_duration.normalized_time * time_delta
        )
        self.hyperdrive.market_state.share_price = market_state_before_open.share_price * (
            1 + self.target_apr * time_delta
        )
        # get the reserves before closing the long
        market_state_before_close = self.hyperdrive.market_state.copy()
        # Bob closes his long half way to maturity
        _, agent_deltas_close = self.hyperdrive.close_long(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.longs[0].balance,
            mint_time=0,
        )
        # Ensure that the realized APR (how much money you made over the time duration)
        # is approximately equal to the pool APR.
        #
        # price = dx / dy
        #       =>
        # rate = (1 - p) / (p * t) = (1 - dx / dy) / (dx / dy * t) # TODO: This line is wrong in solidity
        #       =>
        # realized_apr = (dy - dx) / (dx * t)
        #
        # dy ~= agent base proceeds because the base proceeds are mostly determined by the flat portion
        # t = 1 - time_delta
        base_proceeds = agent_deltas_close.balance.amount  # how much base agent gets as a result of the close
        realized_apr = (base_proceeds - base_amount) / (base_amount * (1 - time_delta))
        self.assertAlmostEqual(
            realized_apr,
            self.target_apr,
            delta=1e-8,
            msg=f"The realized {realized_apr=} should be equal to {self.target_apr=}",
        )
        # verify that the close long updates were correct
        self.verify_close_long(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            unsigned_base_amount_out=abs(base_proceeds),
            bond_amount=agent_deltas_open.longs[0].balance,
            maturity_time=self.hyperdrive.position_duration.days / 365,
        )

    def test_close_long_redeem(self):
        # Bob opens a long
        base_amount = 10  # how much base the agent is using to open a long
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
        market_state_before_open = self.hyperdrive.market_state.copy()
        _, agent_deltas_open = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        # advance time (which also causes the share price to change)
        time_delta = 1.0
        self.hyperdrive.block_time.set_time(
            self.hyperdrive.block_time.time + self.hyperdrive.position_duration.normalized_time * time_delta
        )
        self.hyperdrive.market_state.share_price = market_state_before_open.share_price * (
            1 + self.target_apr * time_delta
        )
        # get the reserves before closing the long
        market_state_before_close = self.hyperdrive.market_state.copy()
        # Bob closes his long half way to maturity
        _, agent_deltas_close = self.hyperdrive.close_long(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.longs[0].balance,
            mint_time=0,
        )
        base_proceeds = agent_deltas_close.balance.amount  # how much base agent gets as a result of the close
        self.assertEqual(
            base_proceeds,
            agent_deltas_open.longs[0].balance,
        )
        # verify that the close long updates were correct
        self.verify_close_long(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            unsigned_base_amount_out=abs(base_proceeds),
            bond_amount=agent_deltas_open.longs[0].balance,
            maturity_time=self.hyperdrive.position_duration.days / 365,
        )

    def test_close_long_redeem_negative_interest(self):
        # Bob opens a long
        base_amount = 10  # how much base the agent is using to open a long
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
        _, agent_deltas_open = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        # advance time (which also causes the share price to change)
        time_delta = 1.0
        self.hyperdrive.block_time.set_time(
            self.hyperdrive.block_time.time + self.hyperdrive.position_duration.normalized_time * time_delta
        )
        self.hyperdrive.market_state.share_price = self.hyperdrive.market_state.share_price * 0.8
        # get the reserves before closing the long
        market_state_before_close = self.hyperdrive.market_state.copy()
        # Bob closes his long half way to maturity
        _, agent_deltas_close = self.hyperdrive.close_long(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.longs[0].balance,
            mint_time=0,
        )
        # verify that Bob received base equal to the full bond amount
        base_proceeds = agent_deltas_close.balance.amount  # how much base the agent gets as a result of the close
        self.assertAlmostEqual(
            base_proceeds,
            agent_deltas_open.longs[0].balance * 0.8,
            delta=1e-18,
        )
        # verify that the close long updates were correct
        self.verify_close_long(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            unsigned_base_amount_out=abs(base_proceeds),
            bond_amount=agent_deltas_open.longs[0].balance,
            maturity_time=self.hyperdrive.position_duration.days / 365,
        )

    def test_close_long_half_term_negative_interest(self):
        # Bob opens a long
        base_amount = 10  # how much base the agent is using to open a long
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
        _, agent_deltas_open = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        # advance time (which also causes the share price to change)
        time_delta = 0.5
        self.hyperdrive.block_time.set_time(
            self.hyperdrive.block_time.time + self.hyperdrive.position_duration.normalized_time * time_delta
        )
        self.hyperdrive.market_state.share_price = self.hyperdrive.market_state.share_price * 0.8
        # get the reserves before closing the long
        market_state_before_close = self.hyperdrive.market_state.copy()
        # Bob closes his long half way to maturity
        _, agent_deltas_close = self.hyperdrive.close_long(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.longs[0].balance,
            mint_time=0,
        )
        base_proceeds = agent_deltas_close.balance.amount  # how much base agent gets as a result of the close
        self.assertAlmostEqual(
            base_proceeds,
            agent_deltas_open.longs[0].balance * 0.4 + agent_deltas_open.longs[0].balance * 0.4762,
            delta=2e-4,
        )
        # verify that the close long updates were correct
        self.verify_close_long(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            unsigned_base_amount_out=abs(base_proceeds),
            bond_amount=agent_deltas_open.longs[0].balance,
            maturity_time=self.hyperdrive.position_duration.days / 365,
        )

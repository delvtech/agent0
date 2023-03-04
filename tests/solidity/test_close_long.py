"""Open long market trade tests that match those being executed in the solidity repo"""
import unittest

import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
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
        market_state = hyperdrive_market.MarketState()
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
        user: agent.Agent,
        market_state_before: hyperdrive_market.MarketState,
        unsigned_base_amount_out: float,
        bond_amount: float,
        maturity_time: float,
    ):
        """Close a long then make sure the market state is correct"""
        self.assertEqual(
            user.wallet.balance.amount,
            0,
            msg=f"{user.wallet.balance.amount=} is not correct",
        )
        # if maturity_time >
        # timeRemaining = _maturityTime > block.timestamp
        #    ? _maturityTime - block.timestamp
        #    : 0;
        # timeRemaining = (timeRemaining).divDown(POSITION_DURATION);
        time_remaining = 1
        self.assertEqual(
            self.hyperdrive.market_state.bond_reserves, market_state_before.bond_reserves + time_remaining * bond_amount
        )
        self.assertEqual(
            self.hyperdrive.market_state.share_reserves,
            market_state_before.share_reserves - unsigned_base_amount_out / market_state_before.share_price,
        )
        self.assertEqual(
            self.hyperdrive.market_state.lp_total_supply,
            market_state_before.lp_total_supply,
        )
        self.assertEqual(
            self.hyperdrive.market_state.longs_outstanding,
            market_state_before.longs_outstanding - bond_amount,
        )
        self.assertEqual(self.hyperdrive.market_state.long_average_maturity_time, 0)
        self.assertEqual(
            self.hyperdrive.market_state.long_base_volume,
            0,
        )
        # TODO: once we add checkpointing we will need to switch to this
        # self.hyperdrive.market_state.long_base_volume_checkpoints(checkpoint_time),
        # checkpoint_time = maturity_time - self.position_duration
        self.assertEqual(
            self.hyperdrive.market_state.long_base_volume,
            0,
        )
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


if __name__ == "__main__":
    tester = TestCloseLong()
    tester.setUp()
    tester.test_close_long_failure_invalid_amount()

"""Close long market trade tests that match those being executed in the solidity repo"""
import unittest

import pytest

import elfpy.agents.agent as agent
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time
import elfpy.types as types


# pylint: disable=too-many-arguments
# pylint: disable=duplicate-code


class TestCloseShort(unittest.TestCase):
    """
    Test opening a opening and closing a short in hyperdrive
    3 failure cases: zero amount, invalid amount, invalid timestamp
    6 success cases:
        - close immediately, with regular, and small amounts
        - redeem at maturity, with zero interest, and with negative interest (skipped)
        - close halfway thru term, with zero, and negative interest (both skipped)
    """

    contribution: float = 500_000_000
    target_apr: float = 0.05
    term_length: int = 365
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

    def verify_close_short(
        self,
        example_agent: agent.Agent,
        market_state_before: hyperdrive_market.MarketState,
        base_proceeds: float,  # trade amount - max loss
        bond_amount: float,
        maturity_time: float,
    ):
        """Close a short then make sure the market state is correct"""
        # verify that all of Bob's bonds were burned
        self.assertFalse(
            example_agent.wallet.shorts
        )  # In solidity we check that the balance is zero, but here we delete the entry if it is zero
        # verify that the bond reserves were updated according to flat+curve
        # the adjustment should be equal to timeRemaining * bondAmount
        time_remaining = 0
        if maturity_time > self.hyperdrive.block_time.time:
            time_remaining = self.hyperdrive.position_duration.normalized_time * (
                maturity_time - self.hyperdrive.block_time.time
            )
        self.assertEqual(  # bond reserves
            self.hyperdrive.market_state.bond_reserves,
            market_state_before.bond_reserves - time_remaining * bond_amount,
        )
        # verify that the other states were correct
        self.assertEqual(  # share reserves
            self.hyperdrive.market_state.share_reserves,
            market_state_before.share_reserves + base_proceeds / market_state_before.share_price,
        )
        self.assertEqual(  # lp total supply
            self.hyperdrive.market_state.lp_total_supply,
            market_state_before.lp_total_supply,
        )
        self.assertEqual(  # share price
            self.hyperdrive.market_state.share_price,
            market_state_before.share_price,
        )
        self.assertEqual(  # longs outstanding
            self.hyperdrive.market_state.longs_outstanding,
            market_state_before.longs_outstanding,
        )
        self.assertEqual(  # long average maturity time
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
        self.assertEqual(  # shorts outstanding
            self.hyperdrive.market_state.shorts_outstanding, market_state_before.shorts_outstanding - bond_amount
        )
        self.assertEqual(  # short average maturity time
            self.hyperdrive.market_state.short_average_maturity_time,
            0,
        )
        self.assertEqual(  # long base volume
            self.hyperdrive.market_state.long_base_volume,
            0,
        )
        self.assertAlmostEqual(  # short base volume
            self.hyperdrive.market_state.short_base_volume,
            0,
        )
        # TODO: once we add checkpointing we will need to switch to this
        # self.hyperdrive.market_state.long_base_volume_checkpoints(checkpoint_time),

    def test_close_short_failure_zero_amount(self):
        """Attempt to close shorts using zero bond_amount. This should fail."""
        bond_amount = 10
        self.bob.budget = bond_amount
        self.bob.wallet.balance = types.Quantity(amount=bond_amount, unit=types.TokenType.BASE)
        _ = self.hyperdrive.open_short(
            agent_wallet=self.bob.wallet,
            bond_amount=bond_amount,
        )
        with self.assertRaises(AssertionError):
            self.hyperdrive.close_short(
                agent_wallet=self.bob.wallet,
                bond_amount=0,
                mint_time=list(self.bob.wallet.shorts.keys())[0],
                open_share_price=1,
            )

    def test_close_short_failure_invalid_amount(self):
        """Attempt to close too many shorts. This should fail."""
        bond_amount = 10
        self.bob.budget = bond_amount
        self.bob.wallet.balance = types.Quantity(amount=bond_amount, unit=types.TokenType.BASE)
        _ = self.hyperdrive.open_short(
            agent_wallet=self.bob.wallet,
            bond_amount=bond_amount,
        )
        with self.assertRaises(AssertionError):
            self.hyperdrive.close_short(
                agent_wallet=self.bob.wallet,
                bond_amount=list(self.bob.wallet.shorts.values())[0].balance + 1,
                mint_time=list(self.bob.wallet.shorts.keys())[0],
                open_share_price=1,
            )

    def test_close_short_failure_invalid_timestamp(self):
        """Attempt to use a timestamp greater than the maximum range. This should fail."""
        base_amount = 10
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
        market_deltas, _ = self.hyperdrive.open_short(
            agent_wallet=self.bob.wallet,
            bond_amount=base_amount,
        )
        with self.assertRaises(ValueError):
            _ = self.hyperdrive.close_short(
                agent_wallet=self.bob.wallet,
                bond_amount=abs(market_deltas.d_bond_asset),
                mint_time=list(self.bob.wallet.shorts.keys())[0] + 1,
                open_share_price=1,
            )

    def test_close_short_immediately_with_regular_amount(self):
        """Open a position, close it immediately, with regular amount"""
        trade_amount = 10  # this will be reflected in BASE in the wallet and PTs in the short
        self.bob.budget = trade_amount
        self.bob.wallet.balance = types.Quantity(amount=trade_amount, unit=types.TokenType.BASE)
        _, agent_deltas_open = self.hyperdrive.open_short(
            agent_wallet=self.bob.wallet,
            bond_amount=trade_amount,
        )
        print(f"  after open short_base_volume: {self.hyperdrive.market_state.short_base_volume}")
        max_loss = abs(agent_deltas_open.balance.amount)
        market_state_before_close = self.hyperdrive.market_state.copy()
        _, agent_deltas_close = self.hyperdrive.close_short(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.shorts[0].balance,
            mint_time=0,
            open_share_price=1,
        )
        print(f"  after close short_base_volume: {self.hyperdrive.market_state.short_base_volume}")
        self.assertAlmostEqual(  # the amount being closed is equal to the trade_amount
            agent_deltas_close.balance.amount,
            max_loss,
            delta=1e-9,
        )
        self.assertAlmostEqual(  # your balance after closing is zero
            first=agent_deltas_close.balance.amount - max_loss,
            second=0,
            delta=1e-9,
        )
        self.verify_close_short(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            base_proceeds=trade_amount - max_loss,
            bond_amount=agent_deltas_open.shorts[0].balance,
            maturity_time=self.hyperdrive.position_duration.days / 365,
        )

    def test_close_short_immediately_with_small_amount(self):
        """Open a small position, close it immediately, with small amount"""
        trade_amount = 0.01  # this will be reflected in BASE in the wallet and PTs in the short
        self.bob.budget = trade_amount
        self.bob.wallet.balance = types.Quantity(amount=trade_amount, unit=types.TokenType.BASE)
        _, agent_deltas_open = self.hyperdrive.open_short(
            agent_wallet=self.bob.wallet,
            bond_amount=trade_amount,
        )
        max_loss = abs(agent_deltas_open.balance.amount)
        market_state_before_close = self.hyperdrive.market_state.copy()
        _, agent_deltas_close = self.hyperdrive.close_short(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.shorts[0].balance,
            mint_time=0,
            open_share_price=1,
        )
        self.assertAlmostEqual(  # the amount being closed is equal to the trade_amount
            agent_deltas_close.balance.amount,
            max_loss,
            delta=1e-9,
        )
        self.assertAlmostEqual(  # your balance after closing is zero
            first=agent_deltas_close.balance.amount - max_loss,
            second=0,
            delta=1e-9,
        )
        self.verify_close_short(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            base_proceeds=trade_amount - max_loss,
            bond_amount=agent_deltas_open.shorts[0].balance,
            maturity_time=self.hyperdrive.position_duration.days / 365,
        )

    def test_close_short_redeem_at_maturity_zero_variable_interest(self):
        """Open a position, advance time all the way through the term, close it, receiving zero variable interest"""
        # Bob opens a long
        trade_amount = 10  # this will be reflected in BASE in the wallet and PTs in the short
        self.bob.budget = trade_amount
        self.bob.wallet.balance = types.Quantity(amount=trade_amount, unit=types.TokenType.BASE)
        _ = self.hyperdrive.market_state.copy()
        _, agent_deltas_open = self.hyperdrive.open_short(
            agent_wallet=self.bob.wallet,
            bond_amount=trade_amount,
        )
        # advance time (which also causes the share price to change)
        time_delta = 1
        self.hyperdrive.block_time.set_time(
            self.hyperdrive.block_time.time + self.hyperdrive.position_duration.normalized_time * time_delta
        )
        # get the reserves before closing the short
        market_state_before_close = self.hyperdrive.market_state.copy()
        # Bob closes his short at to maturity
        market_deltas_close, agent_deltas_close = self.hyperdrive.close_short(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.shorts[0].balance,
            mint_time=0,
            open_share_price=1,
        )
        market_base_proceeds = market_deltas_close.d_base_asset
        agent_base_proceeds = agent_deltas_close.balance.amount
        self.assertEqual(  # market swaps the whole position at maturity
            market_base_proceeds,
            agent_deltas_open.shorts[0].balance,
        )
        self.assertEqual(  # Bob doesn't receive any base from closing the short (received zero variable interest)
            agent_base_proceeds,
            0,
        )
        # verify that the close long updates were correct
        self.verify_close_short(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            base_proceeds=market_base_proceeds,
            bond_amount=agent_deltas_open.shorts[0].balance,
            maturity_time=self.hyperdrive.position_duration.days / 365,
        )

    # TODO: make the below two negative interest tests work, once negative interest is implemented
    @unittest.skip("Negative interest is not implemented yet")
    def test_close_short_redeem_at_maturity_negative_variable_interest(self):
        """Open a position, advance time all the way through the term, close it, receiving negative variable interest"""
        # Bob opens a long
        trade_amount = 10  # this will be reflected in BASE in the wallet and PTs in the short
        self.bob.budget = trade_amount
        self.bob.wallet.balance = types.Quantity(amount=trade_amount, unit=types.TokenType.BASE)
        _, agent_deltas_open = self.hyperdrive.open_short(
            agent_wallet=self.bob.wallet,
            bond_amount=trade_amount,
        )
        # advance time (which also causes the share price to change)
        time_delta = 1.0
        self.hyperdrive.block_time.set_time(
            self.hyperdrive.block_time.time + self.hyperdrive.position_duration.normalized_time * time_delta
        )
        self.hyperdrive.market_state.share_price = self.hyperdrive.market_state.share_price * 0.8
        # get the reserves before closing the short
        market_state_before_close = self.hyperdrive.market_state.copy()
        # Bob closes his short at to maturity
        market_deltas_close, agent_deltas_close = self.hyperdrive.close_short(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.shorts[0].balance,
            mint_time=0,
            open_share_price=1,
        )
        market_base_proceeds = market_deltas_close.d_base_asset
        agent_base_proceeds = agent_deltas_close.balance.amount
        self.assertEqual(  # market swaps the whole position at maturity
            market_base_proceeds,
            agent_deltas_open.shorts[0].balance * 0.8,
        )
        self.assertEqual(  # Bob doesn't receive any base from closing the short
            agent_base_proceeds,
            0,
        )
        # verify that the close long updates were correct
        self.verify_close_short(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            base_proceeds=market_base_proceeds,
            bond_amount=agent_deltas_open.shorts[0].balance,
            maturity_time=self.hyperdrive.position_duration.days / 365,
        )

    @unittest.skip("Negative interest is not implemented yet")
    def test_close_short_halfway_through_term_negative_variable_interest(self):
        """Open a position, advance time halfway through the term, close it, receiving negative variable interest"""
        # Bob opens a long
        trade_amount = 10  # how much base the agent is using to open a long
        self.bob.budget = trade_amount
        self.bob.wallet.balance = types.Quantity(amount=trade_amount, unit=types.TokenType.BASE)
        _, agent_deltas_open = self.hyperdrive.open_short(
            agent_wallet=self.bob.wallet,
            bond_amount=trade_amount,
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
        market_deltas_close, agent_deltas_close = self.hyperdrive.close_short(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.shorts[0].balance,
            mint_time=0,
            open_share_price=1,
        )
        market_base_proceeds = market_deltas_close.d_base_asset
        agent_base_proceeds = agent_deltas_close.balance.amount
        self.assertEqual(  # market swaps the whole position at maturity
            market_base_proceeds,
            agent_deltas_open.shorts[0].balance * 0.8,
        )
        self.assertEqual(  # Bob doesn't receive any base from closing the short
            agent_base_proceeds,
            0,
        )
        # verify that the close long updates were correct
        self.verify_close_short(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            base_proceeds=market_base_proceeds,
            bond_amount=agent_deltas_open.shorts[0].balance,
            maturity_time=self.hyperdrive.position_duration.days / 365,
        )

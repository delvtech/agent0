"""Close long market trade tests that match those being executed in the solidity repo"""
import unittest

import elfpy.agents.agent as elf_agent
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time
from elfpy.time.time import TimeUnit
import elfpy.types as types
from elfpy.math import FixedPoint

# pylint: disable=too-many-arguments
# TODO: Remove duplicate code disable once float code is removed
# pylint: disable=duplicate-code


class TestCloseLong(unittest.TestCase):
    """Test opening a long in hyperdrive"""

    APPROX_EQ: FixedPoint = FixedPoint(1e2)

    contribution: FixedPoint = FixedPoint("500_000_000.0")
    target_apr: FixedPoint = FixedPoint("0.05")
    term_length: FixedPoint = FixedPoint("365.0")
    alice: elf_agent.AgentFP
    bob: elf_agent.AgentFP
    celine: elf_agent.AgentFP
    hyperdrive: hyperdrive_market.MarketFP
    block_time: time.BlockTimeFP

    def setUp(self):
        """Set up agent, pricing model, & market for the subsequent tests.
        This function is run before each test method.
        """
        self.alice = elf_agent.AgentFP(wallet_address=0, budget=self.contribution)
        self.bob = elf_agent.AgentFP(wallet_address=1, budget=self.contribution)
        self.celine = elf_agent.AgentFP(wallet_address=2, budget=self.contribution)
        block_time = time.BlockTimeFP()
        pricing_model = hyperdrive_pm.HyperdrivePricingModelFP()
        market_state = hyperdrive_market.MarketStateFP(
            curve_fee_multiple=FixedPoint(0),
            flat_fee_multiple=FixedPoint(0),
        )
        self.hyperdrive = hyperdrive_market.MarketFP(
            pricing_model=pricing_model,
            market_state=market_state,
            position_duration=time.StretchedTimeFP(
                days=self.term_length,
                time_stretch=pricing_model.calc_time_stretch(self.target_apr),
                normalizing_constant=self.term_length,
            ),
            block_time=block_time,
        )
        _, wallet_deltas = self.hyperdrive.initialize(self.alice.wallet.address, self.contribution, self.target_apr)
        self.alice.wallet.update(wallet_deltas)

    def verify_close_long(
        self,
        example_agent: elf_agent.AgentFP,
        market_state_before: hyperdrive_market.MarketStateFP,
        agent_base_paid: FixedPoint,
        agent_base_proceeds: FixedPoint,
        bond_amount: FixedPoint,
        maturity_time: FixedPoint,
    ):
        """Close a long then make sure the market state is correct"""
        # verify that all of Bob's bonds were burned
        self.assertFalse(
            example_agent.wallet.longs
        )  # In solidity we check that the balance is zero, but here we delete the entry if it is zero
        # verify that the bond reserves were updated according to flat+curve
        # the adjustment should be equal to timeRemaining * bondAmount
        if maturity_time > self.hyperdrive.block_time.time:
            time_remaining = maturity_time - self.hyperdrive.block_time.time
        else:
            time_remaining = FixedPoint(0)
        # TODO: can this be strictly less, with more precision?
        self.assertLessEqual(  # user gets less than what they put in
            agent_base_proceeds,
            agent_base_paid,
            msg="agent gets more than what they put in: agent_bond_proceeds > agent_base_paid",
        )
        self.assertAlmostEqual(  # share reserves
            self.hyperdrive.market_state.share_reserves,
            market_state_before.share_reserves - agent_base_proceeds / market_state_before.share_price,
            delta=self.APPROX_EQ,
            msg=(
                f"{self.hyperdrive.market_state.share_reserves=} should equal the time adjusted amount: "
                f"{(market_state_before.share_reserves - agent_base_proceeds / market_state_before.share_price)=}."
            ),
        )
        self.assertAlmostEqual(  # bond reserves
            self.hyperdrive.market_state.bond_reserves,
            market_state_before.bond_reserves + time_remaining * bond_amount,
            delta=self.APPROX_EQ,
            msg=(
                f"{self.hyperdrive.market_state.bond_reserves=} should equal the "
                f"time adjusted amount: {(market_state_before.bond_reserves + time_remaining * bond_amount)=}."
            ),
        )
        self.assertEqual(  # lp total supply
            self.hyperdrive.market_state.lp_total_supply,
            market_state_before.lp_total_supply,
            msg=(
                f"{self.hyperdrive.market_state.lp_total_supply=} should be unchanged after "
                f"the trade, and thus equal {market_state_before.lp_total_supply=}."
            ),
        )
        self.assertEqual(  # longs outstanding
            self.hyperdrive.market_state.longs_outstanding,
            market_state_before.longs_outstanding - bond_amount,
            msg=(
                f"{self.hyperdrive.market_state.longs_outstanding=} should be "
                f"{(market_state_before.longs_outstanding - bond_amount)=}."
            ),
        )
        self.assertEqual(  # long average maturity time
            self.hyperdrive.market_state.long_average_maturity_time,
            FixedPoint(0),
            msg=f"{self.hyperdrive.market_state.long_average_maturity_time=} should be 0.",
        )
        self.assertAlmostEqual(  # long base volume
            self.hyperdrive.market_state.long_base_volume,
            FixedPoint(0),
            delta=self.APPROX_EQ,
            msg=f"{self.hyperdrive.market_state.long_base_volume=} should be 0.",
        )
        checkpoint_time = maturity_time - self.term_length
        self.assertEqual(  # checkpoint long base volume
            self.hyperdrive.market_state.checkpoints[checkpoint_time].long_base_volume,
            FixedPoint(0),
            msg=(
                f"The long base volume at {checkpoint_time=} should be zero, "
                f"not {self.hyperdrive.market_state.checkpoints[checkpoint_time].long_base_volume=}."
            ),
        )
        self.assertEqual(  # shorts outstanding
            self.hyperdrive.market_state.shorts_outstanding,
            market_state_before.shorts_outstanding,
            msg=(
                f"The {self.hyperdrive.market_state.shorts_outstanding} should be unchanged, "
                f"and thus unchanged from {market_state_before.shorts_outstanding}."
            ),
        )
        self.assertEqual(  # short average maturity time
            self.hyperdrive.market_state.short_average_maturity_time,
            FixedPoint(0),
            msg=f"{self.hyperdrive.market_state.short_average_maturity_time=} should be 0.",
        )
        self.assertEqual(  # short base volume
            self.hyperdrive.market_state.short_base_volume,
            FixedPoint(0),
            msg=f"{self.hyperdrive.market_state.short_base_volume=} should be 0.",
        )
        self.assertEqual(  # checkpoint short base volume
            self.hyperdrive.market_state.checkpoints[checkpoint_time].short_base_volume,
            FixedPoint(0),
            msg=(
                f"The short base volume should at {checkpoint_time=} be zero,"
                f"not {self.hyperdrive.market_state.checkpoints[checkpoint_time].long_base_volume=}."
            ),
        )

    def test_close_long_failure_zero_amount(self):
        """Attempt to close longs using zero bond_amount. This should fail."""
        base_amount = FixedPoint("10.0")
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.QuantityFP(amount=base_amount, unit=types.TokenType.BASE)
        _ = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        with self.assertRaises(AssertionError):
            self.hyperdrive.close_long(
                agent_wallet=self.bob.wallet,
                bond_amount=FixedPoint(0),
                mint_time=FixedPoint(list(self.bob.wallet.longs.keys())[0]),
            )

    def test_close_long_failure_invalid_amount(self):
        """Attempt to close too many longs. This should fail."""
        base_amount = FixedPoint("10.0")
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.QuantityFP(amount=base_amount, unit=types.TokenType.BASE)
        market_deltas, _ = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        with self.assertRaises(AssertionError):
            _ = self.hyperdrive.close_long(
                agent_wallet=self.bob.wallet,
                bond_amount=market_deltas.d_bond_asset + FixedPoint(1),
                mint_time=FixedPoint(list(self.bob.wallet.longs.keys())[0]),
            )

    def test_close_long_failure_invalid_timestamp(self):
        """Attempt to use a timestamp greater than the maximum range. This should fail."""
        base_amount = FixedPoint("10.0")
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.QuantityFP(amount=base_amount, unit=types.TokenType.BASE)
        market_deltas, _ = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        with self.assertRaises(ValueError):
            _ = self.hyperdrive.close_long(
                agent_wallet=self.bob.wallet,
                bond_amount=market_deltas.d_bond_asset,
                mint_time=list(self.bob.wallet.longs.keys())[0] + FixedPoint(1),
            )

    def test_close_long_immediately_with_regular_amount(self):
        """Open a position, close it, and then verify that the close long updates were correct"""
        base_amount = FixedPoint("10.0")
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.QuantityFP(amount=base_amount, unit=types.TokenType.BASE)
        _, agent_deltas_open = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        market_state_before_close = self.hyperdrive.market_state.copy()
        _, agent_deltas_close = self.hyperdrive.close_long(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.longs[FixedPoint(0)].balance,
            mint_time=FixedPoint(0),
        )
        self.verify_close_long(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            agent_base_paid=base_amount,
            agent_base_proceeds=agent_deltas_close.balance.amount,
            bond_amount=agent_deltas_open.longs[FixedPoint(0)].balance,
            maturity_time=self.hyperdrive.position_duration.days / FixedPoint("365.0"),
        )

    def test_close_long_immediately_with_small_amount(self):
        """Open a small position, close it, and then verify that the close long updates were correct"""
        base_amount = 0.01
        base_amount = FixedPoint("0.01")
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.QuantityFP(amount=base_amount, unit=types.TokenType.BASE)
        _, agent_deltas_open = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        market_state_before_close = self.hyperdrive.market_state.copy()
        _, agent_deltas_close = self.hyperdrive.close_long(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.longs[FixedPoint(0)].balance,
            mint_time=FixedPoint(0),
        )
        self.assertLessEqual(
            agent_deltas_close.balance.amount,
            base_amount,
        )
        self.verify_close_long(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            agent_base_paid=base_amount,
            agent_base_proceeds=agent_deltas_close.balance.amount,
            bond_amount=agent_deltas_open.longs[FixedPoint(0)].balance,
            maturity_time=self.hyperdrive.position_duration.days / FixedPoint("365.0"),
        )

    def test_close_long_halfway_through_term_zero_variable_interest(self):
        """Close a long halfway through the term and check the apr realized was the target apr"""
        # Bob opens a long
        base_amount = FixedPoint("10.0")
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.QuantityFP(amount=base_amount, unit=types.TokenType.BASE)
        market_state_before_open = self.hyperdrive.market_state.copy()
        _, agent_deltas_open = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        # advance time (which also causes the share price to change)
        time_delta = FixedPoint("0.5")
        self.hyperdrive.block_time.set_time(self.hyperdrive.block_time.time + time_delta, TimeUnit.YEARS)
        self.hyperdrive.market_state.share_price = market_state_before_open.share_price * (
            FixedPoint("1.0") + self.target_apr * time_delta
        )
        # get the reserves before closing the long
        market_state_before_close = self.hyperdrive.market_state.copy()
        # Bob closes his long half way to maturity
        _, agent_deltas_close = self.hyperdrive.close_long(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.longs[FixedPoint(0)].balance,
            mint_time=FixedPoint(0),
        )
        # Ensure that the realized APR (how much money you made over the time duration)
        # is approximately equal to the pool APR.
        #
        # price = dx / dy
        #       =>
        # rate = (1 - p) / (p * t) = (1 - dx / dy) / (dx / dy * t)
        #       =>
        # realized_apr = (dy - dx) / (dx * t)
        #
        # dy ~= agent base proceeds because the base proceeds are mostly determined by the flat portion
        # t = 1 - time_delta
        base_proceeds = agent_deltas_close.balance.amount  # how much base agent gets as a result of the close
        realized_apr = (base_proceeds - base_amount) / (base_amount * (FixedPoint("1.0") - time_delta))
        self.assertAlmostEqual(  # realized return
            realized_apr,
            self.target_apr,
            delta=self.APPROX_EQ,
            msg=f"The realized {realized_apr=} should be equal to {self.target_apr=}",
        )
        # verify that the close long updates were correct
        self.verify_close_long(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            agent_base_paid=agent_deltas_open.longs[
                FixedPoint(0)
            ].balance,  # not starting amount since we're at maturity
            agent_base_proceeds=base_proceeds,
            bond_amount=agent_deltas_open.longs[FixedPoint(0)].balance,
            maturity_time=self.hyperdrive.position_duration.days / FixedPoint("365.0"),
        )

    def test_close_long_redeem_at_maturity_zero_variable_interest(self):
        """Close long at the end of term"""
        # Bob opens a long
        base_amount = FixedPoint("10.0")
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.QuantityFP(amount=base_amount, unit=types.TokenType.BASE)
        market_state_before_open = self.hyperdrive.market_state.copy()
        _, agent_deltas_open = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        # advance time (which also causes the share price to change)
        time_delta = FixedPoint("1.0")
        self.hyperdrive.block_time.tick(time_delta)
        self.hyperdrive.market_state.share_price = market_state_before_open.share_price * (
            FixedPoint("1.0") + self.target_apr * time_delta
        )
        # get the reserves before closing the long
        market_state_before_close = self.hyperdrive.market_state.copy()
        # Bob closes his long half way to maturity
        _, agent_deltas_close = self.hyperdrive.close_long(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.longs[FixedPoint(0)].balance,
            mint_time=FixedPoint(0),
        )
        base_proceeds = agent_deltas_close.balance.amount  # how much base agent gets as a result of the close
        self.assertAlmostEqual(base_proceeds, agent_deltas_open.longs[FixedPoint(0)].balance, delta=self.APPROX_EQ)
        # verify that the close long updates were correct
        self.verify_close_long(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            agent_base_paid=agent_deltas_open.longs[
                FixedPoint(0)
            ].balance,  # not starting amount since we're at maturity
            agent_base_proceeds=base_proceeds,
            bond_amount=agent_deltas_open.longs[FixedPoint(0)].balance,
            maturity_time=self.hyperdrive.position_duration.days / FixedPoint("365.0"),
        )

    @unittest.skip("Negative interest is not implemented yet")
    def test_close_long_redeem_at_maturity_negative_variable_interest(self):
        """Close a long when the interest rate was negative.

        .. todo:: This test only verifies that a long can be closed with a negative interest rate.
            There is a commented assert on the accounting that should pass after withdrawl shares are implemented.
        """
        # Bob opens a long
        base_amount = FixedPoint("10.0")
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.QuantityFP(amount=base_amount, unit=types.TokenType.BASE)
        _, agent_deltas_open = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        # advance time (which also causes the share price to change)
        time_delta = FixedPoint("1.0")
        self.hyperdrive.block_time.tick(time_delta)
        self.hyperdrive.market_state.share_price = self.hyperdrive.market_state.share_price * FixedPoint("0.8")
        # get the reserves before closing the long
        market_state_before_close = self.hyperdrive.market_state.copy()
        # Bob closes his long half way to maturity
        _, agent_deltas_close = self.hyperdrive.close_long(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.longs[FixedPoint(0)].balance,
            mint_time=FixedPoint("0.0"),
        )
        # verify that Bob received base equal to the full bond amount
        base_proceeds = agent_deltas_close.balance.amount  # how much base the agent gets as a result of the close
        # TODO: This assert won't work until we implement the negative interst & withdrawal accounting
        # self.assertAlmostEqual(
        #     base_proceeds,
        #     agent_deltas_open.longs[0].balance * 0.8,
        #     delta=self.APPROX_EQ,
        # )
        # verify that the close long updates were correct
        self.verify_close_long(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            agent_base_paid=base_amount,
            agent_base_proceeds=base_proceeds,
            bond_amount=agent_deltas_open.longs[FixedPoint(0)].balance,
            maturity_time=self.hyperdrive.position_duration.days / FixedPoint("365.0"),
        )

    @unittest.skip("Negative interest is not implemented yet")
    def test_close_long_half_through_term_negative_variable_interest(self):
        """Close a long when the interest rate was negative halfway through the term

        .. todo:: This test only verifies that a long can be closed with a negative interest rate.
            There is a commented assert on the accounting that should pass after withdrawl shares are implemented.
        """
        # Bob opens a long
        base_amount = FixedPoint("10.0")  # how much base the agent is using to open a long
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.QuantityFP(amount=base_amount, unit=types.TokenType.BASE)
        _, agent_deltas_open = self.hyperdrive.open_long(
            agent_wallet=self.bob.wallet,
            base_amount=base_amount,
        )
        # advance time (which also causes the share price to change)
        time_delta = FixedPoint("0.5")
        self.hyperdrive.block_time.tick(time_delta)
        self.hyperdrive.market_state.share_price = self.hyperdrive.market_state.share_price * FixedPoint("0.8")
        # get the reserves before closing the long
        market_state_before_close = self.hyperdrive.market_state.copy()
        # Bob closes his long half way to maturity
        _, agent_deltas_close = self.hyperdrive.close_long(
            agent_wallet=self.bob.wallet,
            bond_amount=agent_deltas_open.longs[FixedPoint(0)].balance,
            mint_time=FixedPoint("0.0"),
        )
        base_proceeds = agent_deltas_close.balance.amount  # how much base agent gets as a result of the close
        # TODO: This assert won't work until we implement the negative interst & withdrawal accounting
        # self.assertAlmostEqual(
        #     base_proceeds,
        #     agent_deltas_open.longs[0].balance * 0.4 + agent_deltas_open.longs[0].balance * 0.4762,
        #     delta=self.APPROX_EQ,
        # )
        # verify that the close long updates were correct
        self.verify_close_long(
            example_agent=self.bob,
            market_state_before=market_state_before_close,
            agent_base_paid=base_amount,
            agent_base_proceeds=base_proceeds,
            bond_amount=agent_deltas_open.longs[FixedPoint(0)].balance,
            maturity_time=self.hyperdrive.position_duration.days / FixedPoint("365.0"),
        )

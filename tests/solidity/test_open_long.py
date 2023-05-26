"""Open long market trade tests that match those being executed in the solidity repo"""
import unittest

import elfpy.agents.agent as elf_agent
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.types as types
import elfpy.time as time
from elfpy.math import FixedPoint

# pylint: disable=too-many-arguments
# TODO: Remove duplicate code disable once float code is removed
# pylint: disable=duplicate-code


class TestOpenLong(unittest.TestCase):
    """Test opening a long in hyperdrive"""

    contribution: FixedPoint = FixedPoint("500_000_000.0")
    target_apr: FixedPoint = FixedPoint("0.05")
    term_length: FixedPoint = FixedPoint("365.0")
    alice: elf_agent.Agent
    bob: elf_agent.Agent
    celine: elf_agent.Agent
    hyperdrive: hyperdrive_market.Market
    block_time: time.BlockTime

    def setUp(self):
        """Set up agent, pricing model, & market for the subsequent tests.
        This function is run before each test method.
        """
        self.alice = elf_agent.Agent(wallet_address=0, budget=self.contribution)
        self.bob = elf_agent.Agent(wallet_address=1, budget=self.contribution)
        self.celine = elf_agent.Agent(wallet_address=2, budget=self.contribution)
        self.block_time = time.BlockTime()
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
        _, wallet_deltas = self.hyperdrive.initialize(self.alice.wallet.address, self.contribution, self.target_apr)
        self.alice.wallet.update(wallet_deltas)

    def verify_open_long(
        self,
        user: elf_agent.Agent,
        market_state_before: hyperdrive_market.MarketState,
        contribution: FixedPoint,
        base_amount: FixedPoint,
        unsigned_bond_amount_out: FixedPoint,
        maturity_time: FixedPoint,
        apr_before: FixedPoint,
    ):
        """Open a long then make sure the market state is correct"""
        # verify the base transfers
        self.assertEqual(
            user.wallet.balance.amount,
            FixedPoint(0),
            msg=f"{user.wallet.balance.amount=} is not correct",
        )
        hyperdrive_base_amount = self.hyperdrive.market_state.share_reserves * self.hyperdrive.market_state.share_price
        self.assertEqual(
            hyperdrive_base_amount,
            contribution + base_amount,
            msg=f"{hyperdrive_base_amount=} is not correct",
        )
        # verify that opening a long doesn't make the APR go up
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
            msg=f"{self.hyperdrive.market_state.share_reserves=} is not correct",
        )
        self.assertEqual(
            self.hyperdrive.market_state.bond_reserves,
            market_state_before.bond_reserves - unsigned_bond_amount_out,
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
        self.assertEqual(
            self.hyperdrive.market_state.longs_outstanding,
            market_state_before.longs_outstanding + unsigned_bond_amount_out,
            msg=f"{self.hyperdrive.market_state.longs_outstanding=} is not correct",
        )
        self.assertEqual(
            self.hyperdrive.market_state.long_average_maturity_time,
            maturity_time,
            msg=f"{self.hyperdrive.market_state.long_average_maturity_time=} is not correct",
        )
        self.assertEqual(
            self.hyperdrive.market_state.long_base_volume,
            base_amount,
            msg=f"{self.hyperdrive.market_state.long_base_volume=} is not correct",
        )
        # TODO: once we add checkpointing we will need to switch to this
        # self.hyperdrive.market_state.long_base_volume_checkpoints(checkpoint_time),
        # checkpoint_time = maturity_time - self.position_duration
        self.assertEqual(
            self.hyperdrive.market_state.shorts_outstanding,
            market_state_before.shorts_outstanding,
            msg=f"{self.hyperdrive.market_state.shorts_outstanding=} is not correct",
        )
        self.assertEqual(
            self.hyperdrive.market_state.short_average_maturity_time,
            FixedPoint(0),
            msg=f"{self.hyperdrive.market_state.short_average_maturity_time=} is not correct",
        )
        self.assertEqual(
            self.hyperdrive.market_state.short_base_volume,
            FixedPoint(0),
            msg=f"{self.hyperdrive.market_state.short_base_volume=} is not correct",
        )
        # TODO: once we add checkpointing we will need to switch to this
        # self.hyperdrive.market_state.short_base_volume_checkpoints(checkpoint_time),

    def test_open_long_failure_zero_amount(self):
        """Purchasing bonds with zero base fails"""
        with self.assertRaises(AssertionError):
            self.hyperdrive.open_long(self.bob.wallet, FixedPoint(0))

    def test_open_long_failure_extreme_amount(self):
        """Purchasing more bonds than exist fails"""
        base_amount = self.hyperdrive.market_state.bond_reserves
        with self.assertRaises(AssertionError):
            self.hyperdrive.open_long(self.bob.wallet, base_amount)

    def test_open_long(self):
        """Open a long & check that accounting is done correctly"""
        base_amount = FixedPoint("10.0")
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
        market_state_before = self.hyperdrive.market_state.copy()
        apr_before = self.hyperdrive.fixed_apr
        market_deltas, _ = self.hyperdrive.open_long(self.bob.wallet, base_amount)
        self.verify_open_long(
            user=self.bob,
            market_state_before=market_state_before,
            contribution=self.contribution,
            base_amount=base_amount,
            unsigned_bond_amount_out=abs(market_deltas.d_bond_asset),
            maturity_time=self.hyperdrive.position_duration.days / FixedPoint("365.0"),
            apr_before=apr_before,
        )

    def test_open_long_with_small_amount(self):
        """Open a tiny long & check that accounting is done correctly"""
        base_amount = FixedPoint("0.01")
        self.bob.budget = base_amount
        self.bob.wallet.balance = types.Quantity(amount=base_amount, unit=types.TokenType.BASE)
        market_state_before = self.hyperdrive.market_state.copy()
        apr_before = self.hyperdrive.fixed_apr
        market_deltas, _ = self.hyperdrive.open_long(self.bob.wallet, base_amount)
        self.verify_open_long(
            user=self.bob,
            market_state_before=market_state_before,
            contribution=self.contribution,
            base_amount=base_amount,
            unsigned_bond_amount_out=abs(market_deltas.d_bond_asset),
            maturity_time=self.hyperdrive.position_duration.days / FixedPoint("365.0"),
            apr_before=apr_before,
        )

"""Remove liquidity market trade tests that match those being executed in the solidity repo"""
import unittest

import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.markets.hyperdrive.hyperdrive_pricing_model as hyperdrive_pm
import elfpy.time as time

from elfpy.agents.agent import Agent
from elfpy.agents.policies import NoActionPolicy
from elfpy.math import FixedPoint, FixedPointMath

# pylint: disable=too-many-arguments


class TestRemoveLiquidity(unittest.TestCase):
    """Test opening a long in hyperdrive"""

    APPROX_EQ: FixedPoint = FixedPoint(1e5)

    contribution: FixedPoint = FixedPoint("500_000_000.0")
    target_apr: FixedPoint = FixedPoint("0.05")
    term_length: FixedPoint = FixedPoint("365.0")
    alice: Agent
    bob: Agent
    celine: Agent
    hyperdrive: hyperdrive_market.Market

    def setUp(self):
        """Set up agent, pricing model, & market for the subsequent tests.
        This function is run before each test method.
        """
        self.alice = Agent(wallet_address=0, policy=NoActionPolicy(budget=self.contribution))
        self.bob = Agent(wallet_address=1, policy=NoActionPolicy(budget=self.contribution))
        self.celine = Agent(wallet_address=2, policy=NoActionPolicy(budget=self.contribution))
        pricing_model = hyperdrive_pm.HyperdrivePricingModel()
        market_state = hyperdrive_market.HyperdriveMarketState(
            curve_fee_multiple=FixedPoint("0.0"),
            flat_fee_multiple=FixedPoint("0.0"),
        )
        self.hyperdrive = hyperdrive_market.Market(
            pricing_model=pricing_model,
            market_state=market_state,
            position_duration=time.StretchedTime(
                days=self.term_length,
                time_stretch=pricing_model.calc_time_stretch(self.target_apr),
                normalizing_constant=self.term_length,
            ),
            block_time=time.BlockTime(),
        )
        _, wallet_deltas = self.hyperdrive.initialize(self.alice.wallet.address, self.contribution, self.target_apr)
        self.alice.wallet.update(wallet_deltas)

    def test_remove_liquidity_fail_zero_amount(self):
        """Should fail to remove zero liquidity"""
        with self.assertRaises(AssertionError):
            self.hyperdrive.remove_liquidity(self.alice.wallet, FixedPoint(0))

    def test_remove_liquidity_fail_insufficient_shares(self):
        """Should fail to remove more liquidity than the agent has"""
        with self.assertRaises(AssertionError):
            self.hyperdrive.remove_liquidity(self.alice.wallet, self.alice.wallet.lp_tokens + FixedPoint("1.0"))

    def test_remove_liquidity_no_trades(self):
        """Should remove liquidity if there are no open trades"""

        # advance time and let interest accrue
        time_delta = FixedPoint("1.0")
        self.hyperdrive.block_time.set_time(time_delta, unit=time.TimeUnit.YEARS)

        # compund interest = p * e ^(rate * time)
        # we advance by one year, and the rate is .05 / year
        accrued = self.contribution * FixedPointMath.exp(self.target_apr * time_delta)
        self.hyperdrive.market_state.share_price = accrued / self.contribution

        # alice removes all liquidity
        self.hyperdrive.remove_liquidity(self.alice.wallet, self.alice.wallet.lp_tokens)

        # make sure all alice's lp tokens were burned
        self.assertEqual(self.alice.wallet.lp_tokens, FixedPoint(0))
        self.assertEqual(self.hyperdrive.market_state.lp_total_supply, FixedPoint(0))

        # make sure pool balances went to zero
        self.assertEqual(self.hyperdrive.market_state.share_reserves, FixedPoint(0))
        self.assertEqual(self.hyperdrive.market_state.bond_reserves, FixedPoint(0))

        # there should be no withdraw shares since no margin was locked up
        self.assertEqual(self.alice.wallet.withdraw_shares, FixedPoint(0))

    def test_remove_liquidity_long_trade(self):
        """Should remove liquidity if there are open longs"""
        market_state = self.hyperdrive.market_state

        # advance time and let interest accrue
        self.hyperdrive.block_time.set_time(FixedPoint("1.0"), unit=time.TimeUnit.YEARS)

        # compund interest = p * e ^(rate * time)
        # we advance by one year, and the rate is .05 / year
        accrued = self.contribution * FixedPointMath.exp(self.target_apr * FixedPoint("0.5"))
        market_state.share_price = accrued / self.contribution

        # bob opens a long
        base_amount = FixedPoint("50_000_000.0")
        long_market_deltas, _ = self.hyperdrive.open_long(self.bob.wallet, base_amount)
        bond_amount = -long_market_deltas.d_bond_asset

        # alice removes all liquidity
        _, remove_wallet_deltas = self.hyperdrive.remove_liquidity(self.alice.wallet, self.alice.wallet.lp_tokens)
        base_proceeds = remove_wallet_deltas.balance.amount

        # make sure all alice's lp tokens were burned
        self.assertEqual(self.alice.wallet.lp_tokens, FixedPoint(0))
        self.assertEqual(market_state.lp_total_supply, FixedPoint(0))

        # make sure alice gets the correct amount of base
        base_expected = accrued + base_amount - bond_amount
        self.assertAlmostEqual(base_proceeds, base_expected, delta=self.APPROX_EQ)

        # make sure pool balances are correct
        self.assertAlmostEqual(
            market_state.share_reserves, bond_amount / market_state.share_price, delta=self.APPROX_EQ
        )
        # self.assertEqual(market_state.bond_reserves, 0)

        # ensure correct amount of withdrawal shares
        withdraw_shares_expected = (
            market_state.longs_outstanding - market_state.long_base_volume
        ) / market_state.share_price
        self.assertAlmostEqual(self.alice.wallet.withdraw_shares, withdraw_shares_expected, delta=self.APPROX_EQ)

    def test_remove_liquidity_short_trade(self):
        """Remove liquidity if there are open shorts."""

        market_state = self.hyperdrive.market_state

        # advance time and let interest accrue
        self.hyperdrive.block_time.set_time(FixedPoint("0.05"), unit=time.TimeUnit.YEARS)

        # compund interest = p * e ^(rate * time)
        # we advance by one year, and the rate is .05 / year
        accrued = self.contribution * FixedPointMath.exp(self.target_apr * FixedPoint("0.05"))
        market_state.share_price = accrued / self.contribution

        # bob opens a short
        short_amount_bonds = FixedPoint("50_000_000.0")
        _, wallet_deltas = self.hyperdrive.open_short(self.bob.wallet, short_amount_bonds)
        base_paid = abs(wallet_deltas.balance.amount)
        self.assertAlmostEqual(base_paid, FixedPoint(scaled_value=2519919637210444767879702), delta=self.APPROX_EQ)

        # alice removes all liquidity
        _, remove_wallet_deltas = self.hyperdrive.remove_liquidity(self.alice.wallet, self.alice.wallet.lp_tokens)
        base_proceeds = remove_wallet_deltas.balance.amount
        self.assertAlmostEqual(
            base_proceeds, FixedPoint(scaled_value=453771483440107986796265268), delta=self.APPROX_EQ
        )

        # make sure all alice's lp tokens were burned
        self.assertEqual(self.alice.wallet.lp_tokens, FixedPoint(0))
        self.assertEqual(market_state.lp_total_supply, FixedPoint(0))

        # make sure alice gets the correct amount of base
        base_expected = accrued + base_paid - short_amount_bonds
        # TODO: improve this.  this is also pretty bad in the solidity code.
        self.assertAlmostEqual(base_proceeds, base_expected, delta=self.APPROX_EQ)

        # make sure pool balances went to zero
        self.assertEqual(market_state.share_reserves, FixedPoint(0))
        self.assertEqual(market_state.bond_reserves, FixedPoint(0))

        # ensure correct amount of withdrawal shares
        withdraw_shares_expected = market_state.short_base_volume / market_state.share_price
        self.assertAlmostEqual(self.alice.wallet.withdraw_shares, withdraw_shares_expected, delta=self.APPROX_EQ)

"""Remove liquidity market trade tests that match those being executed in the solidity repo"""
import unittest

import elfpy.agents.agent as elf_agent
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time
from elfpy.math import FixedPoint, FixedPointMath

# pylint: disable=too-many-arguments


class TestRemoveLiquidity(unittest.TestCase):
    """Test opening a long in hyperdrive"""

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
        self.block_time = time.BlockTimeFP()
        pricing_model = hyperdrive_pm.HyperdrivePricingModelFP()
        market_state = hyperdrive_market.MarketStateFP(
            curve_fee_multiple=FixedPoint("0.0"),
            flat_fee_multiple=FixedPoint("0.0"),
        )
        self.hyperdrive = hyperdrive_market.MarketFP(
            pricing_model=pricing_model,
            market_state=market_state,
            position_duration=time.StretchedTimeFP(
                days=self.term_length,
                time_stretch=pricing_model.calc_time_stretch(self.target_apr),
                normalizing_constant=self.term_length,
            ),
            block_time=self.block_time,
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
        self.block_time.set_time(time_delta, unit=time.TimeUnit.YEARS)

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
        self.block_time.set_time(FixedPoint("1.0"), unit=time.TimeUnit.YEARS)

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
        self.assertAlmostEqual(base_proceeds, base_expected, places=6)

        # make sure pool balances are correct
        self.assertAlmostEqual(market_state.share_reserves, bond_amount / market_state.share_price, places=6)
        # self.assertEqual(market_state.bond_reserves, 0)

        # ensure correct amount of withdrawal shares
        withdraw_shares_expected = (
            market_state.longs_outstanding - market_state.long_base_volume
        ) / market_state.share_price
        self.assertAlmostEqual(self.alice.wallet.withdraw_shares, withdraw_shares_expected, places=17)

    def test_remove_liquidity_short_trade(self):
        """Should remove liquidity if there are open shorts"""
        market_state = self.hyperdrive.market_state

        # advance time and let interest accrue
        self.block_time.set_time(FixedPoint("0.05"), unit=time.TimeUnit.YEARS)

        # compund interest = p * e ^(rate * time)
        # we advance by one year, and the rate is .05 / year
        accrued = self.contribution * FixedPointMath.exp(self.target_apr * FixedPoint("0.05"))
        market_state.share_price = accrued / self.contribution

        # bob opens a short
        short_amount_bonds = FixedPoint("50_000_000.0")
        _, wallet_deltas = self.hyperdrive.open_short(self.bob.wallet, short_amount_bonds)
        base_paid = abs(wallet_deltas.balance.amount)

        # alice removes all liquidity
        _, remove_wallet_deltas = self.hyperdrive.remove_liquidity(self.alice.wallet, self.alice.wallet.lp_tokens)
        base_proceeds = remove_wallet_deltas.balance.amount

        # make sure all alice's lp tokens were burned
        self.assertEqual(self.alice.wallet.lp_tokens, FixedPoint(0))
        self.assertEqual(market_state.lp_total_supply, FixedPoint(0))

        # make sure alice gets the correct amount of base
        base_expected = accrued + base_paid - short_amount_bonds
        # TODO: improve this.  this is also pretty bad in the solidity code.
        self.assertAlmostEqual(base_proceeds, base_expected, delta=FixedPoint(1e7))

        # make sure pool balances went to zero
        self.assertEqual(market_state.share_reserves, FixedPoint(0))
        self.assertEqual(market_state.bond_reserves, FixedPoint(0))

        # ensure correct amount of withdrawal shares
        withdraw_shares_expected = market_state.short_base_volume / market_state.share_price
        self.assertAlmostEqual(self.alice.wallet.withdraw_shares, withdraw_shares_expected, places=17)

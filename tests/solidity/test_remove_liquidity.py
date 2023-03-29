"""Remove liquidity market trade tests that match those being executed in the solidity repo"""
import unittest

import numpy

import elfpy.agents.agent as agent
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time

# pylint: disable=too-many-arguments
# pylint: disable=duplicate-code


class TestRemoveLiquidity(unittest.TestCase):
    """Test opening a long in hyperdrive"""

    contribution: float = 500_000_000
    target_apr: float = 0.05
    term_length: int = 365
    alice: agent.Agent
    bob: agent.Agent
    celine: agent.Agent
    hyperdrive: hyperdrive_market.Market
    block_time: time.BlockTime

    def setUp(self):
        """Set up agent, pricing model, & market for the subsequent tests.
        This function is run before each test method.
        """
        self.alice = agent.Agent(wallet_address=0, budget=self.contribution)
        self.bob = agent.Agent(wallet_address=1, budget=self.contribution)
        self.celine = agent.Agent(wallet_address=2, budget=self.contribution)
        self.block_time = time.BlockTime()
        pricing_model = hyperdrive_pm.HyperdrivePricingModel()
        market_state = hyperdrive_market.MarketState(
            trade_fee_percent=0.0,
            redemption_fee_percent=0.0,
        )
        self.hyperdrive = hyperdrive_market.Market(
            pricing_model=pricing_model,
            market_state=market_state,
            position_duration=time.StretchedTime(
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
            self.hyperdrive.remove_liquidity(self.alice.wallet, 0)

    def test_remove_liquidity_fail_insufficient_shares(self):
        """Should fail to remove more liquidity than the agent has"""
        with self.assertRaises(ValueError):
            self.hyperdrive.remove_liquidity(self.alice.wallet, self.alice.wallet.lp_tokens + 1)

    def test_remove_liquidity_no_trades(self):
        """Should remove liquidity if there are no open trades"""

        # advance time and let interest accrue
        self.block_time.set_time(1)

        # compund interest = p * e ^(rate * time)
        # we advance by one year, and the rate is .05 / year
        accrued = self.contribution * numpy.exp(self.target_apr * 1)
        self.hyperdrive.market_state.share_price = accrued / self.contribution

        # alice removes all liquidity
        self.hyperdrive.remove_liquidity(self.alice.wallet, self.alice.wallet.lp_tokens)

        # make sure all alice's lp tokens were burned
        self.assertEqual(self.alice.wallet.lp_tokens, 0)
        self.assertEqual(self.hyperdrive.market_state.lp_total_supply, 0)

        # make sure pool balances went to zero
        self.assertEqual(self.hyperdrive.market_state.share_reserves, 0)
        self.assertEqual(self.hyperdrive.market_state.bond_reserves, 0)

        # there should be no withdraw shares since no margin was locked up
        self.assertEqual(self.alice.wallet.withdraw_shares, 0)

    def test_remove_liquidity_long_trade(self):
        """Should remove liquidity if there are open longs"""
        market_state = self.hyperdrive.market_state

        # advance time and let interest accrue
        self.block_time.set_time(1)

        # compund interest = p * e ^(rate * time)
        # we advance by one year, and the rate is .05 / year
        accrued = self.contribution * float(numpy.exp(self.target_apr * 0.5))
        market_state.share_price = accrued / self.contribution

        # bob opens a long
        base_amount = 50_000_000
        long_market_deltas, _ = self.hyperdrive.open_long(self.bob.wallet, base_amount)
        bond_amount = -long_market_deltas.d_bond_asset

        # alice removes all liquidity
        _, remove_wallet_deltas = self.hyperdrive.remove_liquidity(self.alice.wallet, self.alice.wallet.lp_tokens)
        base_proceeds = remove_wallet_deltas.balance.amount

        # make sure all alice's lp tokens were burned
        self.assertEqual(self.alice.wallet.lp_tokens, 0)
        self.assertEqual(market_state.lp_total_supply, 0)

        # make sure alice gets the correct amount of base
        base_expected = accrued + base_amount - bond_amount
        self.assertAlmostEqual(base_proceeds, base_expected, 6)

        # make sure pool balances are correct
        self.assertAlmostEqual(market_state.share_reserves, bond_amount / market_state.share_price, 6)
        # self.assertEqual(market_state.bond_reserves, 0)

        # ensure correct amount of withdrawal shares
        withdraw_shares_expected = (
            market_state.longs_outstanding - market_state.long_base_volume
        ) / market_state.share_price
        self.assertEqual(self.alice.wallet.withdraw_shares, withdraw_shares_expected)

    def test_remove_liquidity_short_trade(self):
        """Should remove liquidity if there are open shorts"""
        market_state = self.hyperdrive.market_state

        # advance time and let interest accrue
        self.block_time.set_time(1)

        # compund interest = p * e ^(rate * time)
        # we advance by one year, and the rate is .05 / year
        accrued = self.contribution * numpy.exp(self.target_apr * 1)
        market_state.share_price = accrued / self.contribution

        # bob opens a short
        short_amount_bonds = 50_000_000
        long_market_deltas, wallet_deltas = self.hyperdrive.open_short(self.bob.wallet, short_amount_bonds)
        base_paid = abs(wallet_deltas.balance.amount)
        bond_amount = long_market_deltas.d_bond_asset

        # alice removes all liquidity
        _, remove_wallet_deltas = self.hyperdrive.remove_liquidity(self.alice.wallet, self.alice.wallet.lp_tokens)
        base_proceeds = remove_wallet_deltas.balance.amount

        # make sure all alice's lp tokens were burned
        self.assertEqual(self.alice.wallet.lp_tokens, 0)
        self.assertEqual(market_state.lp_total_supply, 0)

        # make sure alice gets the correct amount of base
        base_expected = accrued + base_paid - bond_amount
        self.assertAlmostEqual(base_proceeds, base_expected, 6)

        # make sure pool balances went to zero
        self.assertEqual(market_state.share_reserves, 0)
        self.assertEqual(market_state.bond_reserves, 0)

        # ensure correct amount of withdrawal shares
        withdraw_shares_expected = market_state.short_base_volume / market_state.share_price
        self.assertEqual(self.alice.wallet.withdraw_shares, withdraw_shares_expected)

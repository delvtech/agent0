"""Withdraw shares tests that match those being executed in the solidity repo."""
import unittest

import numpy

import elfpy.agents.agent as agent
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time

# pylint: disable=too-many-arguments
# pylint: disable=duplicate-code


class TestWithdrawShares(unittest.TestCase):
    """Test withdraw shares functionality when the market is in different states."""

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

    def test_redeem_withdraw_shares_fail_insufficient_shares(self):
        """Should fail to redeem withdraw shares."""
        market_state = self.hyperdrive.market_state
        # advance time and let interest accrue
        self.block_time.set_time(1)
        # compund interest = p * e ^(rate * time)
        # we advance by one half year, and the rate is .05 / year
        accrued = self.contribution * float(numpy.exp(self.target_apr * 0.5))
        market_state.share_price = accrued / self.contribution

    def test_redeem_withdraw_shares_short(self):
        """Should fail to redeem withdraw shares."""
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

    def test_redeem_withdraw_shares_long(self):
        """Should fail to redeem withdraw shares."""
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

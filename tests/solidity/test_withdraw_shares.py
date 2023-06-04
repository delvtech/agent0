"""Withdraw shares tests that match those being executed in the solidity repo."""
import unittest

import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.markets.hyperdrive.hyperdrive_pricing_model as hyperdrive_pm
import elfpy.time as time

from elfpy.agents.agent import Agent
from elfpy.agents.policies import BasePolicy
from elfpy.math import FixedPoint, FixedPointMath

# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals


class TestWithdrawShares(unittest.TestCase):
    """Test withdraw shares functionality when the market is in different states."""

    APPROX_EQ: FixedPoint = FixedPoint(1e2)

    budget: FixedPoint = FixedPoint("500_000_000.0")
    initial_liquidity: FixedPoint = FixedPoint("500_000_000.0")
    target_apr: FixedPoint = FixedPoint("0.05")
    term_length: FixedPoint = FixedPoint("365.0")
    one_year = FixedPoint("1.0")
    alice: Agent
    bob: Agent
    celine: Agent
    hyperdrive: hyperdrive_market.Market
    block_time: time.BlockTime

    def setUp(self):
        """Set up agent, pricing model, & market for the subsequent tests.
        This function is run before each test method.
        """
        self.alice = Agent(wallet_address=0, policy=BasePolicy(budget=self.budget))
        self.bob = Agent(wallet_address=1, policy=BasePolicy(budget=self.budget))
        self.celine = Agent(wallet_address=2, policy=BasePolicy(budget=self.budget))
        self.block_time = time.BlockTime()
        pricing_model = hyperdrive_pm.HyperdrivePricingModel()
        market_state = hyperdrive_market.HyperdriveMarketState()
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
        _, wallet_deltas = self.hyperdrive.initialize(
            self.alice.wallet.address, self.initial_liquidity, self.target_apr
        )
        self.alice.wallet.update(wallet_deltas)

    # TODO: complete this
    def test_redeem_withdraw_shares_fail_insufficient_shares(self):
        """Should fail to redeem withdraw shares."""
        market_state = self.hyperdrive.market_state
        # advance time and let interest accrue
        self.block_time.set_time(FixedPoint("0.5"), time.TimeUnit.YEARS)
        # compund interest = p * e ^(rate * time)
        # we advance by one half year, and the rate is .05 / year
        accrued = self.budget * FixedPointMath.exp(self.target_apr * FixedPoint("0.5"))
        market_state.share_price = accrued / self.budget

    # TODO: complete this
    def test_redeem_withdraw_shares_short(self):
        """Should fail to redeem withdraw shares."""
        market_state = self.hyperdrive.market_state

        # advance time and let interest accrue
        self.block_time.set_time(self.one_year, time.TimeUnit.YEARS)

        # compund interest = p * e ^(rate * time)
        # we advance by one year, and the rate is .05 / year
        accrued = self.budget * FixedPointMath.exp(self.target_apr * self.one_year)
        market_state.share_price = accrued / self.budget

        # bob opens a short
        short_amount_bonds = FixedPoint("50_000_000.0")
        self.hyperdrive.open_short(self.bob.wallet, short_amount_bonds)

    def test_redeem_withdraw_shares_long(self):
        """Should receive the correct amount of withdrawal shares when there are multiple longs"""
        market_state = self.hyperdrive.market_state

        # TODO: fuzz the trade size betweeon 0 and 5M
        trade_size = FixedPoint("5_000_000.0")
        # TODO: fuzz the variable rate between 0 and 1
        self.target_apr = FixedPoint("0.05")

        # advance time and let interest accrue
        self.block_time.set_time(self.one_year, time.TimeUnit.YEARS)

        # celine opens a long
        long_market_deltas, long_agent_deltas = self.hyperdrive.open_long(self.celine.wallet, trade_size)
        bonds_purchased = abs(long_market_deltas.d_bond_asset)
        base_spent = abs(long_agent_deltas.balance.amount)

        # bob adds liquidity
        contribution = FixedPoint("5_000_000.0")
        _, lp_agent_deltas = self.hyperdrive.add_liquidity(self.bob.wallet, contribution)
        lp_shares = lp_agent_deltas.lp_tokens

        # compund interest = p * e ^(rate * time)
        # we advance by a year, and the rate is .05 / year
        self.block_time.set_time(self.one_year, time.TimeUnit.YEARS)
        base_in_pool = self.initial_liquidity + contribution + base_spent
        pool_value = base_in_pool * FixedPointMath.exp(self.target_apr * self.one_year)
        market_state.share_price = pool_value / base_in_pool

        # calculate the portion of the pool's value (after interest) that bob contributed.
        contribution_with_interest = (pool_value - base_spent) * lp_shares / market_state.lp_total_supply

        # calculate the portion of the fixed interest that bob owes
        fixed_interest_owed = (bonds_purchased - base_spent) * lp_shares / market_state.lp_total_supply

        # calculate the expectd_withdrawal_proceeds
        expected_withdrawal_proceeds = contribution_with_interest - fixed_interest_owed

        _, remove_lp_agent_deltas = self.hyperdrive.remove_liquidity(self.bob.wallet, lp_shares)
        withdrawal_proceeds = remove_lp_agent_deltas.balance.amount
        self.assertAlmostEqual(
            withdrawal_proceeds,
            expected_withdrawal_proceeds,
            delta=self.APPROX_EQ,
            msg=f"{withdrawal_proceeds=} is not almost equal to {expected_withdrawal_proceeds=}",
        )

    def test_redeem_withdraw_shares_long_long(self):
        """Should receive the correct amount of withdrawal shares when there are multiple longs"""
        variable_rate = FixedPoint("0.05")
        market_state = self.hyperdrive.market_state

        # TODO: fuzz the trade size betweeon 0 and 5M
        trade_size = FixedPoint("5_000_000.0")

        # celine opens a long
        long_market_deltas, long_agent_deltas = self.hyperdrive.open_long(self.celine.wallet, trade_size)
        bonds_purchased = abs(long_market_deltas.d_bond_asset)
        base_spent = abs(long_agent_deltas.balance.amount)

        # we advance by a 1/2 year
        half_year = self.one_year / FixedPoint("2.0")
        self.block_time.set_time(self.block_time.time + half_year, time.TimeUnit.YEARS)
        # compund interest = p * e ^(rate * time), the rate is .05 / year, time is .5 year
        base_in_pool = self.initial_liquidity + base_spent
        pool_value = base_in_pool * FixedPointMath.exp(variable_rate * half_year)
        total_shares = base_in_pool
        market_state.share_price = pool_value / total_shares

        # celine opens another long
        _, long_agent_deltas2 = self.hyperdrive.open_long(self.celine.wallet, trade_size)
        bonds_purchased2 = abs(long_market_deltas.d_bond_asset)
        base_spent2 = abs(long_agent_deltas2.balance.amount)

        # bob adds liquidity
        contribution = FixedPoint("5_000_000.0")
        _, lp_agent_deltas = self.hyperdrive.add_liquidity(self.bob.wallet, contribution)
        lp_shares = lp_agent_deltas.lp_tokens

        # we advance by a 1/2 year
        self.block_time.set_time(self.block_time.time + half_year, time.TimeUnit.YEARS)
        # compund interest = p * e ^(rate * time), the rate is .05 / year
        base_in_pool2 = pool_value + contribution + base_spent2
        pool_value2 = base_in_pool2 * FixedPointMath.exp(variable_rate * half_year)
        total_shares2 = total_shares + contribution / market_state.share_price + base_spent2 / market_state.share_price
        market_state.share_price = pool_value2 / total_shares2

        # calculate the portion of the pool's value (after interest) that bob contributed.
        contribution_with_interest = (pool_value2 - base_spent2 - base_spent) * lp_shares / market_state.lp_total_supply

        # calculate the portion of the fixed interest that bob owes
        fixed_interest_owed = (
            (bonds_purchased + bonds_purchased2 - base_spent2 - base_spent) * lp_shares / market_state.lp_total_supply
        )

        # calculate the expectd_withdrawal_proceeds
        expected_withdrawal_proceeds = contribution_with_interest - fixed_interest_owed

        _, remove_lp_agent_deltas = self.hyperdrive.remove_liquidity(self.bob.wallet, lp_shares)
        withdrawal_proceeds = remove_lp_agent_deltas.balance.amount
        self.assertAlmostEqual(withdrawal_proceeds, expected_withdrawal_proceeds, delta=self.APPROX_EQ)

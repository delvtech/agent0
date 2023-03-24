"""Trade fee tests that match those being executed in the solidity repo"""
import unittest
from typing import Optional, Tuple
from decimal import Decimal

import pytest

import elfpy.agents.agent as agent
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time
import elfpy.types as types

# pylint: disable=duplicate-code

AMOUNT = [10**i for i in range(1, 9)]  # trade amounts up to 100 million


@pytest.fixture(scope="class")
def test_fees(*args, **kwargs):
    """Test object"""
    return TestFees(*args, **kwargs)


class TestFees(unittest.TestCase):
    """Test case for fees applied to trades"""

    # pylint: disable=too-many-instance-attributes

    contribution: float = 500_000_000
    target_apr: float = 0.5
    term_length: int = 365
    trade_amount: float = 1
    alice: agent.Agent
    bob: agent.Agent
    gary: agent.Agent  # governance gary
    hyperdrive: hyperdrive_market.Market
    block_time: time.BlockTime
    pricing_model: hyperdrive_pm.HyperdrivePricingModel

    def __init__(self, target_apr: Optional[float] = None, gov_fee: float = 0.5, **kwargs):
        """Set up agent, pricing model, & market for the subsequent tests.
        This function is run before each test method.
        """
        # assign all keyword args to self
        for key, value in kwargs.items():
            setattr(self, key, value)
        if target_apr:
            self.target_apr = target_apr
        self.alice = agent.Agent(wallet_address=0, budget=self.contribution)
        self.bob = agent.Agent(wallet_address=1, budget=self.contribution)
        self.bob.budget = self.trade_amount
        self.bob.wallet.balance = types.Quantity(amount=self.trade_amount, unit=types.TokenType.BASE)
        self.gary = agent.Agent(wallet_address=2, budget=0)
        self.block_time = time.BlockTime()
        self.pricing_model = hyperdrive_pm.HyperdrivePricingModel()
        market_state = hyperdrive_market.MarketState(
            trade_fee_percent=0.1,  # 0.1e18, // curveFee
            redemption_fee_percent=0.1,  # 0.1e18, //flatFee
            governance_fee_percent=gov_fee,  # 0.5e18, //govFee
        )
        super().__init__()

        self.hyperdrive = hyperdrive_market.Market(
            pricing_model=self.pricing_model,
            market_state=market_state,
            block_time=self.block_time,
            position_duration=time.StretchedTime(
                days=self.term_length,
                time_stretch=self.pricing_model.calc_time_stretch(self.target_apr),
                normalizing_constant=self.term_length,
            ),
        )
        _, wallet_deltas = self.hyperdrive.initialize(
            wallet_address=self.alice.wallet.address,
            contribution=self.contribution,
            target_apr=self.target_apr,
        )
        self.alice.wallet.update(wallet_deltas)
        self.market_state_before_open = self.hyperdrive.market_state.copy()

    def assertAlmostEqual(self, first, second, places=None, msg=None, delta=None):
        """
        Assert that first and second are almost equal
        Using this function to cast to Decimal to avoid type comparison errors without tons of casting
        """
        # pylint: disable=too-many-arguments
        if delta is None:
            delta = 10**-16
        super().assertAlmostEqual(Decimal(first), Decimal(second), places=places, msg=msg, delta=delta)


def idfn(val):
    """Custom id function for pytest parametrize"""
    return f"amount={val:.0f}"


def get_gov_fees_accrued(test, market_state=None) -> Decimal:
    """Get the amount of gov fees that have accrued in the market state"""
    if market_state:
        return market_state.gov_fees_accrued * market_state.share_price
    return test.hyperdrive.market_state.gov_fees_accrued * Decimal(test.hyperdrive.market_state.share_price)


def warp(test, time_delta):
    """Move time forward by time_delta and update the share price to simulate interest"""
    test.hyperdrive.block_time.set_time(test.hyperdrive.block_time.time + time_delta)
    test.hyperdrive.market_state.share_price = test.market_state_before_open.share_price * (
        1 + test.target_apr * time_delta
    )


def test_did_we_get_fees():
    """Collect fees and test that the fees received in the governance address have earned interest."""
    test = test_fees()  # set up test object

    # open long
    test.hyperdrive.open_long(test.bob.wallet, test.trade_amount)

    # capture fees right after the open long trade
    gov_fees_after_open_long = get_gov_fees_accrued(test)
    test.assertGreater(gov_fees_after_open_long, 0)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_gov_fee_accrual(amount):
    """Collect fees and test that the fees received in the governance address have earned interest."""
    test = test_fees(trade_amount=amount)  # set up test object

    # open long
    test.hyperdrive.open_long(test.bob.wallet, test.trade_amount)

    # capture fees right after the open long trade
    gov_fees_after_open_long = get_gov_fees_accrued(test)

    # hyperdrive into the future
    warp(test, time_delta=0.5)

    # collect fees to Governance Gary
    test.hyperdrive.collect_gov_fee(test.gary.wallet)
    gov_balance_after = test.gary.wallet.balance.amount
    test.assertGreater(gov_balance_after, gov_fees_after_open_long)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_collect_fees_long(amount):
    """Open a long and then close close to maturity; verify that gov fees are correct"""
    test = test_fees(trade_amount=amount)  # set up test object

    # check that both gov fees and gov balance are 0 before opening a long
    gov_fees_before_open_long = get_gov_fees_accrued(test)
    test.assertEqual(gov_fees_before_open_long, 0)
    gov_balance_before_open_long = test.gary.wallet.balance.amount
    test.assertEqual(gov_balance_before_open_long, 0)

    # open long
    test.hyperdrive.open_long(test.bob.wallet, test.trade_amount)
    gov_fees_after_open_long = get_gov_fees_accrued(test)
    test.assertGreater(gov_fees_after_open_long, gov_fees_before_open_long)

    # hyperdrive into the future
    warp(test, time_delta=0.5)

    # close long
    test.hyperdrive.close_long(
        agent_wallet=test.bob.wallet,
        bond_amount=test.bob.wallet.longs[0].balance,
        mint_time=0,
    )

    # ensure that gov fees have increased
    gov_fees_after_close_long = get_gov_fees_accrued(test)
    test.assertGreater(gov_fees_after_close_long, gov_fees_after_open_long)

    # collect fees to Governance Gary
    test.hyperdrive.collect_gov_fee(test.gary.wallet)
    test.assertEqual(get_gov_fees_accrued(test), 0)

    gov_balance_after = test.gary.wallet.balance.amount
    # ensure that Governance Gary's balance has increased
    test.assertGreater(gov_balance_after, gov_balance_before_open_long)
    # ensure that Governance Gary got the exaxt fees expected
    test.assertAlmostEqual(gov_balance_after, gov_fees_after_close_long, delta=1e-16 * test.trade_amount)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_collect_fees_short(amount):
    """Open a short and then close close to maturity; verify that gov fees are correct"""
    test = test_fees(trade_amount=amount)  # set up test object

    # check that both gov fees and gov balance are 0 before opening a short
    gov_fees_before_open_short = get_gov_fees_accrued(test)
    test.assertEqual(gov_fees_before_open_short, 0)
    gov_balance_before_open_short = test.gary.wallet.balance.amount
    test.assertEqual(gov_balance_before_open_short, 0)

    # open short
    test.hyperdrive.open_short(test.bob.wallet, test.trade_amount)
    gov_fees_after_open_short = get_gov_fees_accrued(test)
    test.assertGreater(gov_fees_after_open_short, gov_fees_before_open_short)

    # hyperdrive into the future
    warp(test, time_delta=0.5)

    # close short
    test.hyperdrive.close_short(
        agent_wallet=test.bob.wallet,
        bond_amount=test.bob.wallet.shorts[0].balance,
        mint_time=0,
        open_share_price=1,
    )

    # ensure that gov fees have increased
    gov_fees_after_close_short = get_gov_fees_accrued(test)
    test.assertGreater(gov_fees_after_close_short, gov_fees_after_open_short)

    # collect fees to Governance Gary
    test.hyperdrive.collect_gov_fee(test.gary.wallet)
    gov_fees_after_collection = get_gov_fees_accrued(test)
    test.assertEqual(gov_fees_after_collection, 0)

    gov_balance_after = test.gary.wallet.balance.amount
    # ensure that Governance Gary's balance has increased
    test.assertGreater(gov_balance_after, gov_balance_before_open_short)
    # ensure that Governance Gary got the exaxt fees expected
    test.assertAlmostEqual(gov_balance_after, gov_fees_after_close_short, delta=1e-16 * test.trade_amount)


def get_all_the_fees(test: TestFees, func: str) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
    """Get all the fees from the market state"""
    # calculate time remaining
    years_remaining = time.get_years_remaining(
        market_time=test.hyperdrive.block_time.time,
        mint_time=0,
        position_duration_years=test.hyperdrive.position_duration.days / 365,
    )  # all args in units of years
    time_remaining = time.StretchedTime(
        days=years_remaining * 365,  # converting years to days
        time_stretch=test.hyperdrive.position_duration.time_stretch,
        normalizing_constant=test.hyperdrive.position_duration.normalizing_constant,
    ).normalized_time

    # calculate curve fee
    spot_price_adjusted = test.hyperdrive.spot_price
    if func == "_calculateFeesOutGivenSharesIn":  # input is in shares
        spot_price_adjusted = 1 / test.hyperdrive.spot_price  # when given shares, invert price

    curve_fee, gov_curve_fee = test.hyperdrive.pricing_model.calc_curve_fee_split(
        amount=Decimal(test.trade_amount * time_remaining),  # sent only unmatured amount to curve trade
        spot_price=Decimal(spot_price_adjusted),
        market_state=test.hyperdrive.market_state,
        func=func,
    )
    test.hyperdrive.market_state.gov_fees_accrued += gov_curve_fee
    gov_curve_fee = abs(get_gov_fees_accrued(test))

    # calculate flat fee
    flat_without_fee = test.trade_amount * test.hyperdrive.block_time.time
    redemption_fee = Decimal(flat_without_fee * test.hyperdrive.market_state.redemption_fee_percent)
    gov_redemption_fee = redemption_fee * Decimal(test.hyperdrive.market_state.governance_fee_percent)
    return curve_fee, redemption_fee, gov_curve_fee, gov_redemption_fee


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_shares_in_at_initiation_gov_fee_0p5(amount):
    """Test that the fees are calculated correctly at initiation"""
    # set up test object
    test = test_fees(target_apr=1, trade_amount=amount)  # 100% APR gives spot_price = 0.5

    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, func="_calculateFeesOutGivenSharesIn")

    test.assertAlmostEqual(curve_fee, 0.1 * test.trade_amount, delta=1e-16 * test.trade_amount)
    test.assertAlmostEqual(gov_curve_fee, 0.05 * test.trade_amount, delta=1e-16 * test.trade_amount)
    test.assertAlmostEqual(flat_fee, 0, delta=1e-16)
    test.assertAlmostEqual(gov_flat_fee, 0, delta=1e-16)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_shares_in_at_maturity_gov_fee_0p5(amount):
    """Test that the fees are calculated correctly at maturity"""
    # set up test object
    test = test_fees(target_apr=1, trade_amount=amount)  # 100% APR gives spot_price = 0.5

    warp(test, time_delta=1)  # hyperdrive into the future to maturity
    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, func="_calculateFeesOutGivenSharesIn")

    test.assertEqual(curve_fee, 0)
    test.assertEqual(gov_curve_fee, 0)
    test.assertAlmostEqual(flat_fee, 0.1 * test.trade_amount, delta=1e-16 * test.trade_amount)
    test.assertAlmostEqual(gov_flat_fee, 0.05 * test.trade_amount, delta=1e-16 * test.trade_amount)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_shares_in_at_initiation_gov_fee_0p6(amount):
    """Test that the fees are calculated correctly at initiation"""
    # set up test object
    test = test_fees(target_apr=1, gov_fee=0.6, trade_amount=amount)  # 100% APR gives spot_price = 0.5

    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, func="_calculateFeesOutGivenSharesIn")

    test.assertAlmostEqual(curve_fee, 0.1 * test.trade_amount, delta=1e-16 * test.trade_amount)
    test.assertAlmostEqual(gov_curve_fee, 0.06 * test.trade_amount, delta=1e-16 * test.trade_amount)
    test.assertAlmostEqual(flat_fee, 0, delta=1e-16 * test.trade_amount)
    test.assertAlmostEqual(gov_flat_fee, 0, delta=1e-16 * test.trade_amount)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_shares_in_at_maturity_gov_fee_0p6(amount):
    """Test that the fees are calculated correctly at maturity"""
    # set up test object
    test = test_fees(target_apr=1, gov_fee=0.6, trade_amount=amount)  # 100% APR gives spot_price = 0.5

    warp(test, time_delta=1)  # hyperdrive into the future to maturity
    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, func="_calculateFeesOutGivenSharesIn")

    test.assertEqual(curve_fee, 0)
    test.assertEqual(gov_curve_fee, 0)
    test.assertAlmostEqual(flat_fee, 0.1 * test.trade_amount, delta=1e-16 * test.trade_amount)
    test.assertAlmostEqual(gov_flat_fee, 0.06 * test.trade_amount, delta=1e-16 * test.trade_amount)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_bonds_in_at_initiation(amount):
    """Test the redeption & trade fee helper function"""
    # set up test object
    test = test_fees(target_apr=1 / 9, trade_amount=amount)  # gives spot_price = 0.9

    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, func="_calculateFeesOutGivenBondsIn")

    test.assertAlmostEqual(curve_fee + flat_fee, 0.01 * test.trade_amount, delta=1e-17 * test.trade_amount)
    test.assertAlmostEqual(gov_curve_fee + gov_flat_fee, 0.005 * test.trade_amount, delta=1e-17 * test.trade_amount)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_bonds_in_at_maturity(amount):
    """Test the redeption & trade fee helper function"""
    # set up test object
    test = test_fees(target_apr=1 / 9, trade_amount=amount)  # gives spot_price = 0.9

    warp(test, time_delta=1)  # hyperdrive into the future to maturity
    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, func="_calculateFeesOutGivenBondsIn")

    test.assertAlmostEqual(curve_fee + flat_fee, 0.1 * test.trade_amount, delta=1e-17 * test.trade_amount)
    test.assertAlmostEqual(gov_curve_fee + gov_flat_fee, 0.05 * test.trade_amount, delta=1e-17 * test.trade_amount)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_bonds_out_at_initiation(amount):
    """Test the redeption & trade fee helper function"""
    # set up test object
    test = test_fees(target_apr=1 / 9, trade_amount=amount)  # gives spot_price = 0.9

    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, func="_calculateFeesInGivenBondsOut")

    test.assertAlmostEqual(curve_fee, 0.01 * test.trade_amount, delta=1e-17 * test.trade_amount)
    test.assertAlmostEqual(gov_curve_fee, 0.005 * test.trade_amount, delta=1e-17 * test.trade_amount)
    test.assertAlmostEqual(flat_fee, 0, delta=1e-16)
    test.assertAlmostEqual(gov_flat_fee, 0, delta=1e-16)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_bonds_out_at_maturity(amount):
    """Test the redeption & trade fee helper function"""
    # set up test object
    test = test_fees(target_apr=1 / 9, trade_amount=amount)  # gives spot_price = 0.9

    warp(test, time_delta=1)  # hyperdrive into the future to maturity
    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, func="_calculateFeesInGivenBondsOut")

    test.assertAlmostEqual(curve_fee, 0, delta=1e-17)
    test.assertAlmostEqual(gov_curve_fee, 0, delta=1e-17)
    test.assertAlmostEqual(flat_fee, 0.1 * test.trade_amount, delta=1e-16 * test.trade_amount)
    test.assertAlmostEqual(gov_flat_fee, 0.05 * test.trade_amount, delta=1e-16 * test.trade_amount)

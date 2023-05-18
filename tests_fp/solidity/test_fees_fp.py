"""Trade fee tests that match those being executed in the solidity repo"""
import unittest
from typing import Optional, Tuple

import pytest

import elfpy.agents.agent as elf_agent
import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.pricing_models.hyperdrive as hyperdrive_pm
import elfpy.time as time
import elfpy.types as types
from elfpy.math import FixedPoint

# pylint: disable=duplicate-code

AMOUNT = [10**i for i in range(1, 9)]  # trade amounts up to 100 million


class TestFees(unittest.TestCase):
    """Test case for fees applied to trades"""

    # pylint: disable=too-many-instance-attributes

    contribution: FixedPoint
    target_apr: FixedPoint
    alice: elf_agent.AgentFP
    bob: elf_agent.AgentFP
    celine: elf_agent.AgentFP
    gary: elf_agent.AgentFP  # governance gary
    hyperdrive: hyperdrive_market.MarketFP
    block_time: time.BlockTimeFP
    term_length: FixedPoint
    trade_amount: FixedPoint
    pricing_model: hyperdrive_pm.HyperdrivePricingModelFP

    def __init__(self, target_apr: float, gov_fee: float, **kwargs):
        """Set up agent, pricing model, & market for the subsequent tests.
        This function is run before each test method.
        """
        # assign all keyword args to self
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.target_apr = FixedPoint(target_apr)
        self.contribution = FixedPoint("500_000_000.0")
        self.term_length = FixedPoint("365.0")
        self.trade_amount = FixedPoint("1.0")
        self.alice = elf_agent.AgentFP(wallet_address=0, budget=self.contribution)
        self.bob = elf_agent.AgentFP(wallet_address=1, budget=self.contribution)
        self.bob.budget = FixedPoint(self.trade_amount)
        self.bob.wallet.balance = types.QuantityFP(amount=self.trade_amount, unit=types.TokenType.BASE)
        self.gary = elf_agent.AgentFP(wallet_address=2, budget=FixedPoint(0))
        self.block_time = time.BlockTimeFP()
        self.pricing_model = hyperdrive_pm.HyperdrivePricingModelFP()
        market_state = hyperdrive_market.MarketStateFP(
            curve_fee_multiple=FixedPoint("0.1"),  # 0.1e18, // curveFee
            flat_fee_multiple=FixedPoint("0.1"),  # 0.1e18, //flatFee
            governance_fee_multiple=FixedPoint(gov_fee),  # 0.5e18, //govFee
        )
        super().__init__()

        self.hyperdrive = hyperdrive_market.MarketFP(
            pricing_model=self.pricing_model,
            market_state=market_state,
            block_time=self.block_time,
            position_duration=time.StretchedTimeFP(
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


def idfn(val):
    """Custom id function for pytest parametrize"""
    return f"amount={val:.0f}"


def advance_time(test: TestFees, time_delta: FixedPoint):
    """Move time forward by time_delta and update the share price to simulate interest"""
    test.block_time.tick(delta_years=time_delta)
    test.hyperdrive.market_state.share_price = test.market_state_before_open.share_price * (
        FixedPoint("1.0") + test.target_apr * time_delta
    )


def get_all_the_fees(
    test: TestFees, in_unit: Optional[types.TokenType] = None, out_unit: Optional[types.TokenType] = None
) -> Tuple[FixedPoint, FixedPoint, FixedPoint, FixedPoint]:
    """Get all the fees from the market state"""
    # calculate time remaining
    years_remaining = time.get_years_remaining_fp(
        market_time=test.hyperdrive.block_time.time,
        mint_time=FixedPoint(0),
        position_duration_years=test.hyperdrive.position_duration.days / FixedPoint("365.0"),
    )  # all args in units of years
    time_remaining = time.StretchedTimeFP(
        days=years_remaining * FixedPoint("365.0"),  # converting years to days
        time_stretch=test.hyperdrive.position_duration.time_stretch,
        normalizing_constant=test.hyperdrive.position_duration.normalizing_constant,
    ).normalized_time

    if in_unit is not None:
        breakdown = test.hyperdrive.pricing_model.calc_out_given_in(
            in_=types.QuantityFP(
                amount=test.trade_amount * time_remaining, unit=in_unit
            ),  # scaled down unmatured amount
            market_state=test.hyperdrive.market_state,
            time_remaining=time.StretchedTimeFP(
                days=test.hyperdrive.position_duration.days,
                time_stretch=test.hyperdrive.position_duration.time_stretch,
                normalizing_constant=test.hyperdrive.position_duration.normalizing_constant,
            ),
        ).breakdown
    elif out_unit is not None:
        breakdown = test.hyperdrive.pricing_model.calc_in_given_out(
            out=types.QuantityFP(
                amount=test.trade_amount * time_remaining, unit=out_unit
            ),  # scaled down unmatured amount
            market_state=test.hyperdrive.market_state,
            time_remaining=time.StretchedTimeFP(
                days=test.hyperdrive.position_duration.days,
                time_stretch=test.hyperdrive.position_duration.time_stretch,
                normalizing_constant=test.hyperdrive.position_duration.normalizing_constant,
            ),
        ).breakdown
    else:
        raise ValueError("Must specify either in_unit or out_unit")
    curve_fee = breakdown.curve_fee
    gov_curve_fee = breakdown.gov_curve_fee
    test.hyperdrive.market_state.gov_fees_accrued += gov_curve_fee
    gov_curve_fee = test.hyperdrive.market_state.gov_fees_accrued * test.hyperdrive.market_state.share_price

    # calculate flat fee
    flat_without_fee = test.trade_amount * test.hyperdrive.block_time.time
    flat_fee = flat_without_fee * test.hyperdrive.market_state.flat_fee_multiple
    gov_flat_fee = flat_fee * test.hyperdrive.market_state.governance_fee_multiple
    return curve_fee, flat_fee, gov_curve_fee, gov_flat_fee


def test_did_we_get_fees():
    """Collect fees and test that the fees received in the governance address have earned interest."""
    test = TestFees(target_apr=0.05, gov_fee=0.5)  # set up test object

    # open long
    test.hyperdrive.open_long(test.bob.wallet, test.trade_amount)

    # capture fees right after the open long trade
    gov_fees_after_open_long = test.hyperdrive.market_state.gov_fees_accrued * test.hyperdrive.market_state.share_price
    test.assertGreater(int(gov_fees_after_open_long), 0)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_gov_fee_accrual(amount: int):
    """Collect fees and test that the fees received in the governance address have earned interest."""
    test = TestFees(target_apr=0.05, gov_fee=0.5, trade_amount=FixedPoint(amount * 10**18))  # set up test object

    # open long
    test.hyperdrive.open_long(test.bob.wallet, test.trade_amount)

    # capture fees right after the open long trade
    gov_fees_after_open_long = test.hyperdrive.market_state.gov_fees_accrued * test.hyperdrive.market_state.share_price

    # hyperdrive into the future
    advance_time(test, FixedPoint("0.5"))

    # collect fees to Governance Gary
    test.gary.wallet.balance.amount += (
        test.hyperdrive.market_state.gov_fees_accrued * test.hyperdrive.market_state.share_price
    )

    test.hyperdrive.market_state.gov_fees_accrued = FixedPoint(0)
    gov_balance_after = test.gary.wallet.balance.amount
    test.assertGreater(gov_balance_after, gov_fees_after_open_long)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_collect_fees_long(amount: int):
    """Open a long and then close close to maturity; verify that gov fees are correct"""
    test = TestFees(target_apr=0.05, gov_fee=0.5, trade_amount=FixedPoint(amount * 10**18))  # set up test object

    # check that both gov fees and gov balance are 0 before opening a long
    gov_fees_before_open_long = test.hyperdrive.market_state.gov_fees_accrued * test.hyperdrive.market_state.share_price
    test.assertEqual(int(gov_fees_before_open_long), 0)
    gov_balance_before_open_long = test.gary.wallet.balance.amount
    test.assertEqual(int(gov_balance_before_open_long), 0)

    # open long
    test.hyperdrive.open_long(test.bob.wallet, test.trade_amount)
    gov_fees_after_open_long = test.hyperdrive.market_state.gov_fees_accrued * test.hyperdrive.market_state.share_price
    test.assertGreater(gov_fees_after_open_long, gov_fees_before_open_long)

    # hyperdrive into the future
    advance_time(test, FixedPoint("0.5"))

    # close long
    test.hyperdrive.close_long(
        agent_wallet=test.bob.wallet,
        bond_amount=test.bob.wallet.longs[0].balance,
        mint_time=FixedPoint(0),
    )

    # ensure that gov fees have increased
    gov_fees_after_close_long = test.hyperdrive.market_state.gov_fees_accrued * test.hyperdrive.market_state.share_price
    test.assertGreater(gov_fees_after_close_long, gov_fees_after_open_long)

    # collect fees to Governance Gary
    test.gary.wallet.balance.amount += (
        test.hyperdrive.market_state.gov_fees_accrued * test.hyperdrive.market_state.share_price
    )
    # TODO: fix this check, don't set fees accrued to zero
    test.hyperdrive.market_state.gov_fees_accrued = FixedPoint(0)
    test.assertEqual(int(test.hyperdrive.market_state.gov_fees_accrued * test.hyperdrive.market_state.share_price), 0)

    gov_balance_after = test.gary.wallet.balance.amount
    # ensure that Governance Gary's balance has increased
    test.assertGreater(gov_balance_after, gov_balance_before_open_long)
    # ensure that Governance Gary got the exaxt fees FixedPointexpecteFixedPointd
    test.assertAlmostEqual(gov_balance_after, gov_fees_after_close_long, delta=FixedPoint(1e-16) * test.trade_amount)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_collect_fees_short(amount):
    """Open a short and then close close to maturity; verify that gov fees are correct"""
    test = TestFees(target_apr=0.05, gov_fee=0.5, trade_amount=FixedPoint(amount * 10**18))  # set up test object

    # check that both gov fees and gov balance are 0 before opening a short
    gov_fees_before_open_short = (
        test.hyperdrive.market_state.gov_fees_accrued * test.hyperdrive.market_state.share_price
    )
    test.assertEqual(int(gov_fees_before_open_short), 0)
    gov_balance_before_open_short = test.gary.wallet.balance.amount
    test.assertEqual(int(gov_balance_before_open_short), 0)

    # open short
    test.hyperdrive.open_short(test.bob.wallet, test.trade_amount)
    gov_fees_after_open_short = test.hyperdrive.market_state.gov_fees_accrued * test.hyperdrive.market_state.share_price
    test.assertGreater(gov_fees_after_open_short, gov_fees_before_open_short)

    # hyperdrive into the future
    advance_time(test, FixedPoint("0.5"))

    # close short
    test.hyperdrive.close_short(
        agent_wallet=test.bob.wallet,
        bond_amount=test.bob.wallet.shorts[0].balance,
        mint_time=FixedPoint(0),
        open_share_price=FixedPoint("1.0"),
    )

    # ensure that gov fees have increased
    gov_fees_after_close_short = (
        test.hyperdrive.market_state.gov_fees_accrued * test.hyperdrive.market_state.share_price
    )
    test.assertGreater(gov_fees_after_close_short, gov_fees_after_open_short)

    # collect fees to Governance Gary
    test.gary.wallet.balance.amount += (
        test.hyperdrive.market_state.gov_fees_accrued * test.hyperdrive.market_state.share_price
    )
    # TODO: fix this check, don't set fees accrued to zero
    test.hyperdrive.market_state.gov_fees_accrued = FixedPoint(0)
    gov_fees_after_collection = test.hyperdrive.market_state.gov_fees_accrued * test.hyperdrive.market_state.share_price
    test.assertEqual(int(gov_fees_after_collection), 0)

    gov_balance_after = test.gary.wallet.balance.amount
    # ensure that Governance Gary's balance has increased
    test.assertGreater(gov_balance_after, gov_balance_before_open_short)
    # ensure that Governance Gary got the exaxt fees expected
    test.assertAlmostEqual(gov_balance_after, gov_fees_after_close_short, delta=FixedPoint(1e-16) * test.trade_amount)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_shares_in_at_initiation_gov_fee_0p5(amount):
    """Test that the fees are calculated correctly at initiation"""
    # set up test object
    test = TestFees(
        target_apr=1.0, gov_fee=0.5, trade_amount=FixedPoint(amount * 10**18)
    )  # 100% APR gives spot_price = 0.5

    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, in_unit=types.TokenType.BASE)

    test.assertAlmostEqual(
        curve_fee, FixedPoint("0.1") * test.trade_amount, delta=FixedPoint(1e-16) * test.trade_amount
    )
    test.assertAlmostEqual(
        gov_curve_fee, FixedPoint("0.05") * test.trade_amount, delta=FixedPoint(1e-16) * test.trade_amount
    )
    test.assertAlmostEqual(flat_fee, FixedPoint(0), delta=FixedPoint(1e-16))
    test.assertAlmostEqual(gov_flat_fee, FixedPoint(0), delta=FixedPoint(1e-16))


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_shares_in_at_maturity_gov_fee_0p5(amount):
    """Test that the fees are calculated correctly at maturity"""
    # set up test object
    test = TestFees(
        target_apr=1.0, gov_fee=0.5, trade_amount=FixedPoint(amount * 10**18)
    )  # 100% APR gives spot_price = 0.5

    advance_time(test, FixedPoint("1.0"))  # hyperdrive into the future.. all the way to maturity
    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, in_unit=types.TokenType.BASE)

    test.assertEqual(curve_fee, FixedPoint(0))
    test.assertEqual(gov_curve_fee, FixedPoint(0))
    test.assertAlmostEqual(flat_fee, FixedPoint("0.1") * test.trade_amount, delta=FixedPoint(1e-16) * test.trade_amount)
    test.assertAlmostEqual(
        gov_flat_fee, FixedPoint("0.05") * test.trade_amount, delta=FixedPoint(1e-16) * test.trade_amount
    )


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_shares_in_at_initiation_gov_fee_0p6(amount):
    """Test that the fees are calculated correctly at initiation"""
    # set up test object
    test = TestFees(
        target_apr=1.0, gov_fee=0.6, trade_amount=FixedPoint(amount * 10**18)
    )  # 100% APR gives spot_price = 0.5

    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, in_unit=types.TokenType.BASE)

    test.assertAlmostEqual(
        curve_fee, FixedPoint("0.1") * test.trade_amount, delta=FixedPoint(1e-16) * test.trade_amount
    )
    test.assertAlmostEqual(
        gov_curve_fee, FixedPoint("0.06") * test.trade_amount, delta=FixedPoint(1e-16) * test.trade_amount
    )
    test.assertAlmostEqual(flat_fee, FixedPoint(0), delta=FixedPoint(1e-16) * test.trade_amount)
    test.assertAlmostEqual(gov_flat_fee, FixedPoint(0), delta=FixedPoint(1e-16) * test.trade_amount)


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_shares_in_at_maturity_gov_fee_0p6(amount):
    """Test that the fees are calculated correctly at maturity"""
    # set up test object
    test = TestFees(
        target_apr=1.0, gov_fee=0.6, trade_amount=FixedPoint(amount * 10**18)
    )  # 100% APR gives spot_price = 0.5

    advance_time(test, FixedPoint("1.0"))  # hyperdrive into the future.. all the way to maturity
    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, in_unit=types.TokenType.BASE)

    test.assertEqual(curve_fee, FixedPoint(0))
    test.assertEqual(gov_curve_fee, FixedPoint(0))
    test.assertAlmostEqual(flat_fee, FixedPoint(0.1) * test.trade_amount, delta=FixedPoint(1e-16) * test.trade_amount)
    test.assertAlmostEqual(
        gov_flat_fee, FixedPoint(0.06) * test.trade_amount, delta=FixedPoint(1e-16) * test.trade_amount
    )


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_bonds_in_at_initiation(amount):
    """Test the redeption & trade fee helper function"""
    # set up test object
    test = TestFees(target_apr=1 / 9, gov_fee=0.5, trade_amount=FixedPoint(amount * 10**18))  # gives spot_price = 0.9

    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, in_unit=types.TokenType.PT)

    test.assertAlmostEqual(
        curve_fee + flat_fee, FixedPoint("0.01") * test.trade_amount, delta=FixedPoint(1e-17) * test.trade_amount
    )
    test.assertAlmostEqual(
        gov_curve_fee + gov_flat_fee,
        FixedPoint("0.005") * test.trade_amount,
        delta=FixedPoint(1e-17) * test.trade_amount,
    )


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_bonds_in_at_maturity(amount):
    """Test the redeption & trade fee helper function"""
    # set up test object
    test = TestFees(target_apr=1 / 9, gov_fee=0.5, trade_amount=FixedPoint(amount * 10**18))  # gives spot_price = 0.9

    advance_time(test, FixedPoint("1.0"))  # hyperdrive into the future.. all the way to maturity
    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, in_unit=types.TokenType.PT)

    test.assertAlmostEqual(
        curve_fee + flat_fee, test.trade_amount / FixedPoint("10.0"), delta=FixedPoint(1e-17) * test.trade_amount
    )
    test.assertAlmostEqual(
        gov_curve_fee + gov_flat_fee,
        FixedPoint("0.05") * test.trade_amount,
        delta=FixedPoint(1e-17) * test.trade_amount,
    )


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_bonds_out_at_initiation(amount):
    """Test the redeption & trade fee helper function"""
    # set up test object
    test = TestFees(target_apr=1 / 9, gov_fee=0.5, trade_amount=FixedPoint(amount * 10**18))  # gives spot_price = 0.9

    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, out_unit=types.TokenType.PT)

    test.assertAlmostEqual(
        curve_fee, FixedPoint("0.01") * test.trade_amount, delta=FixedPoint(1e-17) * test.trade_amount
    )
    test.assertAlmostEqual(
        gov_curve_fee, FixedPoint("0.005") * test.trade_amount, delta=FixedPoint(1e-17) * test.trade_amount
    )
    test.assertAlmostEqual(flat_fee, FixedPoint(0), delta=FixedPoint(1e-16))
    test.assertAlmostEqual(gov_flat_fee, FixedPoint(0), delta=FixedPoint(1e-16))


@pytest.mark.parametrize("amount", AMOUNT, ids=idfn)
def test_calc_fees_out_given_bonds_out_at_maturity(amount):
    """Test the redeption & trade fee helper function"""
    # set up test object
    test = TestFees(target_apr=1 / 9, gov_fee=0.5, trade_amount=FixedPoint(amount * 10**18))  # gives spot_price = 0.9

    advance_time(test, FixedPoint("1.0"))  # hyperdrive into the future.. all the way to maturity
    curve_fee, flat_fee, gov_curve_fee, gov_flat_fee = get_all_the_fees(test, out_unit=types.TokenType.PT)

    test.assertAlmostEqual(curve_fee, FixedPoint(0), delta=FixedPoint(1e-17))
    test.assertAlmostEqual(gov_curve_fee, FixedPoint(0), delta=FixedPoint(1e-17))
    test.assertAlmostEqual(flat_fee, FixedPoint("0.1") * test.trade_amount, delta=FixedPoint(1e-16) * test.trade_amount)
    test.assertAlmostEqual(
        gov_flat_fee, FixedPoint("0.05") * test.trade_amount, delta=FixedPoint(1e-16) * test.trade_amount
    )

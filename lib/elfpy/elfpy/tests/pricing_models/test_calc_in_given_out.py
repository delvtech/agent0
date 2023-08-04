"""Testing for the calc_in_given_out of the pricing models."""
from __future__ import annotations
import decimal
import logging
from typing import TYPE_CHECKING
import unittest

from elfpy.markets.hyperdrive import (
    HyperdriveMarketState,
    HyperdrivePricingModel,
    YieldspacePricingModel,
    hyperdrive_actions,
)
from elfpy.tests.pricing_models.calc_test_dataclasses import (
    CalcInGivenOutFailureTestCase,
    CalcInGivenOutSuccessByModelTestResult,
    CalcInGivenOutSuccessTestCase,
    CalcInGivenOutSuccessTestResult,
)
import elfpy.time as time
import elfpy.types as types
import elfpy.utils.logs as log_utils
from fixedpointmath import FixedPoint
from fixedpointmath import errors as fperrors

if TYPE_CHECKING:
    from elfpy.markets.base import BasePricingModel

# pylint: disable=too-many-lines


class TestCalcInGivenOut(unittest.TestCase):
    """Unit tests for the calc_in_given_out function"""

    APPROX_EQ: FixedPoint = FixedPoint(1e-8)

    # TODO: Add tests for the full TradeResult object
    def test_calc_in_given_out_success(self):
        """Success tests for calc_in_given_out"""
        log_utils.setup_logging("test_calc_in_given_out_failure")
        pricing_models: list[BasePricingModel] = [
            YieldspacePricingModel(),
            HyperdrivePricingModel(),
        ]
        success_test_cases = base_in_test_cases + pt_in_test_cases + pt_in_test_cases_hyperdrive_only
        for (
            test_number,
            (
                test_case,
                results_by_model,
            ),
        ) in enumerate(success_test_cases):
            for pricing_model in pricing_models:
                logging.info("test_number = %s with\ntest_case = %s", test_number, test_case)
                model_name = pricing_model.model_name()
                model_type = pricing_model.model_type()
                time_stretch = pricing_model.calc_time_stretch(test_case.time_stretch_apy)
                time_remaining = time.StretchedTime(
                    days=test_case.days_remaining, time_stretch=time_stretch, normalizing_constant=FixedPoint("365.0")
                )
                # TODO: convert these tests to use total supply, not the approximation
                # approximation of total supply
                test_case.market_state.lp_total_supply = (
                    test_case.market_state.bond_reserves
                    + test_case.market_state.share_price * test_case.market_state.share_reserves
                )
                expected_result = results_by_model[model_type]
                if expected_result is None:
                    continue
                # Ensure we get the expected results from the pricing model.
                trade_result = pricing_model.calc_in_given_out(
                    out=test_case.out,
                    market_state=test_case.market_state,
                    time_remaining=time_remaining,
                )
                self.assertAlmostEqual(
                    trade_result.breakdown.without_fee_or_slippage,
                    expected_result.without_fee_or_slippage,
                    delta=self.APPROX_EQ,
                    msg=f"test {test_number + 1} unexpected without_fee_or_slippage",
                )
                self.assertAlmostEqual(
                    trade_result.breakdown.without_fee,
                    expected_result.without_fee,
                    delta=self.APPROX_EQ,
                    msg=f"test {test_number + 1} unexpected without_fee",
                )
                if model_type in {"yieldspace", "hyperdrive"}:
                    self.assertAlmostEqual(
                        trade_result.breakdown.fee,
                        expected_result.fee,
                        delta=self.APPROX_EQ,
                        msg=f"test {test_number + 1} unexpected yieldspace fee",
                    )
                    self.assertAlmostEqual(
                        trade_result.breakdown.with_fee,
                        expected_result.with_fee,
                        delta=self.APPROX_EQ,
                        msg=f"test {test_number + 1} unexpected yieldspace with_fee",
                    )
                else:
                    raise AssertionError(f'Expected model_name to be or "YieldSpace", not {model_name}')
        log_utils.close_logging()

    def test_calc_in_given_out_precision(self):
        """
        This test ensures that the pricing model can handle very extreme inputs
        such as extremely small inputs with extremely large reserves.

        .. todo:: This should be multiple tests for base & pt trade type
        """
        log_utils.setup_logging("test_calc_in_given_out")
        pricing_models: list[BasePricingModel] = [
            YieldspacePricingModel(),
            HyperdrivePricingModel(),
        ]
        for pricing_model in pricing_models:
            # TODO: Works from 0 to 15, after that with[out]_fee goes 0 and then negative.
            # Need to fix after negative interest is supported (which removes lp_total_supply from in_given_out calcs)
            # Final range should be range(0, 19)
            for range_val, trade_amount in enumerate([FixedPoint(1 * 10 ** (-x)) for x in range(0, 16)]):
                logging.info(
                    "pricing_model=%s\nrange_val=%s; trade_amount=%s", pricing_model, range_val, float(trade_amount)
                )
                # out is in base, in is in bonds (TRADE TOKEN TYPE IS "BASE")
                trade_quantity = types.Quantity(amount=trade_amount, unit=types.TokenType.BASE)
                market_state = HyperdriveMarketState(
                    share_reserves=FixedPoint("10_000_000_000.0"),
                    bond_reserves=FixedPoint("1.0"),
                    share_price=FixedPoint("2.0"),
                    init_share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.1"),
                    # TODO: test with flat fees
                    flat_fee_multiple=FixedPoint("0.0"),
                )
                # TODO: convert these tests to use total supply, not the approximation
                # approximation of total supply
                market_state.lp_total_supply = (
                    market_state.bond_reserves + market_state.share_price * market_state.share_reserves
                )
                time_remaining = time.StretchedTime(
                    days=FixedPoint("365.0"),
                    time_stretch=pricing_model.calc_time_stretch(FixedPoint("0.05")),
                    normalizing_constant=FixedPoint("365.0"),
                )
                trade_result = pricing_model.calc_in_given_out(
                    out=trade_quantity,
                    market_state=market_state,
                    time_remaining=time_remaining,
                )
                self.assertGreater(trade_result.breakdown.with_fee, FixedPoint("0.0"))
                # out is in bonds, in is in base (TRADE TOKEN TYPE IS "PT")
                trade_quantity = types.Quantity(amount=trade_amount, unit=types.TokenType.PT)
                market_state = HyperdriveMarketState(
                    share_reserves=FixedPoint("1.0"),
                    bond_reserves=FixedPoint("10_000_000_000.0"),
                    share_price=FixedPoint("2.0"),
                    init_share_price=FixedPoint("1.2"),
                    curve_fee_multiple=FixedPoint("0.1"),
                    # TODO: test with flat fees
                    flat_fee_multiple=FixedPoint("0.0"),
                )
                time_remaining = time.StretchedTime(
                    days=FixedPoint("365.0"),
                    time_stretch=pricing_model.calc_time_stretch(FixedPoint("0.05")),
                    normalizing_constant=FixedPoint("365.0"),
                )
                trade_result = pricing_model.calc_in_given_out(
                    out=trade_quantity,
                    market_state=market_state,
                    time_remaining=time_remaining,
                )
                self.assertGreater(trade_result.breakdown.with_fee, FixedPoint("0.0"))
        log_utils.close_logging()

    # TODO: This should be refactored to be a test for check_input_assertions and check_output_assertions
    # issue #57
    def test_calc_in_given_out_failure(self):
        """Failure tests for calc_in_given_out"""
        log_utils.setup_logging("test_calc_in_given_out_success")
        pricing_models: list[BasePricingModel] = [
            YieldspacePricingModel(),
            HyperdrivePricingModel(),
        ]
        # Failure test cases.
        failure_test_cases = [
            CalcInGivenOutFailureTestCase(  # test 0
                # amount negative
                out=types.Quantity(amount=FixedPoint("-1.0"), unit=types.TokenType.PT),
                market_state=HyperdriveMarketState(
                    share_reserves=FixedPoint("100_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    share_price=FixedPoint("1.0"),
                    init_share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.01"),
                    flat_fee_multiple=FixedPoint("0.01"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("91.25"), time_stretch=FixedPoint("1.1"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=AssertionError,
            ),
            CalcInGivenOutFailureTestCase(  # test 1
                # amount 0
                out=types.Quantity(amount=FixedPoint("0.0"), unit=types.TokenType.PT),
                market_state=HyperdriveMarketState(
                    share_reserves=FixedPoint("100_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    share_price=FixedPoint("1.0"),
                    init_share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.01"),
                    flat_fee_multiple=FixedPoint("0.01"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("91.25"), time_stretch=FixedPoint("1.1"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=AssertionError,
            ),
            CalcInGivenOutFailureTestCase(  # test 2
                out=types.Quantity(amount=FixedPoint("100.0"), unit=types.TokenType.PT),
                market_state=HyperdriveMarketState(
                    # share reserves negative
                    share_reserves=FixedPoint(-1),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    share_price=FixedPoint("1.0"),
                    init_share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.01"),
                    flat_fee_multiple=FixedPoint("0.01"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("91.25"), time_stretch=FixedPoint("1.1"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=AssertionError,
            ),
            CalcInGivenOutFailureTestCase(  # test 3
                out=types.Quantity(amount=FixedPoint("100.0"), unit=types.TokenType.PT),
                market_state=HyperdriveMarketState(
                    share_reserves=FixedPoint("100_000.0"),
                    # bond reserves negative
                    bond_reserves=FixedPoint(-1),
                    share_price=FixedPoint("1.0"),
                    init_share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.01"),
                    flat_fee_multiple=FixedPoint("0.01"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("91.25"), time_stretch=FixedPoint("1.1"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=AssertionError,
            ),
            CalcInGivenOutFailureTestCase(  # test 4
                out=types.Quantity(amount=FixedPoint("100.0"), unit=types.TokenType.PT),
                market_state=HyperdriveMarketState(
                    share_reserves=FixedPoint("100_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    share_price=FixedPoint("1.0"),
                    init_share_price=FixedPoint("1.0"),
                    # trade fee negative
                    curve_fee_multiple=FixedPoint("-1.0"),
                    flat_fee_multiple=FixedPoint("0.01"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("91.25"), time_stretch=FixedPoint("1.1"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=AssertionError,
            ),
            CalcInGivenOutFailureTestCase(  # test 5
                out=types.Quantity(amount=FixedPoint("100.0"), unit=types.TokenType.PT),
                market_state=HyperdriveMarketState(
                    share_reserves=FixedPoint("100_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    share_price=FixedPoint("1.0"),
                    init_share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.01"),
                    # flat fee negative
                    flat_fee_multiple=FixedPoint("-1.0"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("91.25"), time_stretch=FixedPoint("1.1"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=AssertionError,
            ),
            CalcInGivenOutFailureTestCase(  # test 6
                out=types.Quantity(amount=FixedPoint("100.0"), unit=types.TokenType.PT),
                market_state=HyperdriveMarketState(
                    share_reserves=FixedPoint("100_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    share_price=FixedPoint("1.0"),
                    init_share_price=FixedPoint("1.0"),
                    # trade fee above 1
                    curve_fee_multiple=FixedPoint("1.1"),
                    flat_fee_multiple=FixedPoint("0.01"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("91.25"), time_stretch=FixedPoint("1.1"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=AssertionError,
            ),
            CalcInGivenOutFailureTestCase(  # test 7
                out=types.Quantity(amount=FixedPoint("100.0"), unit=types.TokenType.PT),
                market_state=HyperdriveMarketState(
                    share_reserves=FixedPoint("100_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    share_price=FixedPoint("1.0"),
                    init_share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.01"),
                    # flat fee above 1
                    flat_fee_multiple=FixedPoint("1.1"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("91.25"), time_stretch=FixedPoint("1.1"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=AssertionError,
            ),
            CalcInGivenOutFailureTestCase(  # test 8
                out=types.Quantity(amount=FixedPoint("100.0"), unit=types.TokenType.PT),
                market_state=HyperdriveMarketState(
                    share_reserves=FixedPoint("100_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    share_price=FixedPoint("1.0"),
                    init_share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("1.1"),
                    flat_fee_multiple=FixedPoint("0.01"),
                ),
                # days remaining negative
                time_remaining=time.StretchedTime(
                    days=FixedPoint("-91.25"), time_stretch=FixedPoint("1.1"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=AssertionError,
            ),
            CalcInGivenOutFailureTestCase(  # test 9
                out=types.Quantity(amount=FixedPoint("100.0"), unit=types.TokenType.PT),
                market_state=HyperdriveMarketState(
                    share_reserves=FixedPoint("100_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    share_price=FixedPoint("1.0"),
                    init_share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.1"),
                    flat_fee_multiple=FixedPoint("0.01"),
                ),
                # days remaining == 365, will get divide by zero error
                time_remaining=time.StretchedTime(
                    days=FixedPoint("365.0"), time_stretch=FixedPoint("1.0"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=(fperrors.DivisionByZero),
            ),
            CalcInGivenOutFailureTestCase(  # test 10
                out=types.Quantity(amount=FixedPoint("100.0"), unit=types.TokenType.PT),
                market_state=HyperdriveMarketState(
                    share_reserves=FixedPoint("100_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    share_price=FixedPoint("1.0"),
                    init_share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.1"),
                    flat_fee_multiple=FixedPoint("0.01"),
                ),
                # days remaining > 365
                time_remaining=time.StretchedTime(
                    days=FixedPoint("500.0"), time_stretch=FixedPoint("1.1"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=AssertionError,
            ),
            CalcInGivenOutFailureTestCase(  # test 11
                # amount very high, can't make trade
                out=types.Quantity(amount=FixedPoint("10_000_000.0"), unit=types.TokenType.BASE),
                market_state=HyperdriveMarketState(
                    share_reserves=FixedPoint("100_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    share_price=FixedPoint("1.0"),
                    init_share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.1"),
                    flat_fee_multiple=FixedPoint("0.01"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("92.5"), time_stretch=FixedPoint("1.1"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=(ValueError, decimal.InvalidOperation),
            ),
            CalcInGivenOutFailureTestCase(  # test 12
                out=types.Quantity(amount=FixedPoint("100.0"), unit=types.TokenType.BASE),
                market_state=HyperdriveMarketState(
                    share_reserves=FixedPoint("100_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    share_price=FixedPoint("2.0"),
                    # init_share_price 0
                    init_share_price=FixedPoint("0.0"),
                    curve_fee_multiple=FixedPoint("0.1"),
                    flat_fee_multiple=FixedPoint("0.01"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("91.25"), time_stretch=FixedPoint("1.1"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=AssertionError,
            ),
            CalcInGivenOutFailureTestCase(  # test 13
                # amount < 1 wei
                out=types.Quantity(amount=FixedPoint(0.999e-18), unit=types.TokenType.PT),
                market_state=HyperdriveMarketState(
                    share_reserves=FixedPoint("100_000.0"),
                    bond_reserves=FixedPoint("1_000_000.0"),
                    share_price=FixedPoint("1.0"),
                    init_share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.01"),
                    flat_fee_multiple=FixedPoint("0.01"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("91.25"), time_stretch=FixedPoint("1.1"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=AssertionError,
            ),
            CalcInGivenOutFailureTestCase(  # test 14
                out=types.Quantity(amount=FixedPoint("100.0"), unit=types.TokenType.PT),
                market_state=HyperdriveMarketState(
                    # reserves waaaay unbalanced
                    share_reserves=FixedPoint("30_000_000_000.0"),
                    bond_reserves=FixedPoint("1.0"),
                    share_price=FixedPoint("1.0"),
                    init_share_price=FixedPoint("1.0"),
                    curve_fee_multiple=FixedPoint("0.01"),
                    flat_fee_multiple=FixedPoint("0.01"),
                ),
                time_remaining=time.StretchedTime(
                    days=FixedPoint("91.25"), time_stretch=FixedPoint("1.1"), normalizing_constant=FixedPoint("365.0")
                ),
                exception_type=AssertionError,
            ),
        ]
        # Verify that the pricing model raises the expected exception type for
        # each test case.
        for test_number, test_case in enumerate(failure_test_cases):
            logging.info("test_number=%s\ntest_case=%s", test_number, test_case)
            for pricing_model in pricing_models:
                # TODO: convert these tests to use total supply, not the approximation
                # approximation of total supply
                logging.info("pricing_model_name=%s", pricing_model.model_name())
                test_case.market_state.lp_total_supply = (
                    test_case.market_state.bond_reserves
                    + test_case.market_state.share_price * test_case.market_state.share_reserves
                )
                with self.assertRaises(test_case.exception_type):
                    pricing_model.check_input_assertions(
                        quantity=test_case.out,
                        market_state=test_case.market_state,
                        time_remaining=test_case.time_remaining,
                    )
                    trade_result = pricing_model.calc_in_given_out(
                        out=test_case.out,
                        market_state=test_case.market_state,
                        time_remaining=test_case.time_remaining,
                    )
                    hyperdrive_actions.check_output_assertions(
                        trade_result=trade_result,
                    )
        log_utils.close_logging()


# Test cases where token_in = TokenType.BASE indicating that bonds are being
# purchased for base.
#
# 1. in_ = 100; 10% fee; 100k share reserves; 100k bond reserves;
#    1 share price; 1 init share price; t_stretch targeting 5% APY;
#    6 mo remaining
# 2. in_ = 100; 20% fee; 100k share reserves; 100k bond reserves;
#    1 share price; 1 init share price; t_stretch targeting 5% APY;
#    6 mo remaining
# 3. in_ = 10k; 10% fee; 100k share reserves; 100k bond reserves;
#    1 share price; 1 init share price; t_stretch targeting 5% APY;
#    6 mo remaining
# 4. in_ = 80k; 10% fee; 100k share reserves; 100k bond reserves;
#    1 share price; 1 init share price; t_stretch targeting 5% APY;
#    6 mo remaining
# 5. in_ = 200; 10% fee; 100k share reserves; 100k bond reserves;
#    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
#    6 mo remaining
# 6. in_ = 200; 10% fee; 100k share reserves; 1M bond reserves;
#    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
#    6 mo remaining
# 7. in_ = 200; 10% fee; 100k share reserves; 1M bond reserves;
#    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
#    3 mo remaining
# 8. in_ = 200; 10% fee; 100k share reserves; 1M bond reserves;
#    2 share price; 1.5 init share price; t_stretch targeting 10% APY;
#    3 mo remaining
base_in_test_cases = [
    (  ## test one, basic starting point
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("100.0"), unit=types.TokenType.PT
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("100_000.0"),  # PT reserves
                share_price=FixedPoint("1.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.0"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.1"),  # fee multiple applied to price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),
            ),
            days_remaining=FixedPoint("182.5"),  # 6 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 22.1868770168519182502689135891
        # tau = 0.0225358440315970471499308329778
        # 1 - tau = 0.977464155968402952850069167022
        # k = c/mu*(mu*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
        #   = 302929.51067963685
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu*z))**t
                #   = 1.0250671833648672
                # without_fee_or_slippage = 1/p * out = 97.55458141947516
                without_fee_or_slippage=FixedPoint("97.55458141947516"),
                # d_z' = 1/mu * (mu/c*(k - (2*y + c*z - d_y)**(1 - tau)))**(1/(1 - tau)) - z
                # d_z' = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 100)
                #        **(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                #      = 97.55601990513969
                without_fee=FixedPoint("97.55601990513969"),
                # fee is 10% of discount before slippage = (100-97.55458141947516)*0.1 = 0.24454185805248443
                fee=FixedPoint("0.24454185805248443"),
                # with_fee = d_z' + fee = 97.55601990513969 + 0.24454185805248443 = 97.80056176319217
                with_fee=FixedPoint("97.80056176319218"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("97.58591137152354"),
                without_fee=FixedPoint("97.5866001243412"),
                fee=FixedPoint("0.24140886284764632"),
                with_fee=FixedPoint("97.82800898718885"),
            ),
        ),
    ),  # end of test one
    (  ## test two, double the fee
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("100.0"), unit=types.TokenType.PT
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("100_000.0"),  # PT reserves
                share_price=FixedPoint("1.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.0"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.2"),  # fee multiple applied to the price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("182.5"),  # 6 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 22.1868770168519182502689135891
        # tau = 0.0225358440315970471499308329778
        # 1 - tau = 0.977464155968402952850069167022
        # k = c/mu*(u*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
        #   = 302929.51067963685
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu * z))**tau
                #   = 1.0250671833648672
                # without_fee_or_slippage = 1/p * out = 97.55458141947516
                without_fee_or_slippage=FixedPoint("97.55458141947516"),
                # d_z' = 1/u * (u/c*(k - (2*y + c*z - d_y)**(1 - tau)))**(1/(1 - tau)) - z
                # d_z' = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 100)
                #        **(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                #      = 97.55601990513969
                without_fee=FixedPoint("97.55601990513969"),
                # fee is 20% of discount before slippage = (100-97.55458141947516)*0.2 = 0.48908371610496887
                fee=FixedPoint("0.48908371610496887"),
                # with_fee = d_z' + fee = 97.55601990513969 + 0.4887960189720616 = 98.04481592411175
                with_fee=FixedPoint("98.04510362124466"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("97.58591137152354"),
                without_fee=FixedPoint("97.5866001243412"),
                fee=FixedPoint("0.48281772569529263"),
                with_fee=FixedPoint("98.0694178500365"),
            ),
        ),
    ),  # end of test two
    (  ## test three, 10k out
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("10_000.0"), unit=types.TokenType.PT
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("100_000.0"),  # PT reserves
                share_price=FixedPoint("1.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.0"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.1"),  # fee multiple applied to price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("182.5"),  # 6 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 22.1868770168519182502689135891
        # tau = 0.0225358440315970471499308329778
        # 1 - tau = 0.977464155968402952850069167022
        # k = c/mu*(mu*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
        #   = 302929.51067963685
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu * z))**tau
                #   = 1.0250671833648672
                # without_fee_or_slippage = 1/p * out = 97.55458141947516
                without_fee_or_slippage=FixedPoint("9755.458141947514"),
                # d_z' = 1/mu * (mu/c*(k - (2*y + c*z - d_y)**(1 - tau)))**(1/(1 - tau)) - z
                # d_z' = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 10000)
                #        **(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000
                #      = 9769.577831379836
                without_fee=FixedPoint("9769.577831379836"),
                # fee is 10% of discount before slippage = (10000-9755.458141947514)*0.1 = 24.454185805248564
                fee=FixedPoint("24.454185805248564"),
                # with_fee = d_z' + fee = 9769.577831379836 +  24.454185805248564 = 97.80056176319217
                with_fee=FixedPoint("9794.032017185085"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("9772.537730069402"),
                without_fee=FixedPoint("9779.197793075873"),
                fee=FixedPoint("22.746226993059782"),
                with_fee=FixedPoint("9801.944020068933"),
            ),
        ),
    ),  # end of test three
    (  ## test four, 80k out
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("80_000.0"), unit=types.TokenType.PT
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("100_000.0"),  # PT reserves
                share_price=FixedPoint("1.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.0"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.1"),  # fee multiple applied to price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("182.5"),  # 6 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 22.1868770168519182502689135891
        # tau = 0.0225358440315970471499308329778
        # 1 - tau = 0.977464155968402952850069167022
        # k = c/mu*(u*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
        #   = 302929.51067963685
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu * z))**tau
                #   = 1.0250671833648672
                # without_fee_or_slippage = 1/p * out = 97.55458141947516
                without_fee_or_slippage=FixedPoint("78043.66513558012"),
                # d_z' = 1/mu * (u/c*(k - (2*y + c*z - d_y)**(1 - tau)))**(1/(1 - tau)) - z
                # d_z' = 1/1 * (1/1*(302929.51067963685 - (2*100000 + 100000 - 80000)
                #        **(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778))
                #        - 100000
                #       = 78866.87433323538
                without_fee=FixedPoint("78866.87433323538"),
                # fee is 10% of discount before slippage = (80000-78043.66513558012)*0.1 = 195.6334864419885
                fee=FixedPoint("195.6334864419885"),
                # with_fee = d_z' + fee = 78866.87433323538 +  195.6334864419885 = 79062.50781967737
                with_fee=FixedPoint("79062.50781967737"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("78899.37999298729"),
                without_fee=FixedPoint("79269.0508947279"),
                fee=FixedPoint("110.06200070127115"),
                with_fee=FixedPoint("79379.11289542918"),
            ),
        ),
    ),  # end of test four
    (  ## test five, change share price
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("200.0"), unit=types.TokenType.PT
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("100_000.0"),  # PT reserves
                share_price=FixedPoint("2.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.5"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.1"),  # fee multiple applied to price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("182.5"),  # 6 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 22.1868770168519182502689135891
        # tau = 0.0225358440315970471499308329778
        # 1 - tau = 0.977464155968402952850069167022
        # k = c/mu*(u*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 2/1.5*((1.5*100000)**0.9774641559684029528500691670222) + (2*100000 + 2*100000)
        #     **0.9774641559684029528500691670222
        #   = 451988.7122137336
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu*z))**tau
                #   = ((2*100000 + 2*100000)/(1.5*100000))**0.0225358440315970471499308329778
                #   = 1.0223499142867662
                # without_fee_or_slippage = 1/p * out = 195.627736849304
                without_fee_or_slippage=FixedPoint("195.627736849304"),
                # d_z = 1/mu * (mu/c*(k - (2*y + c*z - d_y)**(1 - tau)))**(1/(1 - tau)) - z
                # d_z = 2*(1/1.5 * (1.5/2*(451988.7122137336 - (2*100000 + 2*100000 - 200)
                #       **(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000)
                #     = 195.63099467812572
                without_fee=FixedPoint("195.63099467812572"),
                # fee is 10% of discount before slippage = (200-195.627736849304)*0.1 = 0.4372263150696
                fee=FixedPoint("0.4372263150696"),
                # with_fee = without_fee + fee = 195.63099467812572 + 0.4372263150696 = 196.06822099319533
                with_fee=FixedPoint("196.06822099319533"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("195.6787624057141"),
                without_fee=FixedPoint("195.68033249810105"),
                fee=FixedPoint("0.4321237594285876"),
                with_fee=FixedPoint("196.11245625752963"),
            ),
        ),
    ),  # end of test five
    (  ## test six, up bond reserves to 1,000,000
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("200.0"), unit=types.TokenType.PT
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("1_000_000.0"),  # PT reserves
                share_price=FixedPoint("2.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.5"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.1"),  # fee multiple applied to price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("182.5"),  # 6 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 22.1868770168519182502689135891
        # tau = 0.0225358440315970471499308329778
        # 1 - tau = 0.977464155968402952850069167022
        # k = c/mu*(u*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 2/1.5*((1.5*100000)**0.9774641559684029528500691670222) + (2*1000000 + 2*100000)
        #     **0.9774641559684029528500691670222
        #   = 1735927.3223407117
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu*z))**tau
                #   = ((2*1000000 + 2*100000)/(1.5*100000))**0.0225358440315970471499308329778
                #   = 1.062390706640675
                # without_fee_or_slippage = 1/p * out = 188.25465880853625
                without_fee_or_slippage=FixedPoint("188.25465880853625"),
                # d_z' = 1/mu * (mu/c*(k - (2*y + c*z - d_y)**(1 - tau)))**(1/(1 - tau)) - z
                # d_z' = 2*(1/1.5 * (1.5/2*(1735927.3223407117 - (2*1000000 + 2*100000 - 200)
                #        **(1-0.0225358440315970471499308329778)))**(1/(1-0.0225358440315970471499308329778)) - 100000)
                #      = 188.2568477257446
                without_fee=FixedPoint("188.2568477257446"),
                # fee is 10% of discount before slippage = (200-188.25465880853625)*0.1 = 1.1745341191463752
                fee=FixedPoint("1.1745341191463752"),
                # with_fee = d_z' + fee = 188.2568477257446 +  1.1745341191463752 = 189.43138184489098
                with_fee=FixedPoint("189.43138184489098"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("188.60171912017125"),
                without_fee=FixedPoint("188.60269388841698"),
                fee=FixedPoint("1.1398280879828715"),
                with_fee=FixedPoint("189.74252197639984"),
            ),
        ),
    ),  # end of test six
    (  ## test seven, halve the days remaining
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("200.0"), unit=types.TokenType.PT
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("1_000_000.0"),  # PT reserves
                share_price=FixedPoint("2.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.5"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.1"),  # fee multiple applied to price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("91.25"),  # 3 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 22.1868770168519182502689135891
        # tau = 91.25/365/22.1868770168519182502689135891 = 0.011267922015798524
        # 1 - tau = 0.9887320779842015
        # k = c/mu*(mu*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 2/1.5*((1.5*100000)**0.9887320779842015) + (2*1000000 + 2*100000)**0.9887320779842015
        #   = 2041060.1949973335
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu*z))**tau
                #   = ((2*1000000 + 2*100000)/(1.5*100000))**0.011267922015798524
                #   = 1.0307233899745727
                # without_fee_or_slippage = 1/p * out = 194.038480105641
                without_fee_or_slippage=FixedPoint("194.038480105641"),
                # d_z' = 1/mu * (mu/c*(k - (2*y + c*z - d_y)**(1 - tau)))**(1/(1 - tau)) - z
                # d_z' = 2*(1/1.5 * (1.5/2*(2041060.1949973335 - (2*1000000 + 2*100000 - 200)
                #        **(1-0.011267922015798524)))**(1/(1-0.011267922015798524)) - 100000)
                #      = 194.0396397759323
                without_fee=FixedPoint("194.0396397759323"),
                # fee is 10% of discount before slippage = (200-194.038480105641)*0.1 = 0.5961519894358986
                fee=FixedPoint("0.5961519894358986"),
                # with_fee = d_z' + fee = 194.0396397759323 + 0.5961519894358986 = 194.6357917653682
                with_fee=FixedPoint("194.6357917653682"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("194.30140381272443"),
                without_fee=FixedPoint("194.30164747033268"),
                fee=FixedPoint("0.5698596187275567"),
                with_fee=FixedPoint("194.87150708906023"),
            ),
        ),
    ),  # end of test seven
    (  ## test eight, halve the APY
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("200.0"), unit=types.TokenType.PT
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("1_000_000.0"),  # PT reserves
                share_price=FixedPoint("2.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.5"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.1"),  # fee multiple applied to price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("91.25"),  # 3 months remaining
            time_stretch_apy=FixedPoint("0.025"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 3.09396 / 0.02789 / 2.5 = 44.37375403370383
        # tau = 91.25/365/44.37375403370383 = 0.005633961007899263
        # 1 - tau = 0.9943660389921007
        # k = c/mu*(mu*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 2/1.5*((1.5*100000)**0.9943660389921007) + (2*1000000 + 2*100000)**0.9943660389921007
        #   = 2213245.968723062
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu*z)**tau
                #   = ((2*1000000 + 2*100000)/(1.5*100000))**0.005633961007899263
                #   = 1.015245482617171
                # without_fee_or_slippage = 1/p * out = 196.99669038115388
                without_fee_or_slippage=FixedPoint("196.99669038115388"),
                # d_z' = 1/mu * (mu/c*(k - (2*y + c*z - d_y)**(1 - tau)))**(1/(1 - tau)) - z
                # d_z' = 2*(1/1.5 * (1.5/2*(2213245.968723062 - (2*1000000 + 2*100000 - 200)
                #        **(1-0.005633961007899263)))**(1/(1-0.005633961007899263)) - 100000)
                #      = 196.9972872567596
                without_fee=FixedPoint("196.9972872567596"),
                # fee is 10% of discount before slippage = (200-196.99669038115388)*0.1 = 0.3003309618846117
                fee=FixedPoint("0.3003309618846117"),
                # with_fee = d_z' + fee = 196.9972872567596 + 0.3003309618846117 = 197.2976182186442
                with_fee=FixedPoint("197.2976182186442"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("197.0645321939592"),
                without_fee=FixedPoint("197.06466894078767"),
                fee=FixedPoint("0.2935467806040798"),
                with_fee=FixedPoint("197.35821572139176"),
            ),
        ),
    ),  # end of test eight
]
pt_in_test_cases = [
    (  ## test one, basic starting point
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("100.0"), unit=types.TokenType.BASE
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("100_000.0"),  # PT reserves
                share_price=FixedPoint("1.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.0"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.1"),  # fee multiple applied to price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("182.5"),  # 6 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 22.1868770168519182502689135891
        # tau = 0.0225358440315970471499308329778
        # 1 - tau = 0.977464155968402952850069167022
        # k = c/mu*(mu*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
        #   = 302929.51067963685
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu * z))**tau
                #   = 1.0250671833648672
                # without_fee_or_slippage = p * out = 102.50671833648673
                without_fee_or_slippage=FixedPoint("102.50671833648673"),
                # d_y' = (k - c/mu*(mu*z - mu*d_z)**(1 - tau))**(1/(1 - tau)) - y
                #         = (302929.51067963685 - 1/1*(1*100000 - 1*100)**0.977464155968402952850069167022)
                #           **(1/0.977464155968402952850069167022) - (2*100_000 + 1*100_000)
                #         = 102.50826839753427
                without_fee=FixedPoint("102.50826839753427"),
                # fee is 10% of discount before slippage = (102.50671833648673-100)*0.1 = 0.2506718336486728
                fee=FixedPoint("0.2506718336486728"),
                # with_fee = d_y' + fee = 102.50826839753427 + 0.2506718336486728 = 102.75894023118293
                with_fee=FixedPoint("102.75894023118293"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("102.53971546251678"),
                without_fee=FixedPoint("102.54051519598579"),
                fee=FixedPoint("0.25397154625167895"),
                with_fee=FixedPoint("102.79448674223747"),
            ),
        ),
    ),  # end of test one
    (  ## test two, double the fee
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("100.0"), unit=types.TokenType.BASE
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("100_000.0"),  # PT reserves
                share_price=FixedPoint("1.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.0"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.2"),  # fee multiple applied to the price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("182.5"),  # 6 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 22.1868770168519182502689135891
        # tau = 0.0225358440315970471499308329778
        # 1 - tau = 0.977464155968402952850069167022
        # k = c/mu*(mu*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
        #   = 302929.51067963685
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu * z))**tau
                #   = 1.0250671833648672
                # without_fee_or_slippage = p * out = 102.50671833648673
                without_fee_or_slippage=FixedPoint("102.50671833648673"),
                # d_y' = (k - c/mu*(mu*z - mu*d_z)**(1 - tau))**(1/(1 - tau)) - y
                #         = (302929.51067963685 - 1/1*(1*100000 - 1*100)**0.977464155968402952850069167022)
                #           **(1/0.977464155968402952850069167022) - (2*100_000 + 1*100_000)
                #         = 102.50826839753427
                without_fee=FixedPoint("102.50826839753427"),
                # fee is 20% of discount before slippage = (102.50671833648673-100)*0.2 = 0.5013436672973456
                fee=FixedPoint("0.5013436672973456"),
                # with_fee = d_y' + fee = 102.50826839753427 + 0.5013436672973456 = 103.00961206483161
                with_fee=FixedPoint("103.00961206483161"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("102.53971546251678"),
                without_fee=FixedPoint("102.54051519598579"),
                fee=FixedPoint("0.5079430925033579"),
                with_fee=FixedPoint("103.04845828848914"),
            ),
        ),
    ),  # end of test two
    (  ## test three, 10k out
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("10_000.0"), unit=types.TokenType.BASE
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("100_000.0"),  # PT reserves
                share_price=FixedPoint("1.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.0"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.1"),  # fee multiple applied to price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("182.5"),  # 6 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 22.1868770168519182502689135891
        # tau = 0.0225358440315970471499308329778
        # 1 - tau = 0.977464155968402952850069167022
        # k = c/mu*(mu*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
        #   = 302929.51067963685
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu * z))**tau
                #   = 1.0250671833648672
                # without_fee_or_slippage = p * out = 10250.671833648673
                without_fee_or_slippage=FixedPoint("10250.671833648673"),
                # d_y' = (k - c/mu*(mu*z - mu*d_z)**(1 - tau))**(1/(1 - tau)) - y
                #         = (302929.51067963685 - 1/1*(1*100000 - 1*10000)**0.977464155968402952850069167022)
                #            **(1/0.977464155968402952850069167022) - (2*100_000 + 1*100_000)
                #         = 10266.550575620378
                without_fee=FixedPoint("10266.550575620378"),
                # fee is 10% of discount before slippage = (10250.671833648673-10000)*0.1 = 25.06718336486738
                fee=FixedPoint("25.06718336486738"),
                # with_fee = d_y' + fee = 10266.550575620378 + 25.06718336486738 = 10291.617758985245
                with_fee=FixedPoint("10291.617758985245"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("10269.89849637121"),
                without_fee=FixedPoint("10278.313158090226"),
                fee=FixedPoint("26.989849637120926"),
                with_fee=FixedPoint("10305.303007727347"),
            ),
        ),
    ),  # end of test three
    (  ## test four, 80k out
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("80_000.0"), unit=types.TokenType.BASE
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("100_000.0"),  # PT reserves
                share_price=FixedPoint("1.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.0"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.1"),  # fee multiple applied to price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("182.5"),  # 6 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 22.1868770168519182502689135891
        # tau = 0.0225358440315970471499308329778
        # 1 - tau = 0.977464155968402952850069167022
        # k = c/mu*(mu*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 100000**0.9774641559684029528500691670222 + (2*100000 + 100000*1)**0.9774641559684029528500691670222
        #   = 302929.51067963685
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu * z))**tau
                #   = 1.0250671833648672
                # without_fee_or_slippage = p * out = 82005.37466918938
                without_fee_or_slippage=FixedPoint("82005.37466918938"),
                # d_y' = (k - c/mu*(u*z - mu*d_z)**(1 - tau))**(1/(1 - tau)) - y
                #         = (302929.51067963685 - 1/1*(1*100000 - 1*80000)**0.977464155968402952850069167022)
                #           **(1/0.977464155968402952850069167022) - (2*100_000 + 1*100_000)
                #         = 83360.61360923108
                without_fee=FixedPoint("83360.61360923108"),
                # fee is 10% of discount before slippage = (82005.37466918938-80000)*0.1 = 200.53746691893758
                fee=FixedPoint("200.53746691893758"),
                # with_fee = d_y' + fee = 83360.61360923108 + 200.53746691893758 = 83561.15107615001
                with_fee=FixedPoint("83561.15107615001"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("83252.75158412871"),
                without_fee=FixedPoint("84268.97713182"),
                fee=FixedPoint("325.2751584128717"),
                with_fee=FixedPoint("84594.25229023286"),
            ),
        ),
    ),  # end of test four
    (  ## test five, change share price
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("200.0"), unit=types.TokenType.BASE
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("100_000.0"),  # PT reserves
                share_price=FixedPoint("2.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.5"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.1"),  # fee multiple applied to price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("182.5"),  # 6 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 22.1868770168519182502689135891
        # tau = 0.0225358440315970471499308329778
        # 1 - tau = 0.977464155968402952850069167022
        # k = c/mu*(mu*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 2/1.5*(1.5*100000)**0.9774641559684029528500691670222 + (2*100000 + 2*100000)
        #     **0.9774641559684029528500691670222
        #   = 451988.7122137336
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu*z))**tau
                #   = ((2*100000 + 2*100000)/(1.5*100000))**0.0225358440315970471499308329778
                #   = 1.0223499142867662
                # without_fee_or_slippage = p * out = 204.46998285735324
                without_fee_or_slippage=FixedPoint("204.46998285735324"),
                # d_y' = (k - c/mu*(mu*z - mu*d_z)**(1 - tau))**(1/(1 - tau)) - y
                #         = (451988.7122137336 - 2/1.5*(1.5*100000 - 1.5*100)**0.977464155968402952850069167022)
                #           **(1/0.977464155968402952850069167022) - (2*100_000 + 2*100_000)
                #         = 204.4734651519102
                without_fee=FixedPoint("204.4734651519102"),
                # fee is 10% of discount before slippage = (204.46998285735324-200)*0.1 = 0.44699828573532446
                fee=FixedPoint("0.44699828573532446"),
                # with_fee = d_z' + fee = 204.4734651519102 + 0.44699828573532446 = 204.92046343764554
                with_fee=FixedPoint("204.92046343764554"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("204.52346839323616"),
                without_fee=FixedPoint("204.52526228054194"),
                fee=FixedPoint("0.45234683932361636"),
                with_fee=FixedPoint("204.97760911986555"),
            ),
        ),
    ),  # end of test five
    (  ## test six, up bond reserves to 1,000,000
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("200.0"), unit=types.TokenType.BASE
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("1_000_000.0"),  # PT reserves
                share_price=FixedPoint("2.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.5"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.1"),  # fee multiple applied to price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("182.5"),  # 6 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 22.1868770168519182502689135891
        # tau = 0.0225358440315970471499308329778
        # 1 - tau = 0.977464155968402952850069167022
        # k = c/mu*(mu*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 2/1.5*(1.5*100000)**0.9774641559684029528500691670222
        #     + (2*1000000 + 2*100000)**0.9774641559684029528500691670222
        #   = 1735927.3223407117
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu * z))**tau
                #   = ((2*1000000 + 2*100000)/(1.5*100000))**0.0225358440315970471499308329778
                #   = 1.062390706640675
                # without_fee_or_slippage = p * out = 212.478141328135
                without_fee_or_slippage=FixedPoint("212.478141328135"),
                # d_y' = (k - c/mu*(mu*z - mu*d_z)**(1 - tau))**(1/(1 - tau)) - y
                #         = (1735927.3223407117 - 2/1.5*(1.5*100000 - 1.5*100)**0.977464155968402952850069167022)
                #           **(1/0.977464155968402952850069167022)
                #           - (2*100_0000 + 2*100_000)
                #         = 212.48076756019145
                without_fee=FixedPoint("212.48076756019145"),
                # fee is 10% of discount before slippage = (212.478141328135-200)*0.1 = 1.2478141328134997
                fee=FixedPoint("1.2478141328134997"),
                # with_fee = d_z' + fee = 212.48076756019145 + 1.2478141328134997 = 213.72858169300494
                with_fee=FixedPoint("213.72858169300494"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("212.87017681569534"),
                without_fee=FixedPoint("212.87157998187467"),
                fee=FixedPoint("1.2870176815695311"),
                with_fee=FixedPoint("214.1585976634442"),
            ),
        ),
    ),  # end of test six
    (  ## test seven, halve the days remaining
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("200.0"), unit=types.TokenType.BASE
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("1_000_000.0"),  # PT reserves
                share_price=FixedPoint("2.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.5"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.1"),  # fee multiple applied to price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("91.25"),  # 3 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 22.1868770168519182502689135891
        # tau = 91.25/365/22.1868770168519182502689135891 = 0.011267922015798524
        # 1 - tau = 0.9887320779842015
        # k = c/mu*(mu*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 2/1.5*(1.5*100000)**0.9887320779842015 + (2*1000000 + 2*100000)**0.9887320779842015
        #   = 2041060.1949973335
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu * z))**tau
                #   = ((2*1000000 + 2*100000)/(1.5*100000))**0.011267922015798524
                #   = 1.0307233899745727
                # without_fee_or_slippage = p * out = 202.22264109508274
                without_fee_or_slippage=FixedPoint("206.14467799491453"),
                # d_y' = (k - c/mu*(mu*z - mu*d_z)**(1 - tau))**(1/(1 - tau)) - y
                #         = (2041060.1949973335 - 2/1.5*(1.5*100000 - 1.5*100)**0.9887320779842015)
                #           **(1/0.9887320779842015)
                #           - (2*100_0000 + 2*100_000)
                #         = 206.1459486191161
                without_fee=FixedPoint("206.1459486191161"),
                # fee is 10% of discount before slippage = (206.14467799491453-200)*0.1 = 0.6144677994914531
                fee=FixedPoint("0.6144677994914531"),
                # with_fee = d_z' + fee = 206.1459486191161 + 0.6144677994914531 = 206.76041641860755
                with_fee=FixedPoint("206.76041641860755"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("206.4357825223524"),
                without_fee=FixedPoint("206.43613336980343"),
                fee=FixedPoint("0.6435782522352407"),
                with_fee=FixedPoint("207.07971162203867"),
            ),
        ),
    ),  # end of test seven
    (  ## test eight, halve the APY
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("200.0"), unit=types.TokenType.BASE
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("100_000.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("1_000_000.0"),  # PT reserves
                share_price=FixedPoint("2.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.5"),  # original share price pool started
                curve_fee_multiple=FixedPoint("0.1"),  # fee multiple applied to price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.0"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("91.25"),  # 3 months remaining
            time_stretch_apy=FixedPoint("0.025"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        # t_stretch = 3.09396 / 0.02789 / 2.5 = 44.37375403370383
        # tau = 91.25/365/44.37375403370383 = 0.005633961007899263
        # 1 - tau = 0.9943660389921007
        # k = c/mu*(mu*z)**(1 - tau) + (2*y + c*z)**(1 - tau)
        #   = 2/1.5*(1.5*100000)**0.9943660389921007 + (2*1000000 + 2*100000)**0.9943660389921007
        #   = 2213245.968723062
        CalcInGivenOutSuccessByModelTestResult(
            yieldspace=CalcInGivenOutSuccessTestResult(
                # p = ((2y+cz)/(mu*z))**tau
                #   = ((2*1000000 + 2*100000)/(1.5*100000))**0.005633961007899263
                #   = 1.015245482617171
                # without_fee_or_slippage = p * out = 203.0490965234342
                without_fee_or_slippage=FixedPoint("203.0490965234342"),
                # d_y' = (k - c/mu*(mu*z - mu*d_z)**(1 - tau))**(1/(1 - tau)) - y
                #         = (2213245.968723062 - 2/1.5*(1.5*100000 - 1.5*100)**0.9943660389921007)
                #           **(1/0.9943660389921007) - (2*100_0000 + 2*100_000)
                #         = 203.04972148826346
                without_fee=FixedPoint("203.04972148826346"),
                # fee is 10% of discount before slippage = (203.0490965234342-200)*0.1 = 0.30490965234342016
                fee=FixedPoint("0.30490965234342016"),
                # with_fee = d_z' + fee = 203.04972148826346 + 0.30490965234342016 = 203.35463114060687
                with_fee=FixedPoint("203.35463114060687"),
            ),
            hyperdrive=CalcInGivenOutSuccessTestResult(
                without_fee_or_slippage=FixedPoint("203.12051511532638"),
                without_fee=FixedPoint("203.12067932868376"),
                fee=FixedPoint("0.31205151153263944"),
                with_fee=FixedPoint("203.4327308402164"),
            ),
        ),
    ),  # end of test eight
]
pt_in_test_cases_hyperdrive_only = [
    (  # test nine, share reserves zero
        CalcInGivenOutSuccessTestCase(
            out=types.Quantity(
                amount=FixedPoint("100.0"), unit=types.TokenType.PT
            ),  # how many tokens you expect to get
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint("0.0"),  # base reserves (in share terms) base = share * share_price
                bond_reserves=FixedPoint("1_000_000.0"),  # PT reserves
                share_price=FixedPoint("1.0"),  # share price of the LP in the yield source
                init_share_price=FixedPoint("1.0"),  # original share price pool started
                curve_fee_multiple=FixedPoint(
                    "0.01"
                ),  # fee multiple applied to the price slippage (1-p) (normally 10%)
                flat_fee_multiple=FixedPoint("0.00"),  # fee multiple applied to the matured portion (normally 10%)
            ),
            days_remaining=FixedPoint("182.5"),  # 6 months remaining
            time_stretch_apy=FixedPoint("0.05"),  # APY of 5% used to calculate time_stretch
        ),
        # From the input, we have the following values:
        #
        #   in hyperdrive, half the position has matured, recycled into the market
        #   z = 50
        #   y = 999_950
        #
        #   t_stretch = 3.09396 / (0.02789 * apr_percent)
        #             = 3.09396 / (0.02789 * 0.05 * 100)
        #             = 22.1868770168519182502689135891
        #
        #   tau = 365 / (365 * t_stretch) * always use FULL TAU for hyperdrive
        #     = 1 / 22.1868770168519182502689135891
        #     = 0.045071688063194094
        #
        #   1 - tau = 0.9549283119368059
        #
        #   k = (c / mu) * (mu * z) **(1 - tau) + (2 * y + c * z)**(1 - tau)
        #     = (1 / 1) * (1 * 0) ** 0.9549283119368059 +
        #           (2 * 1_000_000 + 1 * 0) ** 0.9549283119368059
        #     = 1_039_996.6424696837
        #
        #   p = ((2 * y + c * z) / (mu * z)) ** -tau
        #     = ((2 * 999_950 + 1 * 50) / (1 * 50)) ** -0.045071688063194094
        #     = 0.6202658587589548
        CalcInGivenOutSuccessByModelTestResult(
            hyperdrive=CalcInGivenOutSuccessTestResult(
                # without_fee_or_slippage = p * delta_y * t + delta_y * (1 - t)
                # without_fee_or_slippage = 0.6202658587589548 * 100 * 0.5 + 100 * 0.5
                # without_fee_or_slippage = 31.01329293794774 + 50
                # without_fee_or_slippage = 81.01329293794774
                without_fee_or_slippage=FixedPoint("81.01329293794774"),
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.6202658587589547
                # in_base=81.38288223597203
                # in_pt=134.41541713429615
                without_fee=FixedPoint("81.38288223597203"),
                fee=FixedPoint("0.18986707062052266"),
                with_fee=FixedPoint("81.57274930659256"),
            ),
        ),
    ),  # end of test nine
]

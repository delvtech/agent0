"""
Testing for the calc_in_given_out of the pricing models.
"""

# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init
# pylint: disable=duplicate-code

from dataclasses import dataclass
import unittest
import numpy as np
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel

from elfpy.types import MarketState, Quantity, StretchedTime, TokenType
from elfpy.pricing_models.base import PricingModel
from elfpy.pricing_models.yieldspace import YieldSpacePricingModel


@dataclass
class TestCaseCalcInGivenOutSuccess:
    """Dataclass for calc_in_given_out test cases"""

    out: Quantity
    market_state: MarketState
    fee_percent: float
    days_remaining: float
    time_stretch_apy: float
    test_id: int

    __test__ = False  # pytest: don't test this class


@dataclass
class TestResultCalcInGivenOutSuccess:
    """Dataclass for calc_in_given_out test results"""

    without_fee_or_slippage: float
    without_fee: float
    hyperdrive_fee: float
    hyperdrive_with_fee: float

    __test__ = False  # pytest: don't test this class


@dataclass
class TestCaseCalcInGivenOutFailure:
    """Dataclass for calc_in_given_out test cases"""

    out: Quantity
    market_state: MarketState
    fee_percent: float
    time_remaining: StretchedTime

    __test__ = False  # pytest: don't test this class


class TestCalcInGivenOut(unittest.TestCase):
    """Unit tests for the calc_in_given_out function"""

    # pylint: disable=line-too-long

    # TODO: Add tests for the Hyperdrive pricing model.
    #
    # TODO: Add tests for the full TradeResult object.
    def test_calc_in_given_out_success(self):
        """Success tests for calc_in_given_out"""

        # Test cases where token_in = TokenType.BASE indicating that bonds are being
        # purchased for base.
        #
        # 1. out_ = 100; 10% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 2. out_ = 100; 20% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 3. out_ = 10k; 10% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 4. out_ = 80k; 10% fee; 100k share reserves; 100k bond reserves;
        #    1 share price; 1 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 5. out_ = 200; 10% fee; 100k share reserves; 100k bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 6. out_ = 200; 10% fee; 100k share reserves; 1M bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
        #    6 mo remaining
        # 7. out_ = 200; 10% fee; 100k share reserves; 1M bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 5% APY;
        #    3 mo remaining
        # 8. out_ = 200; 10% fee; 100k share reserves; 1M bond reserves;
        #    2 share price; 1.5 init share price; t_stretch targeting 10% APY;
        #    3 mo remaining
        base_in_test_cases = [
            (  # test 1, token BASE
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9755311553623102
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=100, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=100000,  # PT reserves
                        share_price=1,  # share price of the LP in the yield source
                        init_share_price=1,  # original share price pool started
                    ),
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6.0 months remaining
                    time_stretch_apy=0.05,  # APY used to calculate time_stretch
                    test_id=1,
                ),
                # in_base=98.7769175342255
                # in_pt=101.25451693299692
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=101.25412932755603,
                    without_fee=101.25451693299692,
                    hyperdrive_fee=0.12541293275560306,
                    hyperdrive_with_fee=101.37992986575253,
                ),
            ),  # end of test 1
            (  # test 2, token BASE
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9755311553623102
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=100, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=100000,  # PT reserves
                        share_price=1,  # share price of the LP in the yield source
                        init_share_price=1,  # original share price pool started
                    ),
                    fee_percent=0.2,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6.0 months remaining
                    time_stretch_apy=0.05,  # APY used to calculate time_stretch
                    test_id=2,
                ),
                # in_base=98.7769175342255
                # in_pt=101.25451693299692
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=101.25412932755603,
                    without_fee=101.25451693299692,
                    hyperdrive_fee=0.2508258655112061,
                    hyperdrive_with_fee=101.50534279850812,
                ),
            ),  # end of test 2
            (  # test 3, token BASE
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9740558904034232
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=10000, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=100000,  # PT reserves
                        share_price=1,  # share price of the LP in the yield source
                        init_share_price=1,  # original share price pool started
                    ),
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6.0 months remaining
                    time_stretch_apy=0.05,  # APY used to calculate time_stretch
                    test_id=3,
                ),
                # in_base=9873.953751197507
                # in_pt=10137.245456477627
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=10133.175672218518,
                    without_fee=10137.245456477627,
                    hyperdrive_fee=13.317567221851846,
                    hyperdrive_with_fee=10150.563023699478,
                ),
            ),  # end of test 3
            (  # test 4, token BASE
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9616634834271521
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=80000, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=100000,  # PT reserves
                        share_price=1,  # share price of the LP in the yield source
                        init_share_price=1,  # original share price pool started
                    ),
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6.0 months remaining
                    time_stretch_apy=0.05,  # APY used to calculate time_stretch
                    test_id=4,
                ),
                # in_base=78754.38434374728
                # in_pt=82076.5665282032
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=81594.5917562025,
                    without_fee=82076.5665282032,
                    hyperdrive_fee=159.45917562024994,
                    hyperdrive_with_fee=82236.02570382346,
                ),
            ),  # end of test 4
            (  # test 5, token BASE
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9781221499330645
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=200, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=100000,  # PT reserves
                        share_price=2,  # share price of the LP in the yield source
                        init_share_price=1.5,  # original share price pool started
                    ),
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6.0 months remaining
                    time_stretch_apy=0.05,  # APY used to calculate time_stretch
                    test_id=5,
                ),
                # in_base=197.81302968543605
                # in_pt=202.23759035329567
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=202.23671962325284,
                    without_fee=202.23759035329567,
                    hyperdrive_fee=0.22367196232528477,
                    hyperdrive_with_fee=202.46126231562096,
                ),
            ),  # end of test 5
            (  # test 6, token BASE
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9412617210897727
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=200, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=1000000,  # PT reserves
                        share_price=2,  # share price of the LP in the yield source
                        init_share_price=1.5,  # original share price pool started
                    ),
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6.0 months remaining
                    time_stretch_apy=0.05,  # APY used to calculate time_stretch
                    test_id=6,
                ),
                # in_base=194.12671964618494
                # in_pt=206.2410336495377
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=206.24037688924835,
                    without_fee=206.2410336495377,
                    hyperdrive_fee=0.6240376889248345,
                    hyperdrive_with_fee=206.86507133846254,
                ),
            ),  # end of test 6
            (  # test 7, token BASE
                # t_d=0.25
                # tau=0.011267922015798525
                # 1-tau=0.9887320779842015
                # t_stretch=22.186877016851916
                # spot_price=0.9701834531122594
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=200, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=1000000,  # PT reserves
                        share_price=2,  # share price of the LP in the yield source
                        init_share_price=1.5,  # original share price pool started
                    ),
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=91.25,  # 3.0 months remaining
                    time_stretch_apy=0.05,  # APY used to calculate time_stretch
                    test_id=7,
                ),
                # in_base=198.50924519836553
                # in_pt=201.5367242335342
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=201.53664478568933,
                    without_fee=201.5367242335342,
                    hyperdrive_fee=0.15366447856893342,
                    hyperdrive_with_fee=201.69038871210313,
                ),
            ),  # end of test 7
            (  # test 8, token BASE
                # t_d=0.25
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=11.093438508425958
                # spot_price=0.9412559326928277
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=200, unit=TokenType.BASE),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=1000000,  # PT reserves
                        share_price=2,  # share price of the LP in the yield source
                        init_share_price=1.5,  # original share price pool started
                    ),
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=91.25,  # 3.0 months remaining
                    time_stretch_apy=0.1,  # APY used to calculate time_stretch
                    test_id=8,
                ),
                # in_base=197.06293355708476
                # in_pt=203.12067932868376
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=203.12051511532638,
                    without_fee=203.12067932868376,
                    hyperdrive_fee=0.31205151153263944,
                    hyperdrive_with_fee=203.4327308402164,
                ),
            ),  # end of test 8
        ]

        pt_in_test_cases = [
            (  # test 1, token PT
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9755458141947515
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=100, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=100000,  # PT reserves
                        share_price=1,  # share price of the LP in the yield source
                        init_share_price=1,  # original share price pool started
                    ),
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6.0 months remaining
                    time_stretch_apy=0.05,  # APY used to calculate time_stretch
                    test_id=1,
                ),
                # in_base=98.77765036644996
                # in_pt=101.25374663824914
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=97.55458141947516,
                    without_fee=98.77765036644996,
                    hyperdrive_fee=0.2506718336486724,
                    hyperdrive_with_fee=99.02832220009863,
                ),
            ),  # end of test 1
            (  # test 2, token PT
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9755458141947515
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=100, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=100000,  # PT reserves
                        share_price=1,  # share price of the LP in the yield source
                        init_share_price=1,  # original share price pool started
                    ),
                    fee_percent=0.2,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6.0 months remaining
                    time_stretch_apy=0.05,  # APY used to calculate time_stretch
                    test_id=2,
                ),
                # in_base=98.77765036644996
                # in_pt=101.25374663824914
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=97.55458141947516,
                    without_fee=98.77765036644996,
                    hyperdrive_fee=0.5013436672973448,
                    hyperdrive_with_fee=99.27899403374731,
                ),
            ),  # end of test 2
            (  # test 3, token PT
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9755458141947515
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=10000, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=100000,  # PT reserves
                        share_price=1,  # share price of the LP in the yield source
                        init_share_price=1,  # original share price pool started
                    ),
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6.0 months remaining
                    time_stretch_apy=0.05,  # APY used to calculate time_stretch
                    test_id=3,
                ),
                # in_base=9881.291560883124
                # in_pt=10129.256465315295
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=9755.458141947514,
                    without_fee=9881.291560883124,
                    hyperdrive_fee=25.06718336486724,
                    hyperdrive_with_fee=9906.358744247991,
                ),
            ),  # end of test 3
            (  # test 4, token PT
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9755458141947515
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=80000, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=100000,  # PT reserves
                        share_price=1,  # share price of the LP in the yield source
                        init_share_price=1,  # original share price pool started
                    ),
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6.0 months remaining
                    time_stretch_apy=0.05,  # APY used to calculate time_stretch
                    test_id=4,
                ),
                # in_base=79237.33095282264
                # in_pt=81280.6811146175
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=78043.66513558012,
                    without_fee=79237.33095282264,
                    hyperdrive_fee=200.53746691893792,
                    hyperdrive_with_fee=79437.86841974157,
                ),
            ),  # end of test 4
            (  # test 5, token PT
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.97813868424652
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=200, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=100000,  # PT reserves
                        share_price=2,  # share price of the LP in the yield source
                        init_share_price=1.5,  # original share price pool started
                    ),
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6.0 months remaining
                    time_stretch_apy=0.05,  # APY used to calculate time_stretch
                    test_id=5,
                ),
                # in_base=197.81468293908983
                # in_pt=404.4734651519102
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=195.627736849304,
                    without_fee=197.81468293908983,
                    hyperdrive_fee=0.89399657147065,
                    hyperdrive_with_fee=198.70867951056047,
                ),
            ),  # end of test 5
            (  # test 6, token PT
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9412732940426811
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=200, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=1000000,  # PT reserves
                        share_price=2,  # share price of the LP in the yield source
                        init_share_price=1.5,  # original share price pool started
                    ),
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=182.5,  # 6.0 months remaining
                    time_stretch_apy=0.05,  # APY used to calculate time_stretch
                    test_id=6,
                ),
                # in_base=194.12787670694524
                # in_pt=412.48076756019145
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=188.25465880853622,
                    without_fee=194.12787670694524,
                    hyperdrive_fee=2.4956282656270106,
                    hyperdrive_with_fee=196.62350497257225,
                ),
            ),  # end of test 6
            (  # test 7, token PT
                # t_d=0.25
                # tau=0.011267922015798525
                # 1-tau=0.9887320779842015
                # t_stretch=22.186877016851916
                # spot_price=0.9701924005282051
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=200, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=1000000,  # PT reserves
                        share_price=2,  # share price of the LP in the yield source
                        init_share_price=1.5,  # original share price pool started
                    ),
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=91.25,  # 3.0 months remaining
                    time_stretch_apy=0.05,  # APY used to calculate time_stretch
                    test_id=7,
                ),
                # in_base=198.50969252112554
                # in_pt=403.0726566025987
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=194.038480105641,
                    without_fee=198.50969252112554,
                    hyperdrive_fee=1.2289355989829076,
                    hyperdrive_with_fee=199.73862812010844,
                ),
            ),  # end of test 7
            (  # test 8, token PT
                # t_d=0.25
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=11.093438508425958
                # spot_price=0.9412732940426811
                TestCaseCalcInGivenOutSuccess(
                    out=Quantity(amount=200, unit=TokenType.PT),
                    market_state=MarketState(
                        share_reserves=100000,  # base reserves (in share terms) base = share * share_price
                        bond_reserves=1000000,  # PT reserves
                        share_price=2,  # share price of the LP in the yield source
                        init_share_price=1.5,  # original share price pool started
                    ),
                    fee_percent=0.1,  # fee percent (normally 10%)
                    days_remaining=91.25,  # 3.0 months remaining
                    time_stretch_apy=0.1,  # APY used to calculate time_stretch
                    test_id=8,
                ),
                # in_base=197.0638015367149
                # in_pt=406.2397271185182
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=188.25465880853622,
                    without_fee=197.0638015367149,
                    hyperdrive_fee=2.4956282656270106,
                    hyperdrive_with_fee=199.5594298023419,
                ),
            ),  # end of test 8
        ]

        # test_cases = base_in_test_cases + pt_in_test_cases
        test_cases = base_in_test_cases
        # test_cases = pt_in_test_cases

        pricing_model = HyperdrivePricingModel()
        for (
            test_case,
            expected_result,
        ) in test_cases:
            time_stretch = pricing_model.calc_time_stretch(test_case.time_stretch_apy)
            time_remaining = StretchedTime(days=test_case.days_remaining, time_stretch=time_stretch)

            # Ensure we get the expected results from the pricing model.
            trade_result = pricing_model.calc_in_given_out(
                out=test_case.out,
                market_state=test_case.market_state,
                fee_percent=test_case.fee_percent,
                time_remaining=time_remaining,
            )

            np.testing.assert_almost_equal(
                trade_result.breakdown.without_fee_or_slippage,
                expected_result.without_fee_or_slippage,
                err_msg=f"test {test_case.test_id} unexpected without_fee_or_slippage",
            )
            np.testing.assert_almost_equal(
                trade_result.breakdown.without_fee,
                expected_result.without_fee,
                err_msg=f"test {test_case.test_id} unexpected without_fee",
            )
            np.testing.assert_almost_equal(
                trade_result.breakdown.fee,
                expected_result.hyperdrive_fee,
                err_msg=f"test {test_case.test_id} unexpected hyperdrive fee",
            )
            np.testing.assert_almost_equal(
                trade_result.breakdown.with_fee,
                expected_result.hyperdrive_with_fee,
                err_msg=f"test {test_case.test_id} unexpected hyperdrive with_fee",
            )

    # # TODO: This should be refactored to be a test for check_input_assertions and check_output_assertions
    # def test_calc_in_given_out_failure(self):
    #     """Failure tests for calc_in_given_out"""
    #     pricing_models: list[PricingModel] = [YieldSpacePricingModel()]

    #     # Failure test cases.
    #     test_cases = [
    #         TestCaseCalcInGivenOutFailure(
    #             out=Quantity(amount=-1, unit=TokenType.PT),
    #             market_state=MarketState(
    #                 share_reserves=100_000,
    #                 bond_reserves=1_000_000,
    #                 share_price=1,
    #                 init_share_price=1,
    #             ),
    #             fee_percent=0.01,
    #             time_remaining=StretchedTime(days=91.25, time_stretch=1),
    #         ),
    #         TestCaseCalcInGivenOutFailure(
    #             out=Quantity(amount=0, unit=TokenType.PT),
    #             market_state=MarketState(
    #                 share_reserves=100_000,
    #                 bond_reserves=1_000_000,
    #                 share_price=1,
    #                 init_share_price=1,
    #             ),
    #             fee_percent=0.01,
    #             time_remaining=StretchedTime(days=91.25, time_stretch=1),
    #         ),
    #         TestCaseCalcInGivenOutFailure(
    #             out=Quantity(amount=100, unit=TokenType.PT),
    #             market_state=MarketState(
    #                 share_reserves=-1,
    #                 bond_reserves=1_000_000,
    #                 share_price=1,
    #                 init_share_price=1,
    #             ),
    #             fee_percent=0.01,
    #             time_remaining=StretchedTime(days=91.25, time_stretch=1),
    #         ),
    #         TestCaseCalcInGivenOutFailure(
    #             out=Quantity(amount=100, unit=TokenType.PT),
    #             market_state=MarketState(
    #                 share_reserves=0,
    #                 bond_reserves=1_000_000,
    #                 share_price=1,
    #                 init_share_price=1,
    #             ),
    #             fee_percent=0.01,
    #             time_remaining=StretchedTime(days=91.25, time_stretch=1),
    #         ),
    #         TestCaseCalcInGivenOutFailure(
    #             out=Quantity(amount=100, unit=TokenType.PT),
    #             market_state=MarketState(
    #                 share_reserves=100_000,
    #                 bond_reserves=-1,
    #                 share_price=1,
    #                 init_share_price=1,
    #             ),
    #             fee_percent=0.01,
    #             time_remaining=StretchedTime(days=91.25, time_stretch=1),
    #         ),
    #         TestCaseCalcInGivenOutFailure(
    #             out=Quantity(amount=100, unit=TokenType.PT),
    #             market_state=MarketState(
    #                 share_reserves=100_000,
    #                 bond_reserves=1_000_000,
    #                 share_price=1,
    #                 init_share_price=1,
    #             ),
    #             fee_percent=-1,
    #             time_remaining=StretchedTime(days=91.25, time_stretch=1),
    #         ),
    #         TestCaseCalcInGivenOutFailure(
    #             out=Quantity(amount=100, unit=TokenType.PT),
    #             market_state=MarketState(
    #                 share_reserves=100_000,
    #                 bond_reserves=1_000_000,
    #                 share_price=1,
    #                 init_share_price=1,
    #             ),
    #             fee_percent=1.1,
    #             time_remaining=StretchedTime(days=91.25, time_stretch=1),
    #         ),
    #         TestCaseCalcInGivenOutFailure(
    #             out=Quantity(amount=100, unit=TokenType.PT),
    #             market_state=MarketState(
    #                 share_reserves=100_000,
    #                 bond_reserves=1_000_000,
    #                 share_price=1,
    #                 init_share_price=1,
    #             ),
    #             fee_percent=1.1,
    #             time_remaining=StretchedTime(days=-91.25, time_stretch=1),
    #         ),
    #         TestCaseCalcInGivenOutFailure(
    #             out=Quantity(amount=100, unit=TokenType.PT),
    #             market_state=MarketState(
    #                 share_reserves=100_000,
    #                 bond_reserves=1_000_000,
    #                 share_price=1,
    #                 init_share_price=1,
    #             ),
    #             fee_percent=0.1,
    #             time_remaining=StretchedTime(days=365, time_stretch=1),
    #         ),
    #         TestCaseCalcInGivenOutFailure(
    #             out=Quantity(amount=100, unit=TokenType.PT),
    #             market_state=MarketState(
    #                 share_reserves=100_000,
    #                 bond_reserves=1_000_000,
    #                 share_price=1,
    #                 init_share_price=1,
    #             ),
    #             fee_percent=0.1,
    #             time_remaining=StretchedTime(days=500, time_stretch=1),
    #         ),
    #         TestCaseCalcInGivenOutFailure(
    #             out=Quantity(amount=10_000_000, unit=TokenType.BASE),
    #             market_state=MarketState(
    #                 share_reserves=100_000,
    #                 bond_reserves=1_000_000,
    #                 share_price=1,
    #                 init_share_price=1,
    #             ),
    #             fee_percent=0.1,
    #             time_remaining=StretchedTime(days=92.5, time_stretch=1),
    #         ),
    #         TestCaseCalcInGivenOutFailure(
    #             out=Quantity(amount=100, unit=TokenType.BASE),
    #             market_state=MarketState(
    #                 share_reserves=100_000,
    #                 bond_reserves=1_000_000,
    #                 share_price=2,
    #                 init_share_price=0,
    #             ),
    #             fee_percent=0.1,
    #             time_remaining=StretchedTime(days=91.25, time_stretch=1),
    #         ),
    #         TestCaseCalcInGivenOutFailure(
    #             out=Quantity(amount=100, unit=TokenType.BASE),
    #             market_state=MarketState(
    #                 share_reserves=100_000,
    #                 bond_reserves=1_000_000,
    #                 share_price=1,
    #                 init_share_price=1.5,
    #             ),
    #             fee_percent=0.1,
    #             time_remaining=StretchedTime(days=91.25, time_stretch=1),
    #         ),
    #         TestCaseCalcInGivenOutFailure(
    #             out=Quantity(amount=100, unit=TokenType.BASE),
    #             market_state=MarketState(
    #                 share_reserves=100_000,
    #                 bond_reserves=1_000_000,
    #                 share_price=0,
    #                 init_share_price=1.5,
    #             ),
    #             fee_percent=0.1,
    #             time_remaining=StretchedTime(days=91.25, time_stretch=1),
    #         ),
    #     ]

    #     # Iterate over all of the test cases and verify that the pricing model
    #     # raises an AssertionError for each test case.
    #     for test_case in test_cases:
    #         for pricing_model in pricing_models:
    #             with self.assertRaises(AssertionError):
    #                 pricing_model.check_input_assertions(
    #                     quantity=test_case.out,
    #                     market_state=test_case.market_state,
    #                     fee_percent=test_case.fee_percent,
    #                     time_remaining=test_case.time_remaining,
    #                 )
    #                 trade_result = pricing_model.calc_in_given_out(
    #                     out=test_case.out,
    #                     market_state=test_case.market_state,
    #                     fee_percent=test_case.fee_percent,
    #                     time_remaining=test_case.time_remaining,
    #                 )
    #                 pricing_model.check_output_assertions(
    #                     trade_result=trade_result,
    #                 )

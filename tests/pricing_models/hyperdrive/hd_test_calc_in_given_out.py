"""
Testing for the calc_in_given_out of the pricing models.
"""

# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init
# pylint: disable=duplicate-code

import unittest
import numpy as np
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel

from elfpy.types import MarketState, Quantity, StretchedTime, TokenType
from tests.pricing_models.test_dataclasses import (
    TestCaseCalcInGivenOutFailure,
    TestCaseCalcInGivenOutSuccess,
    TestResultCalcInGivenOutSuccess,
)


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
                # spot_price=0.9516610350825238
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
                ),
                # in_base=97.58374088542769
                # in_pt=102.54051519598579
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=102.53971546251678,
                    without_fee=102.54051519598579,
                    fee=0.25397154625167895,
                    with_fee=102.79448674223747,
                ),
            ),  # end of test 1
            (  # test 2, token BASE
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9516610350825238
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
                ),
                # in_base=97.58374088542769
                # in_pt=102.54051519598579
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=102.53971546251678,
                    without_fee=102.54051519598579,
                    fee=0.5079430925033579,
                    with_fee=103.04845828848914,
                ),
            ),  # end of test 2
            (  # test 3, token BASE
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9487848776296056
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
                ),
                # in_base=9750.950516367564
                # in_pt=10278.313158090226
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=10269.89849637121,
                    without_fee=10278.313158090226,
                    fee=26.989849637120926,
                    with_fee=10305.303007727347,
                ),
            ),  # end of test 3
            (  # test 4, token BASE
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9247966553572445
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
                ),
                # in_base=77535.00890610163
                # in_pt=84268.97713182
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=83252.75158412871,
                    without_fee=84268.97713182,
                    fee=325.2751584128717,
                    with_fee=84594.25229023286,
                ),
            ),  # end of test 4
            (  # test 5, token BASE
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9567229401896802
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
                ),
                # in_base=195.6738646971353
                # in_pt=204.52526228054194
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=204.52346839323616,
                    without_fee=204.52526228054194,
                    fee=0.45234683932361636,
                    with_fee=204.97760911986555,
                ),
            ),  # end of test 5
            (  # test 6, token BASE
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.885973627588881
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
                ),
                # in_base=188.59833831203287
                # in_pt=212.87157998187467
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=212.87017681569534,
                    without_fee=212.87157998187467,
                    fee=1.2870176815695311,
                    with_fee=214.1585976634442,
                ),
            ),  # end of test 6
            (  # test 7, token BASE
                # t_d=0.25
                # tau=0.011267922015798525
                # 1-tau=0.9887320779842015
                # t_stretch=22.186877016851916
                # spot_price=0.885962730829445
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
                ),
                # in_base=194.29838049286627
                # in_pt=206.43613336980343
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=206.4357825223524,
                    without_fee=206.43613336980343,
                    fee=0.6435782522352407,
                    with_fee=207.07971162203867,
                ),
            ),  # end of test 7
            (  # test 8, token BASE
                # t_d=0.25
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=11.093438508425958
                # spot_price=0.7849299604187676
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
                ),
                # in_base=189.24688558027265
                # in_pt=213.70075247436762
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=213.69995097820515,
                    without_fee=213.70075247436762,
                    fee=1.3699950978205144,
                    with_fee=215.07074757218814,
                ),
            ),  # end of test 8
        ]

        pt_in_test_cases = [
            (  # test 1, token PT
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9517182274304707
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
                ),
                # in_base=97.5866001243412
                # in_pt=102.53735730214976
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=97.58591137152354,
                    without_fee=97.5866001243412,
                    fee=0.24140886284764632,
                    with_fee=97.82800898718885,
                ),
            ),  # end of test 9
            (  # test 2, token PT
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9517182274304707
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
                ),
                # in_base=97.5866001243412
                # in_pt=102.53735730214976
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=97.58591137152354,
                    without_fee=97.5866001243412,
                    fee=0.48281772569529263,
                    with_fee=98.0694178500365,
                ),
            ),  # end of test 10
            (  # test 3, token PT
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9545075460138804
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
                ),
                # in_base=9779.197793075873
                # in_pt=10246.109814837924
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=9772.537730069402,
                    without_fee=9779.197793075873,
                    fee=22.746226993059782,
                    with_fee=9801.944020068933,
                ),
            ),  # end of test 11
            (  # test 4, token PT
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9724844998246822
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
                ),
                # in_base=79269.0508947279
                # in_pt=81569.70379803452
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=78899.37999298729,
                    without_fee=79269.0508947279,
                    fee=110.06200070127115,
                    with_fee=79379.11289542918,
                ),
            ),  # end of test 12
            (  # test 5, token PT
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.9567876240571412
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
                ),
                # in_base=195.68033249810105
                # in_pt=204.51819491188508
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=195.6787624057141,
                    without_fee=195.68033249810105,
                    fee=0.4321237594285876,
                    with_fee=196.11245625752963,
                ),
            ),  # end of test 13
            (  # test 6, token PT
                # t_d=0.5
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=22.186877016851916
                # spot_price=0.8860171912017127
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
                ),
                # in_base=188.60269388841698
                # in_pt=212.8660290548578
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=188.60171912017125,
                    without_fee=188.60269388841698,
                    fee=1.1398280879828715,
                    with_fee=189.74252197639984,
                ),
            ),  # end of test 14
            (  # test 7, token PT
                # t_d=0.25
                # tau=0.011267922015798525
                # 1-tau=0.9887320779842015
                # t_stretch=22.186877016851916
                # spot_price=0.8860280762544887
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
                ),
                # in_base=194.30164747033268
                # in_pt=206.43197067594156
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=194.30140381272443,
                    without_fee=194.30164747033268,
                    fee=0.5698596187275567,
                    with_fee=194.87150708906023,
                ),
            ),  # end of test 15
            (  # test 8, token PT
                # t_d=0.25
                # tau=0.02253584403159705
                # 1-tau=0.977464155968403
                # t_stretch=11.093438508425958
                # spot_price=0.7850457519112299
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
                ),
                # in_base=189.25267474842258
                # in_pt=213.6913557597436
                TestResultCalcInGivenOutSuccess(
                    without_fee_or_slippage=189.25228759556148,
                    without_fee=189.25267474842258,
                    fee=1.0747712404438503,
                    with_fee=190.32744598886643,
                ),
            ),  # end of test 16
        ]

        test_cases = base_in_test_cases + pt_in_test_cases

        pricing_model = HyperdrivePricingModel()
        for (
            test_id,
            (
                test_case,
                expected_result,
            ),
        ) in enumerate(test_cases):
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
                err_msg=f"test {test_id} unexpected without_fee_or_slippage",
            )
            np.testing.assert_almost_equal(
                trade_result.breakdown.without_fee,
                expected_result.without_fee,
                err_msg=f"test {test_id} unexpected without_fee",
            )
            np.testing.assert_almost_equal(
                trade_result.breakdown.fee,
                expected_result.fee,
                err_msg=f"test {test_id} unexpected hyperdrive fee",
            )
            np.testing.assert_almost_equal(
                trade_result.breakdown.with_fee,
                expected_result.with_fee,
                err_msg=f"test {test_id} unexpected hyperdrive with_fee",
            )

    # # TODO: This should be refactored to be a test for check_input_assertions and check_output_assertions
    def test_calc_in_given_out_failure(self):
        """Failure tests for calc_in_given_out"""

        pricing_model = HyperdrivePricingModel()
        # Failure test cases.
        test_cases = [
            TestCaseCalcInGivenOutFailure(
                out=Quantity(amount=-1, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
            ),
            TestCaseCalcInGivenOutFailure(
                out=Quantity(amount=0, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
            ),
            TestCaseCalcInGivenOutFailure(
                out=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=-1,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
            ),
            TestCaseCalcInGivenOutFailure(
                out=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=0,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
            ),
            TestCaseCalcInGivenOutFailure(
                out=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=-1,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.01,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
            ),
            TestCaseCalcInGivenOutFailure(
                out=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=-1,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
            ),
            TestCaseCalcInGivenOutFailure(
                out=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=1.1,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
            ),
            TestCaseCalcInGivenOutFailure(
                out=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=1.1,
                time_remaining=StretchedTime(days=-91.25, time_stretch=1),
            ),
            TestCaseCalcInGivenOutFailure(
                out=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.1,
                time_remaining=StretchedTime(days=365, time_stretch=1),
            ),
            TestCaseCalcInGivenOutFailure(
                out=Quantity(amount=100, unit=TokenType.PT),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.1,
                time_remaining=StretchedTime(days=500, time_stretch=1),
            ),
            TestCaseCalcInGivenOutFailure(
                out=Quantity(amount=10_000_000, unit=TokenType.BASE),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1,
                ),
                fee_percent=0.1,
                time_remaining=StretchedTime(days=92.5, time_stretch=1),
            ),
            TestCaseCalcInGivenOutFailure(
                out=Quantity(amount=100, unit=TokenType.BASE),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=2,
                    init_share_price=0,
                ),
                fee_percent=0.1,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
            ),
            TestCaseCalcInGivenOutFailure(
                out=Quantity(amount=100, unit=TokenType.BASE),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=1,
                    init_share_price=1.5,
                ),
                fee_percent=0.1,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
            ),
            TestCaseCalcInGivenOutFailure(
                out=Quantity(amount=100, unit=TokenType.BASE),
                market_state=MarketState(
                    share_reserves=100_000,
                    bond_reserves=1_000_000,
                    share_price=0,
                    init_share_price=1.5,
                ),
                fee_percent=0.1,
                time_remaining=StretchedTime(days=91.25, time_stretch=1),
            ),
        ]

        # Iterate over all of the test cases and verify that the pricing model
        # raises an AssertionError for each test case.
        for test_case in test_cases:
            with self.assertRaises(AssertionError):
                pricing_model.check_input_assertions(
                    quantity=test_case.out,
                    market_state=test_case.market_state,
                    fee_percent=test_case.fee_percent,
                    time_remaining=test_case.time_remaining,
                )
                trade_result = pricing_model.calc_in_given_out(
                    out=test_case.out,
                    market_state=test_case.market_state,
                    fee_percent=test_case.fee_percent,
                    time_remaining=test_case.time_remaining,
                )
                pricing_model.check_output_assertions(
                    trade_result=trade_result,
                )

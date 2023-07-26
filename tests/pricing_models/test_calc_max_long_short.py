"""Testing for the calculate_max_long function of the pricing models"""
from __future__ import annotations

import unittest
from dataclasses import dataclass

from fixedpointmath import FixedPoint

import elfpy.time as time
import elfpy.utils.logs as log_utils
from elfpy.markets.hyperdrive import HyperdriveMarketState, HyperdrivePricingModel
from tests.fixtures.hyperdrive_config import HyperdriveConfig


@dataclass
class TestCaseCalcMax:
    """Dataclass for calculate_max_long test cases"""

    market_state: HyperdriveMarketState
    market_config: HyperdriveConfig
    time_remaining: time.StretchedTime

    __test__ = False  # pytest: don't test this class


class TestCalculateMax(unittest.TestCase):
    """Tests calculate_max_short and calculate_max_long functions within the pricing model"""

    def test_calculate_max_long(self):
        """Tests that calculate_max_long and calculate_max_short are safe

        Values from Hyperdrive

        # Market information pre-trade
        poolConfig
            initialSharePrice 1000000000000000000
            minimumShareReserves 1000000000000000000
            positionDuration 31536000
            checkpointDuration 86400
            timeStretch 44463125629060298
            governance 0x71554DE85ecD7bDD19e24078e518ead88d691871
            feeCollector 0xd002315CAcB4882e1099EDFb00895Fa8867256B5
            fees.curve 0
            fees.flat 0
            fees.governance 0
            oracleSize 5
            updateGap 1000
        poolInfo
            shareReserves 500000000000000000000000000
            bondReserves 1498059016940075710500000000
            lpTotalSupply 499999999000000000000000000
            sharePrice 1000000000000000000
            longsOutstanding 0
            longAverageMaturityTime 0
            shortsOutstanding 0
            shortAverageMaturityTime 0
            shortBaseVolume 0
            withdrawalSharesReadyToWithdraw 0

        # Expected result
        baseAmount 493213221042049515844300901
        bondAmount 504845795898026194655699099

        # Market information post-trade
        poolInfo
            shareReserves 993213221042049515844300901
            bondReserves 993213221042049549613550417
            lpTotalSupply 499999999000000000000000000
            sharePrice 1000000000000000000
            longsOutstanding 504845795898026160886449583
            longAverageMaturityTime 126144000000000000000000000
            shortsOutstanding 0
            shortAverageMaturityTime 0
            shortBaseVolume 0
            withdrawalSharesReadyToWithdraw 0
            withdrawalSharesProceeds 0
        """
        log_utils.setup_logging(log_filename="test_calculate_max")
        pricing_model: HyperdrivePricingModel = HyperdrivePricingModel()

        test_case = TestCaseCalcMax(
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint(scaled_value=500000000000000000000000000),
                bond_reserves=FixedPoint(scaled_value=1498059016940075710500000000),
                lp_total_supply=FixedPoint(scaled_value=499999999000000000000000000),
                init_share_price=FixedPoint(1),
                share_price=FixedPoint(1),
                curve_fee_multiple=FixedPoint(0),
                flat_fee_multiple=FixedPoint(0),
            ),
            time_remaining=time.StretchedTime(
                days=FixedPoint(90),
                time_stretch=FixedPoint(scaled_value=44463125629060298),
                normalizing_constant=FixedPoint(365),
            ),
            market_config=HyperdriveConfig(time_stretch=44463125629060298, minimum_share_reserves=FixedPoint(1)),
        )

        max_long_result = pricing_model.calculate_max_long(
            test_case.market_state.share_reserves,
            test_case.market_state.bond_reserves,
            test_case.market_state.longs_outstanding,
            # TODO: remove inversion once we switch base_pricing_model.calc_time_stretch to return 1/t
            # issue #692
            FixedPoint(1) / FixedPoint(scaled_value=test_case.market_config.time_stretch),
            test_case.market_state.share_price,
            test_case.market_state.share_price,
            test_case.market_config.minimum_share_reserves,
            max_iterations=20,
        )

        self.assertEqual(max_long_result.base_amount, FixedPoint(scaled_value=493213221042049515844300901))
        self.assertEqual(max_long_result.bond_amount, FixedPoint(scaled_value=504845795898026194655699099))

        log_utils.close_logging()

    def test_calculate_max_short(self):
        """
        Tests that calculate_max_long and calculate_max_short are safe, by checking
            apr >= 0
            share_price * market_state.share_reserves >= base_buffer
            bond_reserves >= bond_buffer
        """
        log_utils.setup_logging(log_filename="test_calculate_max")
        pricing_model: HyperdrivePricingModel = HyperdrivePricingModel()

        # Values from Hyperdrive
        # poolConfig
        #     initialSharePrice 1000000000000000000
        #     minimumShareReserves 1000000000000000000
        #     positionDuration 31536000
        #     checkpointDuration 86400
        #     timeStretch 44463125629060298
        #     governance 0x71554DE85ecD7bDD19e24078e518ead88d691871
        #     feeCollector 0xd002315CAcB4882e1099EDFb00895Fa8867256B5
        #     fees.curve 0
        #     fees.flat 0
        #     fees.governance 0
        #     oracleSize 5
        #     updateGap 1000
        # poolInfo
        #     shareReserves 500000000000000000000000000
        #     bondReserves 1498059016940075710500000000
        #     lpTotalSupply 499999999000000000000000000
        #     sharePrice 1000000000000000000
        #     longsOutstanding 0
        #     longAverageMaturityTime 0
        #     shortsOutstanding 0
        #     shortAverageMaturityTime 0
        #     shortBaseVolume 0
        #     withdrawalSharesReadyToWithdraw 0
        #     withdrawalSharesProceeds 0

        # bondAmount 553481229469973716375181531

        test_case = TestCaseCalcMax(
            market_state=HyperdriveMarketState(
                share_reserves=FixedPoint(scaled_value=500000000000000000000000000),
                bond_reserves=FixedPoint(scaled_value=1498059016940075710500000000),
                lp_total_supply=FixedPoint(scaled_value=499999999000000000000000000),
                longs_outstanding=FixedPoint(scaled_value=0),
                init_share_price=FixedPoint(1),
                share_price=FixedPoint(1),
                curve_fee_multiple=FixedPoint(0),
                flat_fee_multiple=FixedPoint(0),
            ),
            time_remaining=time.StretchedTime(
                days=FixedPoint(90),
                time_stretch=FixedPoint(scaled_value=44463125629060298),
                normalizing_constant=FixedPoint(365),
            ),
            market_config=HyperdriveConfig(time_stretch=44463125629060298),
        )

        max_short = pricing_model.calculate_max_short(
            test_case.market_state.share_reserves,
            test_case.market_state.bond_reserves,
            test_case.market_state.longs_outstanding,
            # TODO: remove inversion once we switch base_pricing_model.calc_time_stretch to return 1/t
            # issue #692
            FixedPoint(1) / FixedPoint(scaled_value=test_case.market_config.time_stretch),
            test_case.market_state.share_price,
            test_case.market_state.share_price,
            test_case.market_config.minimum_share_reserves,
        )

        self.assertEqual(max_short, FixedPoint(scaled_value=553481229469973716375181531))

        log_utils.close_logging()

# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-module-docstring
# pylint: disable=attribute-defined-outside-init
# pylint: disable=wrong-import-position

import os
import sys

import unittest
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path: sys.path.append(ROOT_DIR)

from sim import YieldSimulator, ElementPricingModel, YieldSpacev2PricingModel

class TestUtils(unittest.TestCase):
    def setup_vars(self):
        # fixed variables
        self.random_seed = 3
        self.test_rng = np.random.default_rng(self.random_seed)
        self.simulator_rng = np.random.default_rng(self.random_seed)
        self.config = {
            'min_fee': 0.5,
            'max_fee': 0.5,
            'floor_fee': 0,
            't_min': 0.1,
            't_max': 0.1,
            'base_asset_price': 2500., # aka market price
            'min_target_liquidity': 100000.,
            'max_target_liquidity': 100000.,
            'min_target_volume': 2e5,
            'max_target_volume': 2e5,
            'min_pool_apy': 0.5,
            'max_pool_apy': 50,
            'min_vault_age': 0.,
            'max_vault_age': 2,
            'min_vault_apy': 0.,
            'max_vault_apy': 10.,
            'precision': None,
            'pricing_model_name': 'YieldSpacev2',
            'tokens': ['base', 'fyt'],
            'trade_direction': 'out',
            'pool_duration': 180,
            'num_trading_days': 180, # should be <= days_until_maturity
            'rng': self.simulator_rng,
        }
        # looped variables
        self.num_trading_days_list = [1, 5, 10]
        # random variables

        target_liquidity_min = 1e5
        target_liquidity_max = 1e6
        base_asset_price_min = 2e3
        base_asset_price_max = 3e3
        base_asset_reserves_min = 1752
        base_asset_reserves_max = 3007
        token_asset_reserves_min = 1136
        token_asset_reserves_max = 2378
        total_supply_min = 4104
        total_supply_max = 4104
        time_remaining_min = 0.01
        time_remaining_max = 0.99
        init_share_price_min = 1.10
        init_share_price_max = 1.10
        share_price_min = 1.10
        share_price_max = 1.12
        self.base_asset_reserves = self.test_rng.uniform(base_asset_reserves_min, base_asset_reserves_max)
        self.token_asset_reserves = self.test_rng.uniform(token_asset_reserves_min, token_asset_reserves_max)
        self.total_supply = self.test_rng.uniform(total_supply_min, total_supply_max)
        self.time_remaining = self.test_rng.uniform(time_remaining_min, time_remaining_max)
        self.init_share_price = self.test_rng.uniform(init_share_price_min, init_share_price_max)
        self.share_price = self.test_rng.uniform(share_price_min, share_price_max)
        self.target_liquidity = self.test_rng.uniform(target_liquidity_min, target_liquidity_max)
        self.base_asset_price = self.test_rng.uniform(base_asset_price_min, base_asset_price_max)

#    def test_calc_spot_price(self):
#        self.setup_vars()
#        pool_apy = self.test_rng.normal(loc=10, scale=0.1)
#        pool_duration = 180
#        pricing_models = [ElementPricingModel(), YieldSpacev2PricingModel()]
#        for pricing_model in pricing_models:
#            # Shared calculations
#            time_stretch = pricing_model.calc_time_stretch(pool_apy)
#            (base_asset_reserves, token_asset_reserves) = pricing_model.calc_liquidity(
#                self.target_liquidity,
#                self.base_asset_price,
#                pool_apy,
#                pool_duration,
#                time_stretch,
#                self.init_share_price,
#                self.init_share_price)[:2]
#            total_supply = base_asset_reserves + token_asset_reserves
#            days_remaining = pricing_model.norm_days(pool_duration)
#            time_remaining = pricing_model.stretch_time(days_remaining, time_stretch)
#            # Version 1
#            spot_price_from_reserves = pricing_model.calc_spot_price(base_asset_reserves,
#                token_asset_reserves, total_supply, time_remaining,
#                self.init_share_price, self.init_share_price)
#            # Version 2
#            apy = pricing_model.apy(spot_price_from_reserves, days_remaining)
#            spot_price_from_apy = pricing_model.calc_spot_price_from_apy(apy, days_remaining)
#            # Test
#            np.testing.assert_allclose(spot_price_from_reserves, spot_price_from_apy)
#
    def test_get_days_remaining(self):
        self.setup_vars()
        simulator = YieldSimulator(**self.config)
        simulator.set_random_variables()
        for num_trading_days in self.num_trading_days_list:
            override_dict = {'num_trading_days': num_trading_days}
            simulator.setup_pricing_and_market(override_dict)
            for day in range(num_trading_days):
                days_remaining = simulator.get_days_remaining()
                test_days_remaining = self.config['pool_duration'] - day
                np.testing.assert_allclose(days_remaining, test_days_remaining)
                simulator.market.tick(simulator.step_size)
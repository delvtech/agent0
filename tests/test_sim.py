
import os, sys

import unittest
import numpy as np


ROOT_DIR = os.path.dirname(os.getcwd())
if ROOT_DIR not in sys.path: sys.path.append(ROOT_DIR)

from analysis.sim import YieldSimulator


class TestUtils(unittest.TestCase):
    def test_simulator(self):
        ## fixed variables
        random_seed = 3
        config = {
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
            'rng': np.random.default_rng(random_seed),
        }
        ## looped variables
        num_trading_days_list = [1, 5, 10]
        simulator = YieldSimulator(**config)
        simulator.set_random_variables()
        for num_trading_days in num_trading_days_list:
            override_dict = {
                'num_trading_days': num_trading_days,
            }
            simulator.setup_pricing_and_market(override_dict)
            for day in range(num_trading_days):
                days_remaining = simulator.get_days_remaining()
                calc_days_remaining = lambda pool_duration, current_day : pool_duration - current_day
                test_days_remaining = calc_days_remaining(config['pool_duration'], day)
                np.testing.assert_allclose(days_remaining, test_days_remaining)
                simulator.market.tick(simulator.step_size)
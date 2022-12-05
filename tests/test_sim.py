"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init

import unittest
import itertools
import numpy as np
import pandas as pd
import os, sys

sys.path.insert(1, os.path.join(os.getcwd(), "src"))

from elfpy.simulators import YieldSimulator
from elfpy.pricing_models import ElementPricingModel, HyperdrivePricingModel
from elfpy.markets import Market
from elfpy.utils.parse_config import AMMConfig, Config, MarketConfig, SimulatorConfig


class BaseTest(unittest.TestCase):
    """Generic test class"""

    def setup_test_vars(self):
        """Assigns member variables that are useful for many tests"""
        random_seed = 123
        simulator_rng = np.random.default_rng(random_seed)
        num_vals_per_variable = 4
        self.test_rng = np.random.default_rng(simulator_rng)
        self.target_liquidity_vals = self.test_rng.uniform(low=1e5, high=1e6, size=num_vals_per_variable)
        self.base_asset_price_vals = self.test_rng.uniform(low=2e3, high=3e3, size=num_vals_per_variable)
        self.init_share_price_vals = self.test_rng.uniform(low=1.0, high=2.0, size=num_vals_per_variable)
        self.normalizing_constant_vals = self.test_rng.uniform(low=0, high=365, size=num_vals_per_variable)
        self.time_stretch_vals = self.test_rng.normal(loc=10, scale=0.1, size=num_vals_per_variable)
        self.num_trading_days_vals = self.test_rng.integers(low=1, high=100, size=num_vals_per_variable)
        self.days_remaining_vals = self.test_rng.integers(low=0, high=180, size=num_vals_per_variable)
        self.spot_price_vals = np.maximum(1e-5, self.test_rng.normal(loc=1, scale=0.5, size=num_vals_per_variable))
        self.pool_apy_vals = np.maximum(1e-5, self.test_rng.normal(loc=0.2, scale=0.1, size=num_vals_per_variable))
        self.fee_percent_vals = self.test_rng.normal(loc=0.1, scale=0.01, size=num_vals_per_variable)

        self.config = Config(
            market=MarketConfig(), amm=AMMConfig(verbose=True), simulator=SimulatorConfig(user_policies=[])
        )
        self.pricing_models = [
            # ElementPricingModel(),
            HyperdrivePricingModel(),
        ]


class TestSimulator(BaseTest):
    """Simulator test class"""

    def test_simulator(self):
        """Tests the simulator output to verify that indices are correct"""
        self.setup_test_vars()
        simulator = YieldSimulator(self.config)

        for rng_index in range(1, 2):
            simulator.reset_rng(np.random.default_rng())
            simulator.set_random_variables()
            for pricing_model in self.pricing_models:
                simulator.run_simulation(
                    {
                        "pricing_model_name": pricing_model.model_name(),
                    }
                )

    def test_indexing(self):
        """Tests the simulator output to verify that indices are correct"""
        self.setup_test_vars()
        simulator = YieldSimulator(self.config)
        simulator.set_random_variables()

        for pricing_model in self.pricing_models:
            simulator.run_simulation(
                {
                    "pricing_model_name": pricing_model.model_name(),
                }
            )

            analysis_df = pd.DataFrame.from_dict(simulator.analysis_dict)
            init_day_list = []
            end_day_list = []
            for model in analysis_df.model_name.unique():
                model_df = analysis_df.loc[analysis_df.model_name == model]
                init_day = model_df.day.iloc[0]
                end_day = model_df.day.iloc[-1]
                init_day_list.append(init_day)
                end_day_list.append(end_day)
                num_vals_eq_to_first = init_day_list.count(init_day_list[0])
                total_num = len(init_day_list)
                assert (
                    num_vals_eq_to_first == total_num
                ), f"Error: All init day values should be the same but are {init_day_list}"
                num_vals_eq_to_first = end_day_list.count(end_day_list[0])
                total_num = len(end_day_list)
                assert (
                    num_vals_eq_to_first == total_num
                ), f"Error: All end day values should be the same but are {end_day_list}"

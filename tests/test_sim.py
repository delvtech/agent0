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

from elfpy.simulators import YieldSimulator
from elfpy.pricing_models import ElementPricingModel, YieldSpacev2PricingModel
from elfpy.markets import Market


class BaseTest(unittest.TestCase):
    """Generic test class"""

    def setup_test_vars(self):
        """Assigns member variables that are useful for many tests"""
        # fixed variables
        random_seed = 123
        simulator_rng = np.random.default_rng(random_seed)
        self.config = {
            "min_fee": 0.1,  # decimal that assigns fee_percent
            "max_fee": 0.5,  # decimal that assigns fee_percent
            "min_target_liquidity": 1e6,  # in USD
            "max_target_liquidity": 10e6,  # in USD
            "min_target_volume": 0.001,  # fraction of pool liquidity
            "max_target_volume": 0.01,  # fration of pool liquidity
            "min_pool_apy": 0.02,  # as a decimal
            "max_pool_apy": 0.9,  # as a decimal
            "min_vault_age": 0,  # fraction of a year
            "max_vault_age": 1,  # fraction of a year
            "min_vault_apy": 0.001,  # as a decimal
            "max_vault_apy": 0.9,  # as a decimal
            "base_asset_price": 2.5e3,  # aka market price
            "pool_duration": 180,  # in days
            "num_trading_days": 180,  # should be <= pool_duration
            "floor_fee": 0,  # minimum fee percentage (bps)
            "tokens": ["base", "fyt"],
            "trade_direction": "out",
            "precision": None,
            "pricing_model_name": "Element",
            "rng": simulator_rng,
            "verbose": False,
        }

        self.pricing_models = [
            ElementPricingModel(verbose=self.config["verbose"]),
            YieldSpacev2PricingModel(verbose=self.config["verbose"]),
        ]
        # random variables for fuzzy testing
        num_vals_per_variable = 4
        self.test_rng = np.random.default_rng(random_seed)
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


class TestSimulator(BaseTest):
    """Simulator test class"""

    def test_simulator(self):
        """Tests the simulator output to verify that indices are correct"""
        self.setup_test_vars()
        simulator = YieldSimulator(**self.config)
        for rng_index in range(1, 15):
            simulator.reset_rng(np.random.default_rng(rng_index))  # reset random inits
            simulator.set_random_variables()
            for pricing_model in self.pricing_models:
                override_dict = {
                    "pricing_model_name": pricing_model.model_name(),
                }
                # Running the simulation will include asserts that can fail
                simulator.run_simulation(override_dict)

    def test_get_days_remaining(self):
        """Tests the simulator function for getting the number of days remaining in a pool"""
        self.setup_test_vars()
        simulator = YieldSimulator(**self.config)
        simulator.set_random_variables()
        for num_trading_days in self.num_trading_days_vals:
            override_dict = {"num_trading_days": num_trading_days}
            simulator.setup_pricing_and_market(override_dict)
            for day in range(num_trading_days):
                days_remaining = simulator.get_days_remaining()
                test_days_remaining = self.config["pool_duration"] - day
                np.testing.assert_allclose(days_remaining, test_days_remaining)
                simulator.market.tick(simulator.step_size)

    def test_simulator_indexing(self):
        """Tests the simulator output to verify that indices are correct"""
        self.setup_test_vars()
        simulator = YieldSimulator(**self.config)
        simulator.set_random_variables()
        for pricing_model in self.pricing_models:
            override_dict = {
                "pricing_model_name": pricing_model.model_name(),
            }
            simulator.run_simulation(override_dict)
        analysis_df = pd.DataFrame.from_dict(simulator.analysis_dict)
        init_day_list = []
        end_day_list = []
        for model in analysis_df.model_name.unique():
            model_df = analysis_df.loc[analysis_df.model_name == model]
            init_day = model_df.day.iloc[0]
            end_day = model_df.day.iloc[-1]
            init_day_list.append(init_day)
            end_day_list.append(end_day)
        # check that all values in the lists are equal across models
        num_vals_eq_to_first = init_day_list.count(init_day_list[0])
        total_num = len(init_day_list)
        assert (
            num_vals_eq_to_first == total_num
        ), f"Error: All init day values should be the same but are {init_day_list}"
        num_vals_eq_to_first = end_day_list.count(end_day_list[0])
        total_num = len(end_day_list)
        assert num_vals_eq_to_first == total_num, f"Error: All end day values should be the same but are {end_day_list}"


class TestPricingModels(BaseTest):
    """Pricing Model test class"""

    def test_pool_length_normalization(self):
        """
        Tests time conversions

        Convert pool length specified in days to a normalized and stretched time value
        and then back.
        """
        self.setup_test_vars()
        for normalizing_constant, time_stretch, days_remaining, pricing_model, in itertools.product(
            self.normalizing_constant_vals,
            self.time_stretch_vals,
            self.days_remaining_vals,
            self.pricing_models,
        ):
            time_remaining = pricing_model.days_to_time_remaining(days_remaining, time_stretch, normalizing_constant)
            new_days_remaining = pricing_model.time_to_days_remaining(
                time_remaining, time_stretch, normalizing_constant
            )
            np.testing.assert_allclose(days_remaining, new_days_remaining)

    def test_calc_spot_price_from_apy(self):
        """Tests spot price by converting to and from an APY."""
        self.setup_test_vars()
        for random_spot_price, days_remaining, pricing_model in itertools.product(
            self.spot_price_vals, self.days_remaining_vals, self.pricing_models
        ):
            normalized_days_remaining = days_remaining / 365
            apy = pricing_model.calc_apy_from_spot_price(random_spot_price, normalized_days_remaining)
            calculated_spot_price = pricing_model.calc_spot_price_from_apy(apy, normalized_days_remaining)
            np.testing.assert_allclose(random_spot_price, calculated_spot_price)

    # TODO: def test_calc_spot_price_from_reserves(self):
    # TODO: def test_calc_apy_from_reserves(self):

    def test_calc_liquidity_total_supply(self):
        """Ensures that the total supply value returned from
        calc_liquidity matches the expected amount passed as the target_liquidity argument.
        """
        self.setup_test_vars()
        for (
            random_apy,
            days_remaining,
            target_liquidity,
            base_asset_price,
            init_share_price,
            pricing_model,
        ) in itertools.product(
            self.pool_apy_vals,
            self.days_remaining_vals,
            self.target_liquidity_vals,
            self.base_asset_price_vals,
            self.init_share_price_vals,
            self.pricing_models,
        ):
            time_stretch = pricing_model.calc_time_stretch(random_apy)
            calculated_total_liquidity_eth = pricing_model.calc_liquidity(
                target_liquidity,
                base_asset_price,
                random_apy,
                days_remaining,
                time_stretch,
                init_share_price,
                init_share_price,
            )[2]
            calculated_total_liquidity_usd = calculated_total_liquidity_eth * base_asset_price
            np.testing.assert_allclose(target_liquidity, calculated_total_liquidity_usd)

    def test_calc_liquidity_given_spot_price(self):
        """Tests the calc_liquidity function, assuming that spot_price calculation functions are working."""
        self.setup_test_vars()
        for (
            random_apy,
            days_remaining,
            target_liquidity,
            base_asset_price,
            init_share_price,
            pricing_model,
        ) in itertools.product(
            self.pool_apy_vals,
            self.days_remaining_vals,
            self.target_liquidity_vals,
            self.base_asset_price_vals,
            self.init_share_price_vals,
            self.pricing_models,
        ):
            # Version 1
            time_stretch = pricing_model.calc_time_stretch(random_apy)
            reserves = pricing_model.calc_liquidity(
                target_liquidity,
                base_asset_price,
                random_apy,
                days_remaining,
                time_stretch,
                init_share_price,
                init_share_price,
            )
            base_asset_reserves, token_asset_reserves = reserves[:2]
            time_remaining = pricing_model.days_to_time_remaining(days_remaining, time_stretch)
            total_reserves = base_asset_reserves + token_asset_reserves
            spot_price_from_reserves = pricing_model.calc_spot_price_from_reserves(
                base_asset_reserves,
                token_asset_reserves,
                total_reserves,
                time_remaining,
                init_share_price,
                init_share_price,
            )
            # Version 2
            normalized_days_remaining = days_remaining / 365
            spot_price_from_apy = pricing_model.calc_spot_price_from_apy(random_apy, normalized_days_remaining)
            # Test version 1 output == version 2 output
            np.testing.assert_allclose(spot_price_from_reserves, spot_price_from_apy)

    def test_calc_apy_from_reserves_given_calc_liquidity(self):
        """Tests the calc_apy_from_reserves function, assuming that calc_liquidity is working."""
        self.setup_test_vars()
        for (
            random_apy,
            days_remaining,
            target_liquidity,
            base_asset_price,
            init_share_price,
            pricing_model,
        ) in itertools.product(
            self.pool_apy_vals,
            self.days_remaining_vals,
            self.target_liquidity_vals,
            self.base_asset_price_vals,
            self.init_share_price_vals,
            self.pricing_models,
        ):
            time_stretch = pricing_model.calc_time_stretch(random_apy)
            reserves = pricing_model.calc_liquidity(
                target_liquidity,
                base_asset_price,
                random_apy,
                days_remaining,
                time_stretch,
                init_share_price,
                init_share_price,
            )
            base_asset_reserves, token_asset_reserves = reserves[:2]
            total_reserves = base_asset_reserves + token_asset_reserves
            time_remaining = pricing_model.days_to_time_remaining(days_remaining, time_stretch)
            calculated_apy = pricing_model.calc_apy_from_reserves(
                base_asset_reserves,
                token_asset_reserves,
                total_reserves,
                time_remaining,
                time_stretch,
                init_share_price,
                init_share_price,
            )
            np.testing.assert_allclose(random_apy, calculated_apy)


class TestMarkets(BaseTest):
    """Market test class"""

    def test_market_apy_given_calc_apy_from_reserves(self):
        """Test the Market class apy calculation matches that from PricingModel.calc_apy_from_reserves"""
        self.setup_test_vars()
        for (
            random_apy,
            days_remaining,
            target_liquidity,
            base_asset_price,
            init_share_price,
            fee_percent,
            pricing_model,
        ) in itertools.product(
            self.pool_apy_vals,
            self.days_remaining_vals,
            self.target_liquidity_vals,
            self.base_asset_price_vals,
            self.init_share_price_vals,
            self.fee_percent_vals,
            self.pricing_models,
        ):
            time_stretch = pricing_model.calc_time_stretch(random_apy)
            reserves = pricing_model.calc_liquidity(
                target_liquidity,
                base_asset_price,
                random_apy,
                days_remaining,
                time_stretch,
                init_share_price,
                init_share_price,
            )
            base_asset_reserves, token_asset_reserves = reserves[:2]
            total_reserves = base_asset_reserves + token_asset_reserves
            time_remaining = pricing_model.days_to_time_remaining(days_remaining, time_stretch)
            calculated_apy = pricing_model.calc_apy_from_reserves(
                base_asset_reserves,
                token_asset_reserves,
                total_reserves,
                time_remaining,
                time_stretch,
                init_share_price,
                init_share_price,
            )
            market = Market(
                base_asset=base_asset_reserves,  # x
                token_asset=token_asset_reserves,  # y
                fee_percent=fee_percent,  # g
                time_remaining=time_remaining,  # t
                pricing_model=pricing_model,
                init_share_price=init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
                share_price=init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
                verbose=True,
            )
            sim_days_remaining = pricing_model.time_to_days_remaining(market.time_remaining, time_stretch)
            market_apy = market.apy(sim_days_remaining)
            np.testing.assert_allclose(calculated_apy, market_apy)

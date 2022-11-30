"""
Testing for the parsing of the Market, AMM and Simulator configs from a TOML file
"""

# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init

from typing import Union

from dataclasses import dataclass, fields, MISSING
import unittest
import numpy as np

from elfpy.utils import parse_config as config_utils
from elfpy.pricing_models import ElementPricingModel, HyperdrivePricingModel

class TestParseSimulationConfig(unittest.TestCase):
    """Unit tests for the parse_simulation_config function"""

    def test_parse_simulation_config(self):
        """Test for parse_simulation_config"""

        config = config_utils.parse_simulation_config("./tests/utils/test_parse_config_success_data.toml")

        # manually set Market config to be the same as the TOML file
        market = config_utils.MarketConfig(
            min_target_liquidity=1000000.0, 
            max_target_liquidity=10000000.0, 
            min_target_volume=0.001, 
            max_target_volume=0.01, 
            min_vault_age=0, 
            max_vault_age=1, 
            min_vault_apy=0.001, 
            max_vault_apy=0.9, 
            base_asset_price=2500.0
            )

        # manually set AMM config to be the same as the TOML file
        amm = config_utils.AMMConfig(
            min_fee=0.1,
            max_fee=0.5,
            min_pool_apy=0.02,
            max_pool_apy=0.9,
            floor_fee=0
            )

        # manually set Simulator config to be the same as the TOML file
        simulator = config_utils.SimulatorConfig(
            pool_duration=180,
            num_trading_days=180,
            num_blocks_per_day=7200,
            token_duration=180,
            precision=64,
            pricing_model_name='Element',
            user_policies=['single_long'],
            random_seed=123,
            verbose=False
            )

        assert (market == config.market), "Loaded Market TOML data doesn't match the hardcoded data"
        assert (amm == config.amm), "Loaded AMM TOML data doesn't match the hardcoded data"
        assert (simulator == config.simulator), "Loaded Simulator TOML data doesn't match the hardcoded data"
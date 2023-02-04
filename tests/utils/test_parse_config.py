"""Testing for the parsing of the Market, AMM and Simulator configs from a TOML file"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest

from elfpy.utils import parse_config as config_utils


class TestParseSimulationConfig(unittest.TestCase):
    """Unit tests for the parse_simulation_config function"""

    def test_parse_simulation_config(self):
        """Test for parse_simulation_config"""
        config = config_utils.load_and_parse_config_file("./tests/utils/test_parse_config_success_data.toml")
        # manually set Market config to be the same as the TOML file
        market = config_utils.MarketConfig(
            min_target_liquidity=1000000.0,
            max_target_liquidity=10000000.0,
            min_vault_age=0,
            max_vault_age=1,
            vault_apr={"type": "constant", "value": 0.05},
            base_asset_price=2500.0,
        )
        # manually set AMM config to be the same as the TOML file
        amm = config_utils.AMMConfig(
            pricing_model_name="Hyperdrive", min_fee=0.1, max_fee=0.5, min_pool_apr=0.02, max_pool_apr=0.9, floor_fee=0
        )
        # manually set Simulator config to be the same as the TOML file
        simulator = config_utils.SimulatorConfig(
            num_trading_days=180,
            num_blocks_per_day=7200,
            token_duration=180,
            agent_policies=["single_long"],
            shuffle_users=True,
            init_lp=True,
            compound_vault_apr=True,
            random_seed=123,
            precision=64,
            logging_level="warning",
        )
        assert market == config.market, "Loaded Market TOML data doesn't match the hardcoded data"
        assert amm == config.amm, "Loaded AMM TOML data doesn't match the hardcoded data"
        assert simulator == config.simulator, "Loaded Simulator TOML data doesn't match the hardcoded data"

    def test_load_config(self):
        """Verify that config loading returns a proper dictionary, and that both can be loaded"""
        config_file = "./tests/utils/test_parse_config_success_data.toml"
        config_dict = {
            "title": "example simulation config",
            "market": {
                "min_target_liquidity": 1000000.0,
                "max_target_liquidity": 10000000.0,
                "min_vault_age": 0,
                "max_vault_age": 1,
                "vault_apr": {"type": "constant", "value": 0.05},
                "base_asset_price": 2500.0,
            },
            "amm": {
                "pricing_model_name": "Hyperdrive",
                "min_fee": 0.1,
                "max_fee": 0.5,
                "min_pool_apr": 0.02,
                "max_pool_apr": 0.9,
                "floor_fee": 0,
            },
            "simulator": {
                "num_trading_days": 180,
                "num_blocks_per_day": 7200,
                "token_duration": 180,
                "agent_policies": ["single_long"],
                "random_seed": 123,
                "shuffle_users": True,
                "init_lp": True,
                "compound_vault_apr": True,
                "precision": 64,
                "logging_level": "warning",
            },
        }
        # check that the loaded config looks like the dictionary
        loaded_config = config_utils.load_config_file(config_file)
        assert loaded_config == config_dict
        # check that parsing a file or a dictionary results in the same config
        config_from_file = config_utils.load_and_parse_config_file(config_file)
        config_from_dict = config_utils.parse_simulation_config(config_dict)
        assert config_from_file == config_from_dict

    def test_text_to_logging_level(self):
        """Test that logging level strings result in the correct integera amounts"""
        # change up case to test .lower()
        logging_levels = ["notset", "debug", "info", "Warning", "Error", "CRITICAL"]
        logging_constants = [0, 10, 20, 30, 40, 50]
        for level_str, level_int in zip(logging_levels, logging_constants):
            func_level = config_utils.text_to_logging_level(level_str)
            assert level_int == func_level

    def test_override_config_variables(self):
        """Make sure that the override dict changes config variables, while leaving the others unchanged"""
        config_file = "./tests/utils/test_parse_config_success_data.toml"
        loaded_config = config_utils.load_and_parse_config_file(config_file)
        override_dict = {"num_trading_days": 10}
        new_config = config_utils.override_config_variables(loaded_config, override_dict)
        for config_type in ["market", "simulator", "amm"]:
            for key, value in override_dict.items():
                if key in new_config[config_type].__dict__:
                    assert new_config[config_type][key] == value
        assert loaded_config != new_config

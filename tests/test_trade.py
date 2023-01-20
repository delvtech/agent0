"""
Testing for the ElfPy package modules
"""

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals
# pylint: disable=attribute-defined-outside-init
# pylint: disable=duplicate-code

import unittest
import logging
import numpy as np

import utils_for_tests as test_utils
import elfpy.utils.outputs as output_utils


class BaseTradeTest(unittest.TestCase):
    """Generic Trade Test class"""

    # pylint: disable=too-many-arguments
    # because we're testing lots of stuff here!
    def run_base_trade_test(
        self,
        agent_policies,
        config_file="config/example_config.toml",
        delete_logs=True,
        additional_overrides=None,
        target_liquidity=None,
        target_pool_apr=None,
    ):
        """Assigns member variables that are useful for many tests"""
        output_utils.setup_logging(log_filename=".logging/test_trades.log", log_level=logging.DEBUG)
        # load default config
        override_dict = {
            "pricing_model_name": "Yieldspace",
            "target_liquidity": 10e6 if not target_liquidity else target_liquidity,
            "fee_percent": 0.1,
            "target_pool_apr": 0.05 if not target_pool_apr else target_pool_apr,
            "vault_apr": {"type": "constant", "value": 0.05},
            "num_trading_days": 3,  # sim 3 days to keep it fast for testing
            "num_blocks_per_day": 3,  # 3 block a day, keep it fast for testing
        }
        if additional_overrides:
            override_dict.update(additional_overrides)
        simulator = test_utils.setup_simulation_entities(
            config_file=config_file, override_dict=override_dict, agent_policies=agent_policies
        )
        if target_pool_apr:  # check that apr is within 0.005 of the target
            market_apr = simulator.market.rate
            assert np.allclose(market_apr, target_pool_apr, atol=0.005), (
                f"test_trade.run_base_lp_test: ERROR: {target_pool_apr=} does not equal {market_apr=}"
                f"with error of {(np.abs(market_apr - target_pool_apr)/target_pool_apr)=}"
            )
        if target_liquidity:  # check that the liquidity is within 0.001 of the target
            # TODO: This will not work with Hyperdrive PM
            total_liquidity = simulator.market.market_state.share_reserves * simulator.market.market_state.share_price
            assert np.allclose(total_liquidity, target_liquidity, atol=0.001), (
                f"test_trade.run_base_lp_test: ERROR: {target_liquidity=} does not equal {total_liquidity=} "
                f"with error of {(np.abs(total_liquidity - target_liquidity)/target_liquidity)=}."
            )
        simulator.run_simulation()
        output_utils.close_logging(delete_logs=delete_logs)
        return simulator


class SingleTradeTests(BaseTradeTest):
    """
    Tests for the SingeLong policy
    TODO: In a followup PR, loop over pricing model types & rerun tests
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def test_init_only(self):
        """Tests base LP setups"""
        self.run_base_trade_test(agent_policies=[], target_liquidity=1e6, target_pool_apr=0.05)

    def test_single_long(self):
        """Tests the BaseUser class"""
        self.run_base_trade_test(agent_policies=["single_long"])

    def test_single_short(self):
        """Tests the BaseUser class"""
        self.run_base_trade_test(agent_policies=["single_short"])

    def test_base_lps(self):
        """Tests base LP setups"""
        self.run_base_trade_test(agent_policies=["single_lp"], target_liquidity=1e6, target_pool_apr=0.05)

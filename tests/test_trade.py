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
import utils_for_tests as test_utils  # utilities for testing

import elfpy.utils.outputs as output_utils  # utilities for file outputs
from elfpy.types import MarketState
from elfpy.markets import Market


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
        init_only=False,
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
            assert np.allclose(market_apr, target_pool_apr, atol=0, rtol=1e-14), (
                f"test_trade.run_base_lp_test: ERROR: {target_pool_apr=} does not equal {market_apr=}"
                f"with error of {(np.abs(market_apr - target_pool_apr)/target_pool_apr)=}"
            )
        if target_liquidity:  # check that the liquidity is within 0.001 of the target
            # TODO: This will not work with Hyperdrive PM
            total_liquidity = simulator.market.market_state.share_reserves * simulator.market.market_state.share_price
            # use rtol here because liquidity can be set to any magnitude
            assert np.allclose(total_liquidity, target_liquidity, atol=0, rtol=1e-14), (
                f"test_trade.run_base_lp_test: ERROR: {target_liquidity=} does not equal {total_liquidity=} "
                f"with error of {(np.abs(total_liquidity - target_liquidity)/target_liquidity)=}."
            )
        if not init_only:
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

    def test_compare_agent_to_calc_liquidity(self):
        """Compare agent init as above to old calc_liquidity method"""
        target_liquidity = 1e6
        target_pool_apr = 0.05
        simulator = self.run_base_trade_test(
            agent_policies=[], target_liquidity=target_liquidity, target_pool_apr=target_pool_apr, init_only=True
        )
        # assign the results of the init_lp agent to explicit variables
        share_reserves_new = simulator.market.market_state.share_reserves
        share_reserves_old, bond_reserves_old = simulator.market.pricing_model.calc_liquidity(
            market_state=simulator.market.market_state,  # used only for share_price and init_share_price
            target_liquidity=target_liquidity,
            target_apr=target_pool_apr,
            position_duration=simulator.market.position_duration,
        )
        market_old = Market(
            pricing_model=simulator.market.pricing_model,
            market_state=MarketState(
                share_reserves=share_reserves_old,
                bond_reserves=bond_reserves_old,
                base_buffer=simulator.market.market_state.base_buffer,
                bond_buffer=simulator.market.market_state.bond_buffer,
                lp_reserves=simulator.market.market_state.lp_reserves,
                vault_apr=simulator.market.market_state.vault_apr,
                share_price=simulator.market.market_state.share_price,
                init_share_price=simulator.market.market_state.init_share_price,
            ),
            position_duration=simulator.market.position_duration,
        )
        total_liquidity_old = market_old.pricing_model.calc_total_liquidity_from_reserves_and_price(
            market_state=market_old.market_state, share_price=market_old.market_state.share_price
        )
        calc_apr = market_old.rate
        # total liquidity check
        total_liquidity_new = share_reserves_new * simulator.market.market_state.share_price
        print(f"{total_liquidity_old=} and {total_liquidity_new=}")
        atol = 1
        assert np.allclose(total_liquidity_old, total_liquidity_new, atol=atol, rtol=1e-05), (
            f"test_trade.test_compare_agent_to_calc_liquidity: ERROR: {total_liquidity_old=}"
            f"does not equal {total_liquidity_new=} "
            f"off by {(np.abs(total_liquidity_old - total_liquidity_new))=}."
        )
        # apr check
        print(f"{calc_apr=} and {simulator.market.rate=}")
        assert np.allclose(calc_apr, simulator.market.rate, atol=1e-20), (
            f"test_trade.test_compare_agent_to_calc_liquidity: ERROR: {calc_apr=}"
            f" does not equal {simulator.market.rate=}"
            f"off by {(np.abs(calc_apr - simulator.market.rate))=}."
        )

    def test_single_long(self):
        """Tests the BaseUser class"""
        self.run_base_trade_test(agent_policies=["single_long"])

    def test_single_short(self):
        """Tests the BaseUser class"""
        self.run_base_trade_test(agent_policies=["single_short"])

    def test_base_lps(self):
        """Tests base LP setups"""
        self.run_base_trade_test(agent_policies=["single_lp"], target_liquidity=1e6, target_pool_apr=0.05)


if __name__ == "__main__":
    unittest.main()

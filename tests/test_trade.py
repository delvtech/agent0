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

    @staticmethod
    def setup_simulation_entities(config_file, override_dict, agent_policies) -> tuple[Simulator, Market]:
        """Construct and run the simulator"""
        # create config object
        config = config_utils.override_config_variables(
            config_utils.load_and_parse_config_file(config_file), override_dict
        )
        # instantiate rng object
        rng = np.random.default_rng(config.simulator.random_seed)
        # run random number generators to get random simulation arguments
        random_sim_vars = sim_utils.override_random_variables(
            sim_utils.get_random_variables(config, rng), override_dict
        )
        # instantiate the pricing model
        pricing_model = sim_utils.get_pricing_model(model_name=config.amm.pricing_model_name)
        # instantiate the market
        market = sim_utils.get_market(
            pricing_model,
            random_sim_vars.target_pool_apr,
            random_sim_vars.fee_percent,
            config.simulator.token_duration,
            random_sim_vars.vault_apr,
            random_sim_vars.init_share_price,
        )
        # instantiate the init_lp agent
        init_agents = {
            0: sim_utils.get_init_lp_agent(
                market,
                random_sim_vars.target_liquidity,
                random_sim_vars.target_pool_apr,
                random_sim_vars.fee_percent,
            )
        }
        # set up simulator with only the init_lp_agent
        simulator = Simulator(
            config=config,
            market=market,
            agents=init_agents.copy(),  # we use this variable later, so pass a copy ;)
            rng=rng,
            random_simulation_variables=random_sim_vars,
        )
        # initialize the market using the LP agent
        simulator.collect_and_execute_trades()
        # get trading agent list
        for agent_id, policy_instruction in enumerate(agent_policies):
            if ":" in policy_instruction:  # we have custom parameters
                policy_name, kwargs = BaseTradeTest.validate_custom_parameters(policy_instruction)
            else:  # we don't have custom parameters
                policy_name = policy_instruction
                kwargs = {}
            wallet_address = len(init_agents) + agent_id
            agent = import_module(f"elfpy.policies.{policy_name}").Policy(
                wallet_address=wallet_address,  # first policy goes to init_lp_agent
                **kwargs,
            )
            agent.log_status_report()
            simulator.agents.update({agent.wallet.address: agent})
        return (simulator, market)

    @staticmethod
    def validate_custom_parameters(policy_instruction):
        """
        separate the policy name from the policy arguments and validate the arguments
        """
        policy_name, policy_args = policy_instruction.split(":")
        try:
            policy_args = policy_args.split(",")
        except AttributeError as exception:
            logging.info("ERROR: No policy arguments provided")
            raise exception
        try:
            policy_args = [arg.split("=") for arg in policy_args]
        except AttributeError as exception:
            logging.info("ERROR: Policy arguments must be provided as key=value pairs")
            raise exception
        try:
            kwargs = {key: float(value) for key, value in policy_args}
        except ValueError as exception:
            logging.info("ERROR: Policy arguments must be provided as key=value pairs")
            raise exception
        return policy_name, kwargs

    @staticmethod
    def setup_logging(log_level=logging.DEBUG):
        """Setup test logging levels and handlers"""
        log_filename = ".logging/test_trades.log"
        output_utils.setup_logging(log_filename, log_level=log_level)

    @staticmethod
    def close_logging(delete_logs=True):
        """Close logging and handlers for the test"""
        logging.shutdown()
        if delete_logs:
            for handler in logging.getLogger().handlers:
                handler.close()
                if hasattr(handler, "baseFilename"):
                    if os.path.exists(handler.baseFilename):
                        os.remove(handler.baseFilename)

    # pylint: disable=too-many-arguments because we're testing lots of stuff here!
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
        simulator, market = self.setup_simulation_entities(
            config_file=config_file, override_dict=override_dict, agent_policies=agent_policies
        )
        if target_pool_apr:  # check that apr is within 0.005 of the target
            market_apr = market.rate
            assert np.allclose(market_apr, target_pool_apr, atol=0.005), (
                f"test_trade.run_base_lp_test: ERROR: {target_pool_apr=} does not equal {market_apr=}"
                f"with error of {(np.abs(market_apr - target_pool_apr)/target_pool_apr)=}"
            )
        if target_liquidity:  # check that the liquidity is within 0.001 of the target
            # TODO: This will not work with Hyperdrive PM
            total_liquidity = market.market_state.share_reserves * market.market_state.share_price
            assert np.allclose(total_liquidity, target_liquidity, atol=0.001), (
                f"test_trade.run_base_lp_test: ERROR: {target_liquidity=} does not equal {total_liquidity=} "
                f"with error of {(np.abs(total_liquidity - target_liquidity)/target_liquidity)=}."
            )
        simulator.run_simulation()
        self.close_logging(delete_logs=delete_logs)
        return simulator

    def run_custom_parameters_test(self, agent_policies, expected_result, delete_logs=True):
        """Test custom parameters passed to agent creation"""
        # create simulator with agent_policies
        simulator = self.run_base_trade_test(agent_policies=agent_policies, delete_logs=False)
        number_of_init_agents = 0  # count number of init agents so we can skip over them
        for all_agent_index, agent in simulator.agents.items():  # loop over all agents
            if agent.name == "init_lp":
                number_of_init_agents += 1
            else:  # only for custom agents, loop across them and check their parameters
                custom_agent_index = all_agent_index - number_of_init_agents  # identify which custom agent we are on
                expected_result_dict = expected_result[custom_agent_index]
                for key, value in expected_result_dict.items():  # for each custom parameter to check
                    np.testing.assert_almost_equal(
                        getattr(agent, key),
                        value,
                        err_msg=f"{key} does not equal {value}",
                    )
        self.close_logging(delete_logs=delete_logs)


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

    def test_custom_parameters(self):
        """Tests passing custom parameters"""
        list_of_agent_policies_that_pass = [["single_lp:amount_to_lp=200", "single_short:pt_to_short=500"]]
        list_of_agent_policies_that_fail = [
            ["single_lp:amount_to_lp=200", "single_short:pt_to_short=499"],
            ["single_lp:amount_to_lp=200", "single_short:pt_to_short=501"],
            ["single_lp:amount_to_lp=199", "single_short:pt_to_short=500"],
            ["single_lp:amount_to_lp=201", "single_short:pt_to_short=500"],
        ]
        expected_result = [{"amount_to_lp": 200}, {"pt_to_short": 500}]
        for agent_policies in list_of_agent_policies_that_pass:
            self.run_custom_parameters_test(agent_policies=agent_policies, expected_result=expected_result)
        for agent_policies in list_of_agent_policies_that_fail:
            with self.assertRaises(AssertionError):
                self.run_custom_parameters_test(agent_policies=agent_policies, expected_result=expected_result)


if __name__ == "__main__":
    unittest.main()

""" Implements functions that are useful for testing """

# pylint: disable=too-many-locals

import logging
from importlib import import_module

import numpy as np

from elfpy.markets import Market
from elfpy.simulators import Simulator
from elfpy.utils import sim_utils
import elfpy.utils.parse_config as config_utils


@staticmethod
def setup_simulation_entities(config_file, override_dict, agent_policies) -> tuple[Simulator, Market]:
    """Construct and run the simulator"""
    # create config object
    config = config_utils.override_config_variables(config_utils.load_and_parse_config_file(config_file), override_dict)
    # instantiate rng object
    rng = np.random.default_rng(config.simulator.random_seed)
    # run random number generators to get random simulation arguments
    random_sim_vars = sim_utils.override_random_variables(sim_utils.get_random_variables(config, rng), override_dict)
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
            policy_name, not_kwargs = validate_custom_parameters(policy_instruction)
        else:  # we don't have custom parameters
            policy_name = policy_instruction
            not_kwargs = {}
        wallet_address = len(init_agents) + agent_id
        agent = import_module(f"elfpy.policies.{policy_name}").Policy(
            wallet_address=wallet_address,  # first policy goes to init_lp_agent
        )
        for key, value in not_kwargs.items():
            setattr(agent, key, value)
        agent.log_status_report()
        simulator.agents.update({agent.wallet.address: agent})
    return simulator


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

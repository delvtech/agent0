""" Implements functions that are useful for testing """
# TODO: review these helper functions for inclusion into the package under src/elfpy/utils
# left to be reviewed when we add new examples that will live inside the package
# if those examples use these functions, then we should move them into the package

# pylint: disable=too-many-locals
# pylint: disable=duplicate-code

import logging
from importlib import import_module
import numpy as np

from elfpy.simulators import Simulator
from elfpy.utils import sim_utils
import elfpy.utils.parse_config as config_utils


def float_to_string(value, precision=3, min_digits=0, debug=False):
    """
    Format a float to a string with a given precision
    this follows the significant figure behavior, irrepective of number size
    """
    # TODO: Include more specific error handling in the except statement
    # pylint: disable=broad-except
    if debug:
        print(f"value: {value}, type: {type(value)}, precision: {precision}, min_digits: {min_digits}")
    if np.isinf(value):
        return "inf"
    if np.isnan(value):
        return "nan"
    if value == 0:
        return "0"
    try:
        digits = int(np.floor(np.log10(abs(value)))) + 1  #  calculate number of digits in value
    except Exception as err:
        if debug:
            print(
                f"Error in float_to_string: value={value}({type(value)}), precision={precision},"
                f" min_digits={min_digits}, \n error={err}"
            )
        return str(value)
    # decimals = np.clip(precision - digits, 0, precision)
    decimals = min(max(precision - digits, min_digits), precision)  #  calculate desired decimals
    if debug:
        print(f"value: {value}, type: {type(value)} calculated digits: {digits}, decimals: {decimals}")
    if abs(value) > 0.1:
        string = f"{value:,.{decimals}f}"
    else:  # add an additional sigfig if the value is really small
        string = f"{value:0.{precision-1}e}"
    return string


@staticmethod
def setup_simulation_entities(config_file, override_dict, agent_policies) -> Simulator:
    """Construct and run the simulator"""
    # Instantiate the config.
    config = config_utils.override_config_variables(config_utils.load_and_parse_config_file(config_file), override_dict)
    random_sim_vars = sim_utils.override_random_variables(sim_utils.get_random_variables(config), override_dict)

    # Create the agents.
    agents = []
    for agent_id, policy_instruction in enumerate(agent_policies):
        if ":" in policy_instruction:  # we have custom parameters
            policy_name, not_kwargs = validate_custom_parameters(policy_instruction)
        else:  # we don't have custom parameters
            policy_name = policy_instruction
            not_kwargs = {}
        wallet_address = agent_id + 1
        agent = import_module(f"elfpy.policies.{policy_name}").Policy(
            wallet_address=wallet_address,  # first policy goes to init_lp_agent
        )
        for key, value in not_kwargs.items():
            if hasattr(agent, key):  # check if parameter exists
                setattr(agent, key, value)
            else:
                raise AttributeError(f"Policy {policy_name} does not have parameter {key}")
        agent.log_status_report()
        agents += [agent]

    # Initialize the simulator.
    simulator = sim_utils.get_simulator(config, agents, random_sim_vars)

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

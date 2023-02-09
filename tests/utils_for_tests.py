""" Implements functions that are useful for testing """
from __future__ import annotations  # types are strings by default in 3.11

import logging
from importlib import import_module

from elfpy.simulators import Simulator
from elfpy.utils import sim_utils


# TODO: review these helper functions for inclusion into the package under src/elfpy/utils
# left to be reviewed when we add new examples that will live inside the package
# if those examples use these functions, then we should move them into the package


def setup_simulation_entities(config, agent_policies) -> Simulator:
    """Construct and run the simulator"""
    # Create the agents.
    print(f"{agent_policies=}")
    print(f"{len(agent_policies)=}")
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
    simulator = sim_utils.get_simulator(config, agents)  # initialize the simulator
    return simulator


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

import logging
import os

import numpy as np

from elfpy.agents import Agent
from elfpy.agents.load_agent_policies import load_builtin_policies, parse_folder_for_classes, get_invoked_path
from elfpy.eth.accounts.eth_account import EthAccount
from elfpy.utils import logs

from .bot_config import bot_config

def run_main():

    # setup config
    config = bot_config
    rng = np.random.default_rng(config.random_seed)

    # setup logging
    logs.setup_logging(
        log_filename=config.log_filename,
        max_bytes=config.max_bytes,
        log_level=config.log_level,
        delete_previous_logs=config.delete_previous_logs,
        log_stdout=config.log_stdout,
        log_format_string=config.log_formatter,
    )
    

    # setup agents # FIXME: move this out of main
    # load agent policies
    all_policies = load_builtin_policies()
    custom_policies_path = os.path.join(get_invoked_path(), "custom_policies")
    all_policies.update(parse_folder_for_classes(custom_policies_path))
    # make a list of agents
    agents: dict[str, tuple[EthAccount, Agent]] = {}
    num_agents_so_far = []
    for agent_info in config.agents:
        kwargs = agent_info.init_kwargs
        kwargs["rng"] = rng
        kwargs["budget"] = agent_info.budget.sample_budget(rng)
        for policy_instance_index in range(agent_info.number_of_bots):
            agent_count = policy_instance_index + sum(num_agents_so_far)
            policy = all_policies[agent_info.name](**kwargs)
            agent = Agent(wallet_address=eth_account.checksum_address, policy=policy)
            eth_account = EthAccount(extra_entropy=str(agent_count))
            agents[f"agent_{eth_account.checksum_address}"] = (eth_account, agent)
        num_agents_so_far.append(agent_info.number_of_bots)


    # x point to chain env
    # x setup base contract interface
    # x setup initialize (LP) agent
    # - setup hyperdrive contract interface (initialize)
    # - setup other agents (assign addresses, add funds from base)
    # run_trade_loop()

def run_trade_loop():
    # loop forever
        try:
            for agent in agents:
                # do trades
        except:
            # deliver crash report
            # raise err if config.fail else continue

if __name__ == "__main__":
    run_main()
import os

import numpy as np

from elfpy.agents.load_agent_policies import load_builtin_policies, parse_folder_for_classes, get_invoked_path
from elfpy.eth.accounts.eth_account import EthAccount

from .bot_config import bot_config

def run_main():

    # get configs
    config = bot_config

    rng = np.random.default_rng(config.random_seed)


    # get agent objects # FIXME: move this out of main
    # get dev accounts
    dev_accounts = 
    all_agents = load_builtin_policies()
    custom_policies_path = os.path.join(get_invoked_path(), "custom_policies")
    all_agents.update(parse_folder_for_classes(custom_policies_path))

    agents = []
    for agent_info in config.agents:
        kwargs = agent_info.init_kwargs
        kwargs["rng"] = rng
        kwargs["budget"] = agent_info.budget.sample_budget(rng)
        for agent_number in range(agent_info.number_of_bots):
            agent_policy = all_agents[agent_info.name](**kwargs)
            #agent


    # setup logging
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
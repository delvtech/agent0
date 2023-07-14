import os

import numpy as np

from elfpy.agents import Agent
from elfpy.agents.load_agent_policies import load_builtin_policies, parse_folder_for_classes, get_invoked_path
from elfpy.eth.accounts.eth_account import EthAccount

from .bot_config import bot_config

def run_main():

    # setup config
    config = bot_config
    rng = np.random.default_rng(config.random_seed)

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


# %%
counter = 0
outer_size = 3
inner_size = 4
for outer_index in range(outer_size):
    for inner_index in range(inner_size):
        print(counter)
        counter += 1
# %%
outer_size = 3
inner_size = 4
for outer_index in range(outer_size):
    for inner_index in range(inner_size):
        counter = inner_index + (inner_size) * outer_index
        print(counter)

# %%
outer_size = 3
inner_size = [4, 4, 4]
for outer_index in range(outer_size):
    for inner_index in range(inner_size[outer_index]):
        counter = inner_index + sum(inner_size[:outer_index])
        print(counter)
# %%
outer_size = 3
inner_size = [4, 4, 4]
inner_sizes_so_far = []
for outer_index in range(outer_size):
    for inner_index in range(inner_size[outer_index]):
        counter = inner_index + sum(inner_sizes_so_far)
        print(counter)
    inner_sizes_so_far.append(inner_size[outer_index])
# %%
print(f"{inner_sizes_so_far=}")

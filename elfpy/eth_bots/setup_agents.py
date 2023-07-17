"""Script for loading ETH & Elfpy agents with trading policies"""
from __future__ import annotations

import logging
import os

from numpy.random._generator import Generator as NumpyGenerator
from web3 import Web3
from web3.contract.contract import Contract

from elfpy import eth
from elfpy.agents import Agent
from elfpy.agents.load_agent_policies import get_invoked_path, load_builtin_policies, parse_folder_for_classes

from .bot_config import BotConfig


def get_agents(
    config: BotConfig, web3: Web3, base_token_contract: Contract, rng: NumpyGenerator
) -> dict[str, tuple[eth.accounts.EthAccount, Agent]]:
    """Get agents according to provided config"""
    all_policies = load_builtin_policies()
    custom_policies_path = os.path.join(get_invoked_path(), "custom_policies")
    all_policies.update(parse_folder_for_classes(custom_policies_path))
    # make a list of agents
    agents: dict[str, tuple[eth.accounts.EthAccount, Agent]] = {}
    num_agents_so_far = []
    for agent_info in config.agents:
        kwargs = agent_info.init_kwargs
        kwargs["rng"] = rng
        for policy_instance_index in range(agent_info.number_of_bots):
            kwargs["budget"] = agent_info.budget.sample_budget(rng)
            agent_count = policy_instance_index + sum(num_agents_so_far)
            # programatically load the policy, then invoke it
            policy = all_policies[agent_info.name](**kwargs)
            # create agents
            agent = Agent(wallet_address=eth_account.checksum_address, policy=policy)
            eth_account = eth.accounts.EthAccount(extra_entropy=str(agent_count))
            # fund test account with ether
            rpc_response = eth.set_anvil_account_balance(
                web3, eth_account.checksum_address, int(web3.to_wei(1000, "ether"))
            )
            print(f"{rpc_response=}")  # FIXME: raise issue on failure
            # fund test account by minting with the ERC20 base account
            tx_receipt = eth.smart_contract_transact(
                web3, base_token_contract, "mint", eth_account.checksum_address, kwargs["budget"].scaled_value
            )
            print(f"{tx_receipt=}")  # FIXME: raise issue on failure
            agents[f"agent_{eth_account.checksum_address}"] = (eth_account, agent)
        num_agents_so_far.append(agent_info.number_of_bots)
    logging.info("Added %d agents", sum(num_agents_so_far))
    return agents

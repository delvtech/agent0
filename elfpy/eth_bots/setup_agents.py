"""Script for loading ETH & Elfpy agents with trading policies"""
from __future__ import annotations

import logging

from numpy.random._generator import Generator as NumpyGenerator
from web3 import Web3
from web3.contract.contract import Contract

from elfpy import eth
from elfpy.bots.bot_info import BotInfo

from .eth_agent import EthAgent


def get_agents(config: list[BotInfo], web3: Web3, base_token_contract: Contract, rng: NumpyGenerator) -> list[EthAgent]:
    """Get agents according to provided config"""
    agents: list[EthAgent] = []
    num_agents_so_far: list[int] = []
    for agent_info in config.agents:
        kwargs = agent_info.init_kwargs
        kwargs["rng"] = rng
        for policy_instance_index in range(agent_info.number_of_bots):
            kwargs["budget"] = agent_info.budget.sample_budget(rng)
            agent_count = policy_instance_index + sum(num_agents_so_far)
            # create agents
            eth_account = eth.accounts.EthAccount(extra_entropy=str(agent_count))
            agent = EthAgent(wallet_address=eth_account.checksum_address, policy=agent.policy, eth_account=eth_account)
            # fund test account with ether
            rpc_response = eth.set_anvil_account_balance(
                web3, eth_account.checksum_address, int(web3.to_wei(1000, "ether"))
            )
            print(f"{rpc_response=}")  # TODO: raise issue on failure
            # fund test account by minting with the ERC20 base account
            tx_receipt = eth.smart_contract_transact(
                web3, base_token_contract, "mint", eth_account.checksum_address, kwargs["budget"].scaled_value
            )
            print(f"{tx_receipt=}")  # TODO: raise issue on failure
            agents.append(agent)
        num_agents_so_far.append(agent_info.number_of_bots)
    logging.info("Added %d agents", sum(num_agents_so_far))
    return agents

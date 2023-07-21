"""Script for loading ETH & Elfpy agents with trading policies"""
from __future__ import annotations

import logging

import eth_utils
import requests
from numpy.random._generator import Generator as NumpyGenerator
from web3 import Web3
from web3.contract.contract import Contract

from elfpy import eth
from elfpy.agents.agent import Agent
from elfpy.bots import BotInfo, EnvironmentConfig
from elfpy.eth.accounts import EthAccount


def register_username(register_url: str, wallet_addrs: list[str], username: str) -> None:
    """Connects to the register user flask server via post request and registeres the username"""
    json_data = {"wallet_addrs": wallet_addrs, "username": username}
    result = requests.post(register_url + "/register_bots", json=json_data, timeout=3)
    if result.status_code != 200:
        raise ConnectionError(result)


def get_agent_accounts(
    agent_config: list[BotInfo],
    environment_config: EnvironmentConfig,
    web3: Web3,
    base_token_contract: Contract,
    hyperdrive_address: str,
    rng: NumpyGenerator,
) -> list[EthAccount]:
    """Get agents according to provided config, provide eth, base token and approve hyperdrive.

    Arguments
    ---------
    agent_config : list[BotInfo]
        List containing all of the agent specifications
    environment_config : EnvironmentConfig
        Dataclass containing all of the user environment settings
    web3 : Web3
        web3 provider object
    base_token_contract : Contract
        The deployed ERC20 base token contract
    hyperdrive_address : str
        The address of the deployed hyperdrive contract
    rng : numpy.random._generator.Generator
        The experiment's stateful random number generator

    Returns
    -------
    list[EthAccount]
        A list of EthAccount objects that contain a wallet address and a Elfpy Agent for determining trades
    """
    # TODO: raise issue on failure by looking at `rpc_response`, `tx_receipt` returned from function
    #   Do this for `set_anvil_account_balance`, `smart_contract_transact(mint)`, `smart_contract_transact(approve)`
    agents: list[EthAccount] = []
    num_agents_so_far: list[int] = []
    for agent_info in agent_config:
        kwargs = agent_info.init_kwargs
        kwargs["rng"] = rng
        for policy_instance_index in range(agent_info.number_of_bots):
            kwargs["budget"] = agent_info.budget.sample_budget(rng)
            agent_count = policy_instance_index + sum(num_agents_so_far)
            # create agents
            # FIXME: add better comments explaining this process
            policy = agent_info.policy(**kwargs)
            agent = Agent(wallet_address=agent_count, policy=policy)
            eth_account = eth.accounts.EthAccount(agent=agent, extra_entropy=str(agent_count))
            # fund test account with ethereum
            _ = eth.set_anvil_account_balance(web3, eth_account.checksum_address, int(web3.to_wei(1000, "ether")))
            # fund test account by minting with the ERC20 base account
            _ = eth.smart_contract_transact(
                web3,
                base_token_contract,
                eth_account,
                "mint(address,uint256)",
                eth_account.checksum_address,
                kwargs["budget"].scaled_value,
            )
            # Establish max approval for the hyperdrive contract
            _ = eth.smart_contract_transact(
                web3,
                base_token_contract,
                eth_account,
                "approve",
                hyperdrive_address,
                eth_utils.conversions.to_int(eth_utils.currency.MAX_WEI),
            )
            agents.append(eth_account)
        num_agents_so_far.append(agent_info.number_of_bots)
    logging.info("Added %d agents", sum(num_agents_so_far))
    # Set up postgres to write username to agent wallet addr
    # initialize the postgres session
    wallet_addrs = [str(agent.checksum_address) for agent in agents]
    register_username(environment_config.username_register_url, wallet_addrs, environment_config.username)
    return agents

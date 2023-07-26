"""Script for loading ETH & Elfpy agents with trading policies"""
from __future__ import annotations

import json
import logging
import os

import eth_utils
from dotenv import load_dotenv
from fixedpointmath import FixedPoint
from numpy.random._generator import Generator as NumpyGenerator
from web3 import Web3
from web3.contract.contract import Contract

from elfpy import eth
from elfpy.agents.agent import Agent
from elfpy.bots import AgentConfig
from elfpy.eth.accounts import EthAccount

# pylint: disable=too-many-locals


def get_agent_accounts(
    agent_config: list[AgentConfig],
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
        A list of EthAccount objects that contain a wallet address and Elfpy Agent for determining trades
    """
    # load user dotenv variables
    load_dotenv()
    # TODO: raise issue on failure by looking at `rpc_response`, `tx_receipt` returned from function
    #   Do this for `set_anvil_account_balance`, `smart_contract_transact(mint)`, `smart_contract_transact(approve)`
    agents: list[EthAccount] = []
    num_agents_so_far: list[int] = []  # maintains the total number of agents for each agent type
    key_string = os.environ.get("AGENT_KEYS")
    if key_string is None:
        raise ValueError("AGENT_KEYS environment variable must be set")
    agent_private_keys = json.loads(key_string)
    #  get agent budgets
    base_budget_string = os.environ.get("AGENT_BASE_BUDGETS")
    if base_budget_string is None:
        raise ValueError("AGENT_BASE_BUDGETS environment variable must be set")
    agent_base_budgets = [int(budget) for budget in json.loads(base_budget_string)]
    # each agent_info object specifies one agent type and a variable number of agents of that type
    for agent_info in agent_config:
        kwargs = agent_info.init_kwargs
        kwargs["rng"] = rng
        for policy_instance_index in range(agent_info.number_of_agents):  # instantiate one agent per policy
            kwargs["budget"] = agent_info.base_budget.sample_budget(rng)
            kwargs["slippage_tolerance"] = agent_info.slippage_tolerance
            agent_count = policy_instance_index + sum(num_agents_so_far)
            if len(agent_base_budgets) >= agent_count:
                kwargs["budget"] = FixedPoint(scaled_value=agent_base_budgets[agent_count])
            else:
                kwargs["budget"] = agent_info.base_budget.sample_budget(rng)
                # TODO: This is where we would fund the bots if we wanted to mint money from nothing
            # the Agent object holds the policy, which makes decisions based
            # on the market and can produce a list of trades
            # NOTE: the wallet_address argument is a throwaway right now; the eth_account will have the actual address
            agent = Agent(wallet_address=agent_count, policy=agent_info.policy(**kwargs))
            # the eth_account holds an agent (where the smarts lies) as well as a wallet (an address used by contracts)
            if len(agent_private_keys) < agent_count:
                raise AssertionError(
                    "Private keys must be specified for the eth_bots demo. Did you list enough in your .env?"
                )
            eth_account = eth.accounts.EthAccount(agent=agent, private_key=agent_private_keys[agent_count])
            agent_eth_funds = eth.rpc_interface.get_account_balance(web3, eth_account.checksum_address)
            if agent_eth_funds == 0:
                raise AssertionError(
                    f"Agent needs Ethereum to operate! The agent {eth_account.checksum_address=} has a "
                    f"balance of {agent_eth_funds=}.\nDid you fund their accounts?"
                )
            agent_base_funds = eth.smart_contract_read(base_token_contract, "balanceOf", eth_account.checksum_address)
            if agent_base_funds["value"] == 0:
                raise AssertionError("Agent needs Base tokens to operate! Did you fund their accounts?")
            # establish max approval for the hyperdrive contract
            _ = eth.smart_contract_transact(
                web3,
                base_token_contract,
                eth_account,
                "approve",
                hyperdrive_address,
                eth_utils.conversions.to_int(eth_utils.currency.MAX_WEI),
            )
            agents.append(eth_account)
        num_agents_so_far.append(agent_info.number_of_agents)
    logging.info("Added %d agents", sum(num_agents_so_far))
    return agents

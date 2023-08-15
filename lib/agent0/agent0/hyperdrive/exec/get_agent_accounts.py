"""Script for loading ETH & Elfpy agents with trading policies"""
from __future__ import annotations

import logging

import eth_utils
from agent0 import AccountKeyConfig
from agent0.base.config import AgentConfig
from agent0.hyperdrive.agents import HyperdriveAgent
from eth_account.account import Account
from ethpy.base import get_account_balance, smart_contract_read, smart_contract_transact
from fixedpointmath import FixedPoint
from numpy.random._generator import Generator as NumpyGenerator
from web3 import Web3
from web3.contract.contract import Contract


# TODO consolidate config
# pylint: disable=too-many-arguments
def get_agent_accounts(
    web3: Web3,
    agent_config: list[AgentConfig],
    account_key_config: AccountKeyConfig,
    base_token_contract: Contract,
    hyperdrive_address: str,
    rng: NumpyGenerator,
) -> list[HyperdriveAgent]:
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
    list[Agent]
        A list of Agent objects that contain a wallet address and Elfpy Agent for determining trades
    """
    # TODO: raise issue on failure by looking at `rpc_response`, `tx_receipt` returned from function
    #   Do this for `set_anvil_account_balance`, `smart_contract_transact(mint)`, `smart_contract_transact(approve)`
    agents: list[HyperdriveAgent] = []
    num_agents_so_far: list[int] = []  # maintains the total number of agents for each agent type
    agent_base_budgets = [int(budget) for budget in account_key_config.AGENT_BASE_BUDGETS]

    # each agent_info object specifies one agent type and a variable number of agents of that type
    for agent_info in agent_config:
        kwargs = agent_info.init_kwargs
        kwargs["rng"] = rng
        for policy_instance_index in range(agent_info.number_of_agents):  # instantiate one agent per policy
            agent_count = policy_instance_index + sum(num_agents_so_far)
            # the agent object holds the policy, which makes decisions based
            # on the market and can produce a list of trades
            if len(account_key_config.AGENT_KEYS) < agent_count:
                raise AssertionError(
                    "Private keys must be specified for the eth_bots demo. Did you list enough in your .env?"
                )
            # Get the budget from the env file
            kwargs["budget"] = FixedPoint(scaled_value=agent_base_budgets[agent_count])
            kwargs["slippage_tolerance"] = agent_info.slippage_tolerance
            eth_agent = HyperdriveAgent(
                Account().from_key(account_key_config.AGENT_KEYS[agent_count]), policy=agent_info.policy(**kwargs)
            )
            if get_account_balance(web3, eth_agent.checksum_address) == 0:
                raise AssertionError(
                    f"Agent needs Ethereum to operate! The agent {eth_agent.checksum_address=} has a "
                    f"balance of 0.\nDid you fund their accounts?"
                )
            agent_base_funds = smart_contract_read(base_token_contract, "balanceOf", eth_agent.checksum_address)
            if agent_base_funds["value"] == 0:
                raise AssertionError("Agent needs Base tokens to operate! Did you fund their accounts?")
            # establish max approval for the hyperdrive contract
            _ = smart_contract_transact(
                web3,
                base_token_contract,
                eth_agent,
                "approve",
                hyperdrive_address,
                eth_utils.conversions.to_int(eth_utils.currency.MAX_WEI),
            )
            agents.append(eth_agent)
        num_agents_so_far.append(agent_info.number_of_agents)
    logging.info("Added %d agents", sum(num_agents_so_far))
    return agents

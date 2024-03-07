"""Script for loading agents with trading policies."""

from __future__ import annotations

import asyncio
import logging

import eth_utils
from eth_account.account import Account
from fixedpointmath import FixedPoint
from numpy.random._generator import Generator
from web3 import Web3
from web3.contract.contract import Contract
from web3.types import TxReceipt

from agent0.core import AccountKeyConfig
from agent0.core.base.config import AgentConfig
from agent0.core.hyperdrive import HyperdriveAgent
from agent0.ethpy.base import async_smart_contract_transact, get_account_balance

RETRY_COUNT = 5


# TODO consolidate various configs into one config?
# Unsure if above is necessary, as long as key agent0 interface is concise.
# pylint: disable=too-many-arguments
def get_agent_accounts(
    web3: Web3,
    agent_config: list[AgentConfig],
    account_key_config: AccountKeyConfig,
    base_token_contract: Contract,
    hyperdrive_address: str,
    global_rng: Generator,
) -> list[HyperdriveAgent]:
    """Get agents according to provided config, provide eth, base token and approve hyperdrive.

    Arguments
    ---------
    web3: Web3
        Web3 provider object.
    agent_config: list[AgentConfig]
        List containing all of the agent specifications.
    account_key_config: AccountKeyConfig
        Dataclass containing configuration options for the agent account, including keys and budgets.
    base_token_contract: Contract
        The deployed ERC20 base token contract.
    hyperdrive_address: str
        The address of the deployed hyperdrive contract.
    global_rng: `numpy.random._generator.Generator <https://numpy.org/doc/stable/reference/random/generator.html>`_
        The experiment's stateful random number generator.

    Returns
    -------
    list[Agent]
        A list of Agent objects that contain a wallet address and Agent for determining trades
    """
    # TODO: raise issue on failure by looking at `rpc_response`, `tx_receipt` returned from function
    #   Do this for `set_anvil_account_balance`, `smart_contract_transact(mint)`, `smart_contract_transact(approve)`
    agents: list[HyperdriveAgent] = []
    num_agents_so_far: list[int] = []  # maintains the total number of agents for each agent type
    agent_base_budgets = [int(budget) for budget in account_key_config.AGENT_BASE_BUDGETS]

    # each agent_info object specifies one agent type and a variable number of agents of that type
    for agent_info in agent_config:
        for policy_instance_index in range(agent_info.number_of_agents):  # instantiate one agent per policy
            agent_count = policy_instance_index + sum(num_agents_so_far)
            # the agent object holds the policy, which makes decisions based
            # on the market and can produce a list of trades
            if len(account_key_config.AGENT_KEYS) < agent_count:
                raise AssertionError("Private keys must be specified. Did you list them in your .env?")
            # Get the budget from the env file
            agent_budget = FixedPoint(scaled_value=agent_base_budgets[agent_count])

            # Check in policy config to see if rng is set.
            # If it's not set, spawn a new rng from the global rng
            if agent_info.policy_config.rng_seed is None and agent_info.policy_config.rng is None:
                agent_info.policy_config.rng = global_rng.spawn(1)[0]

            eth_agent = HyperdriveAgent(
                Account().from_key(account_key_config.AGENT_KEYS[agent_count]),
                initial_budget=agent_budget,
                policy=agent_info.policy(agent_info.policy_config),
            )
            if get_account_balance(web3, eth_agent.checksum_address) == 0:
                raise AssertionError(
                    f"Agent needs Ethereum to operate! The agent {eth_agent.checksum_address=} has a "
                    f"balance of 0.\nDid you fund their accounts?"
                )
            agents.append(eth_agent)
        num_agents_so_far.append(agent_info.number_of_agents)
    logging.info("Added %d agents", sum(num_agents_so_far))

    # establish max approval for the hyperdrive contract
    asyncio.run(set_max_approval(agents, web3, base_token_contract, hyperdrive_address))

    return agents


async def set_max_approval(
    agents: list[HyperdriveAgent], web3: Web3, base_token_contract: Contract, hyperdrive_address: str
) -> None:
    """Establish max approval for the hyperdrive contract for all agents async

    Arguments
    ---------
    agents: list[HyperdriveAgent]
        List of agents
    web3: Web3
        web3 provider object
    base_token_contract: Contract
        The deployed ERC20 base token contract
    hyperdrive_address: str
        The address of the deployed hyperdrive contract
    """
    agents_left = list(agents)
    exception = None
    for attempt in range(RETRY_COUNT):
        approval_calls = [
            async_smart_contract_transact(
                web3,
                base_token_contract,
                agent,
                "approve",
                hyperdrive_address,
                eth_utils.conversions.to_int(eth_utils.currency.MAX_WEI),
            )
            for agent in agents_left
        ]
        # We expect the type here to be BaseException (due to the return type of asyncio.gather),
        # but the underlying exception should be subclassed from Exception.
        gather_results: list[TxReceipt | BaseException] = await asyncio.gather(*approval_calls, return_exceptions=True)

        # Rebuild accounts_left list if the result errored out for next iteration
        out_agents_left = []
        for agent, result in zip(agents_left, gather_results):
            if isinstance(result, Exception):
                out_agents_left.append(agent)
                logging.warning(
                    "Retry attempt %s out of %s: Base approval failed with exception %s",
                    attempt,
                    RETRY_COUNT,
                    repr(result),
                )
                exception = result
        agents_left = out_agents_left
        # If successful, break retry loop
        if len(agents_left) == 0:
            break

    if len(agents_left) > 0:
        assert exception is not None
        raise exception

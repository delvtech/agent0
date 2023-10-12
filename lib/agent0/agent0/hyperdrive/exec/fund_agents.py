"""Fund agent private keys from a user key."""
from __future__ import annotations

import asyncio
import os

from agent0 import AccountKeyConfig
from agent0.hyperdrive.agents import HyperdriveAgent
from eth_account.account import Account
from ethpy import EthConfig
from ethpy.base import (
    async_eth_transfer,
    async_retry_call,
    async_smart_contract_transact,
    get_account_balance,
    initialize_web3_with_http_provider,
    load_abi_from_file,
    smart_contract_read,
)
from ethpy.hyperdrive import HyperdriveAddresses

RETRY_COUNT = 5

# TODO async_retry_call should really be a generic util function, not something in
# ethpy to be used here.


async def async_fund_agents(
    user_account: HyperdriveAgent,
    eth_config: EthConfig,
    account_key_config: AccountKeyConfig,
    contract_addresses: HyperdriveAddresses,
) -> None:
    """Fund agents using passed in configs.

    Arguments
    ---------
    user_account : HyperdriveAgent
        The HyperdriveAgent corresponding to the user account to fund the agents.
    eth_config: EthConfig
        Configuration for URIs to the rpc and artifacts.
    account_key_config: AccountKeyConfig
        Configuration linking to the env file for storing private keys and initial budgets.
        Defines the agents to be funded.
    contract_addresses: HyperdriveAddresses
        Configuration for defining various contract addresses.
    """
    agent_accounts = [
        HyperdriveAgent(Account().from_key(agent_private_key)) for agent_private_key in account_key_config.AGENT_KEYS
    ]

    web3 = initialize_web3_with_http_provider(eth_config.rpc_uri, reset_provider=False)
    abi_file_loc = os.path.join(
        os.path.join(eth_config.abi_dir, "ERC20Mintable.sol"),
        "ERC20Mintable.json",
    )
    base_contract_abi = load_abi_from_file(abi_file_loc)

    base_token_contract = web3.eth.contract(
        abi=base_contract_abi, address=web3.to_checksum_address(contract_addresses.base_token)
    )

    # Check for balances
    total_agent_eth_budget = sum((int(budget) for budget in account_key_config.AGENT_ETH_BUDGETS))
    total_agent_base_budget = sum((int(budget) for budget in account_key_config.AGENT_BASE_BUDGETS))

    user_eth_balance = get_account_balance(web3, user_account.checksum_address)
    if user_eth_balance is None:
        raise AssertionError("User has no Ethereum balance")
    if user_eth_balance < total_agent_eth_budget:
        raise AssertionError(
            f"User account {user_account.checksum_address=} has {user_eth_balance=}, "
            f"which must be >= {total_agent_eth_budget=}"
        )

    user_base_balance = smart_contract_read(
        base_token_contract,
        "balanceOf",
        user_account.checksum_address,
    )["value"]
    if user_base_balance < total_agent_base_budget:
        raise AssertionError(
            f"User account {user_account.checksum_address=} has {user_base_balance=}, "
            f"which must be >= {total_agent_base_budget=}"
        )

    # Launch all funding processes in async mode
    print("Funding accounts")

    # Sanity check for zip function
    assert len(agent_accounts) == account_key_config.AGENT_ETH_BUDGETS
    assert len(agent_accounts) == account_key_config.AGENT_BASE_BUDGETS

    # Gather all async function calls in a list
    # Running with retries
    eth_funding_calls = [
        async_retry_call(
            RETRY_COUNT, None, async_eth_transfer, web3, user_account, agent_account.checksum_address, agent_eth_budget
        )
        for agent_account, agent_eth_budget in zip(agent_accounts, account_key_config.AGENT_ETH_BUDGETS)
    ]
    base_funding_calls = [
        async_retry_call(
            RETRY_COUNT,
            None,
            async_smart_contract_transact,
            web3,
            base_token_contract,
            user_account,
            "transfer",
            agent_account.checksum_address,
            agent_base_budget,
        )
        for agent_account, agent_base_budget in zip(agent_accounts, account_key_config.AGENT_BASE_BUDGETS)
    ]

    await asyncio.gather(*(eth_funding_calls + base_funding_calls))

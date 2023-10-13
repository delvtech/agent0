"""Fund agent private keys from a user key."""
from __future__ import annotations

import asyncio
import logging
import os

from agent0 import AccountKeyConfig
from agent0.hyperdrive.agents import HyperdriveAgent
from elfpy.utils import logs as log_utils
from eth_account.account import Account
from ethpy import EthConfig
from ethpy.base import (
    async_eth_transfer,
    async_smart_contract_transact,
    get_account_balance,
    initialize_web3_with_http_provider,
    load_abi_from_file,
    retry_call,
    smart_contract_read,
)
from ethpy.hyperdrive import HyperdriveAddresses
from web3.types import Nonce, TxReceipt

RETRY_COUNT = 5


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

    # Funding contains its own logging as this is typically ran from a script or in debug mode
    log_utils.setup_logging(".logging/fund_accounts.log", log_stdout=True)

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

    # Sanity check for zip function
    assert len(agent_accounts) == len(account_key_config.AGENT_ETH_BUDGETS)
    assert len(agent_accounts) == len(account_key_config.AGENT_BASE_BUDGETS)

    # We launch funding in batches, so we do an outer retry loop here
    # Fund eth
    logging.info("Funding Eth")
    accounts_left = [
        (agent_account, eth_budget)
        for agent_account, eth_budget in zip(agent_accounts, account_key_config.AGENT_ETH_BUDGETS)
    ]
    for attempt in range(RETRY_COUNT):
        # Fund agents async from a single account.
        # To do this, we need to manually set the nonce, so we get the base transaction count here
        # and pass in an incrementing nonce per call
        # TODO figure out which exception here to retry on
        base_nonce = retry_call(5, None, web3.eth.get_transaction_count, user_account.checksum_address)

        # Gather all async function calls in a list
        # Running with retries
        # Explicitly setting a nonce here due to nonce issues with launching a batch of transactions
        eth_funding_calls = [
            async_eth_transfer(
                web3, user_account, agent_account.checksum_address, agent_eth_budget, nonce=Nonce(base_nonce + i)
            )
            for i, (agent_account, agent_eth_budget) in enumerate(accounts_left)
        ]
        gather_results: list[TxReceipt | Exception] = await asyncio.gather(*eth_funding_calls, return_exceptions=True)

        # Rebuild accounts_left list if the result errored out for next iteration
        accounts_left = []
        for account, result in zip(accounts_left, gather_results):
            if isinstance(result, Exception):
                accounts_left.append(account)
                logging.warning(
                    "Retry attempt %s out of %s: Eth transfer failed with exception %s",
                    attempt,
                    RETRY_COUNT,
                    repr(result),
                )
        # If all accounts funded, break retry loop
        if len(accounts_left) == 0:
            break

    # We launch funding in batches, so we do an outer retry loop here
    # Fund base
    logging.info("Funding Base")
    accounts_left = [
        (agent_account, base_budget)
        for agent_account, base_budget in zip(agent_accounts, account_key_config.AGENT_BASE_BUDGETS)
    ]
    for attempt in range(RETRY_COUNT):
        # Fund agents async from a single account.
        # To do this, we need to manually set the nonce, so we get the base transaction count here
        # and pass in an incrementing nonce per call
        # TODO figure out which exception here to retry on
        base_nonce = retry_call(5, None, web3.eth.get_transaction_count, user_account.checksum_address)

        # Gather all async function calls in a list
        # Running with retries
        # Explicitly setting a nonce here due to nonce issues with launching a batch of transactions
        base_funding_calls = [
            async_smart_contract_transact(
                web3,
                base_token_contract,
                user_account,
                "transfer",
                agent_account.checksum_address,
                agent_base_budget,
                nonce=Nonce(base_nonce + i),
            )
            for i, (agent_account, agent_base_budget) in enumerate(accounts_left)
        ]
        gather_results: list[TxReceipt | Exception] = await asyncio.gather(*base_funding_calls, return_exceptions=True)

        # Rebuild accounts_left list if the result errored out for next iteration
        accounts_left = []
        for account, result in zip(accounts_left, gather_results):
            if isinstance(result, Exception):
                accounts_left.append(account)
                logging.warning(
                    "Retry attempt %s out of %s: Base transfer failed with exception %s",
                    attempt,
                    RETRY_COUNT,
                    repr(result),
                )
        # If all accounts funded, break retry loop
        if len(accounts_left) == 0:
            break

    logging.info("Accounts funded")

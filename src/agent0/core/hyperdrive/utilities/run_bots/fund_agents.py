"""Fund agent private keys from a user key."""

from __future__ import annotations

import asyncio
import logging

from eth_account.account import Account
from web3.types import Nonce, TxReceipt

from agent0.core import AccountKeyConfig
from agent0.core.base.make_key import make_private_key
from agent0.core.hyperdrive import HyperdriveAgent
from agent0.ethpy.base import (
    async_eth_transfer,
    async_smart_contract_transact,
    get_account_balance,
    retry_call,
    set_anvil_account_balance,
    smart_contract_transact,
)
from agent0.ethpy.hyperdrive import HyperdriveReadInterface

FUND_RETRY_COUNT = 5
DEFAULT_READ_RETRY_COUNT = 5


def async_fund_agents_with_fake_user(
    interface: HyperdriveReadInterface,
    account_key_config: AccountKeyConfig,
) -> None:
    """Create a fake user account with money and fund agents.

    Arguments
    ---------
    interface: HyperdriveReadInterface
        An Hyperdrive interface object for accessing the base token contract.
    account_key_config: AccountKeyConfig
        Configuration linking to the env file for storing private keys and initial budgets.
        Defines the agents to be funded.
    """
    # Generate fake user account
    user_private_key = make_private_key(extra_entropy="FAKE USER")  # argument value can be any str
    user_account = HyperdriveAgent(Account().from_key(user_private_key))
    # Fund the user with Eth
    eth_balance = sum((int(budget) for budget in account_key_config.AGENT_ETH_BUDGETS)) * 2  # double for good measure
    _ = set_anvil_account_balance(interface.web3, user_account.address, eth_balance)
    # Fund the user with Base
    base_balance = sum((int(budget) for budget in account_key_config.AGENT_BASE_BUDGETS)) * 2  # double for good measure
    _ = smart_contract_transact(
        interface.web3,
        interface.base_token_contract,
        user_account,
        "mint(address,uint256)",
        user_account.checksum_address,
        base_balance,
    )
    asyncio.run(async_fund_agents(interface, user_account, account_key_config))


async def async_fund_agents(
    interface: HyperdriveReadInterface,
    user_account: HyperdriveAgent,
    account_key_config: AccountKeyConfig,
) -> None:
    """Fund agents using passed in configs.

    Arguments
    ---------
    interface: HyperdriveReadInterface
        An Hyperdrive interface object for accessing the base token contract.
    user_account: HyperdriveAgent
        The HyperdriveAgent corresponding to the user account to fund the agents.
    account_key_config: AccountKeyConfig
        Configuration linking to the env file for storing private keys and initial budgets.
        Defines the agents to be funded.
    """
    # Check that the user has enough money to fund the agents
    _check_user_balances(interface, user_account, account_key_config)

    # Launch all funding processes in async mode
    # We launch funding in batches, so we do an outer retry loop here
    # Fund eth
    logging.info("Funding Eth.")
    # Prepare accounts and eth budgets
    # Sanity check for zip function
    agent_accounts = [
        HyperdriveAgent(Account().from_key(agent_private_key)) for agent_private_key in account_key_config.AGENT_KEYS
    ]
    accounts_left = list(zip(agent_accounts, account_key_config.AGENT_ETH_BUDGETS))
    for attempt in range(FUND_RETRY_COUNT):
        # Fund agents async from a single account.
        # To do this, we need to manually set the nonce, so we get the base transaction count here
        # and pass in an incrementing nonce per call
        # TODO figure out which exception here to retry on
        base_nonce = retry_call(
            DEFAULT_READ_RETRY_COUNT, None, interface.web3.eth.get_transaction_count, user_account.checksum_address
        )

        # Gather all async function calls in a list
        # Running with retries
        # Explicitly setting a nonce here due to nonce issues with launching a batch of transactions
        eth_funding_calls = [
            async_eth_transfer(
                interface.web3,
                user_account,
                agent_account.checksum_address,
                agent_eth_budget,
                nonce=Nonce(base_nonce + i),
            )
            for i, (agent_account, agent_eth_budget) in enumerate(accounts_left)
        ]
        gather_results: list[TxReceipt | BaseException] = await asyncio.gather(
            *eth_funding_calls, return_exceptions=True
        )

        # Rebuild accounts_left list if the result errored out for next iteration
        accounts_left = []
        for account, result in zip(accounts_left, gather_results):
            if isinstance(result, Exception):
                accounts_left.append(account)
                logging.warning(
                    "Retry attempt %s out of %s: Eth transfer failed with exception %s",
                    attempt,
                    FUND_RETRY_COUNT,
                    repr(result),
                )
        # If all accounts funded, break retry loop
        if len(accounts_left) == 0:
            break

    # We launch funding in batches, so we do an outer retry loop here
    # Fund base
    logging.info("Funding Base.")
    # Prepare accounts and eth budgets
    accounts_left = list(zip(agent_accounts, account_key_config.AGENT_BASE_BUDGETS))
    for attempt in range(FUND_RETRY_COUNT):
        # Fund agents async from a single account.
        # To do this, we need to manually set the nonce, so we get the base transaction count here
        # and pass in an incrementing nonce per call
        # TODO figure out which exception here to retry on
        base_nonce = retry_call(
            DEFAULT_READ_RETRY_COUNT, None, interface.web3.eth.get_transaction_count, user_account.checksum_address
        )

        # Gather all async function calls in a list
        # Running with retries
        # Explicitly setting a nonce here due to nonce issues with launching a batch of transactions
        base_funding_calls = [
            async_smart_contract_transact(
                interface.web3,
                interface.base_token_contract,
                user_account,
                "transfer",
                agent_account.checksum_address,
                agent_base_budget,
                nonce=Nonce(base_nonce + i),
            )
            for i, (agent_account, agent_base_budget) in enumerate(accounts_left)
        ]
        gather_results: list[TxReceipt | BaseException] = await asyncio.gather(
            *base_funding_calls, return_exceptions=True
        )

        # Rebuild accounts_left list if the result errored out for next iteration
        accounts_left = []
        for account, result in zip(accounts_left, gather_results):
            if isinstance(result, Exception):
                accounts_left.append(account)
                logging.warning(
                    "Retry attempt %s out of %s: Base transfer failed with exception %s",
                    attempt,
                    FUND_RETRY_COUNT,
                    repr(result),
                )
        # If all accounts funded, break retry loop
        if len(accounts_left) == 0:
            break


def _check_user_balances(
    interface: HyperdriveReadInterface,
    user_account: HyperdriveAgent,
    account_key_config: AccountKeyConfig,
) -> None:
    """Check the user eth and base balances to ensure there is enough for funding agents.

    Arguments
    ---------
    interface: HyperdriveReadInterface
        An Hyperdrive interface object for accessing the base token contract.
    user_account: HyperdriveAgent
        The HyperdriveAgent corresponding to the user account to fund the agents.
    account_key_config: AccountKeyConfig
        Configuration linking to the env file for storing private keys and initial budgets.
        Defines the agents to be funded.
    """
    # Eth balance check
    user_eth_balance = get_account_balance(interface.web3, user_account.checksum_address)
    total_agent_eth_budget = sum((int(budget) for budget in account_key_config.AGENT_ETH_BUDGETS))
    if user_eth_balance is None:
        raise AssertionError("User has no Ethereum balance")
    if user_eth_balance < total_agent_eth_budget:
        raise AssertionError(
            f"User account {user_account.checksum_address=} has {user_eth_balance=}, "
            f"which must be >= {total_agent_eth_budget=}"
        )

    # Base balance check
    user_base_balance = interface.base_token_contract.functions.balanceOf(user_account.checksum_address).call()
    total_agent_base_budget = sum((int(budget) for budget in account_key_config.AGENT_BASE_BUDGETS))
    if user_base_balance < total_agent_base_budget:
        raise AssertionError(
            f"User account {user_account.checksum_address=} has {user_base_balance=}, "
            f"which must be >= {total_agent_base_budget=}"
        )

    # Ensure there are an equal number of keys and budgets
    if (len(account_key_config.AGENT_KEYS) != len(account_key_config.AGENT_ETH_BUDGETS)) or (
        len(account_key_config.AGENT_KEYS) != len(account_key_config.AGENT_BASE_BUDGETS)
    ):
        raise AssertionError(
            "Environment configs for AGENT_ETH_BUDGETS and AGENT_BASE_BUDGETS must be the same length as AGENT_KEYS."
        )

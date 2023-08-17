"""Fund agent private keys from a user key."""
from __future__ import annotations

import os

from agent0 import AccountKeyConfig
from agent0.hyperdrive.agents import HyperdriveAgent
from eth_account.account import Account
from ethpy import EthConfig
from ethpy.base import (
    eth_transfer,
    get_account_balance,
    initialize_web3_with_http_provider,
    load_abi_from_file,
    smart_contract_read,
    smart_contract_transact,
)
from ethpy.hyperdrive import HyperdriveAddresses


def fund_agents(
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
        Configuration for urls to the rpc and artifacts.
    account_key_config: AccountKeyConfig
        Configuration linking to the env file for storing private keys and initial budgets.
        Defines the agents to be funded.
    contract_addresses: HyperdriveAddresses
        Configuration for defining various contract addresses.
    """
    agent_accounts = [
        HyperdriveAgent(Account().from_key(agent_private_key)) for agent_private_key in account_key_config.AGENT_KEYS
    ]

    web3 = initialize_web3_with_http_provider(eth_config.RPC_URL, reset_provider=False)
    abi_file_loc = os.path.join(
        os.path.join(eth_config.ABI_DIR, "ERC20Mintable.sol"),
        "ERC20Mintable.json",
    )
    base_contract_abi = load_abi_from_file(abi_file_loc)

    base_token_contract = web3.eth.contract(
        abi=base_contract_abi, address=web3.to_checksum_address(contract_addresses.base_token)
    )

    for agent_account, agent_eth_budget, agent_base_budget in zip(
        agent_accounts, account_key_config.AGENT_ETH_BUDGETS, account_key_config.AGENT_BASE_BUDGETS
    ):
        # fund Ethereum
        user_eth_balance = get_account_balance(web3, user_account.checksum_address)
        if user_eth_balance is None:
            raise AssertionError("User has no Ethereum balance")
        if user_eth_balance < agent_eth_budget:
            raise AssertionError(
                f"User account {user_account.checksum_address=} has {user_eth_balance=}, "
                f"which must be >= {agent_eth_budget=}"
            )
        _ = eth_transfer(
            web3,
            user_account,
            agent_account.checksum_address,
            agent_eth_budget,
        )
        #  fund base
        user_base_balance = smart_contract_read(
            base_token_contract,
            "balanceOf",
            user_account.checksum_address,
        )["value"]
        if user_base_balance < agent_base_budget:
            raise AssertionError(
                f"User account {user_account.checksum_address=} has {user_base_balance=}, "
                f"which must be >= {agent_base_budget=}"
            )
        _ = smart_contract_transact(
            web3,
            base_token_contract,
            user_account,
            "transfer",
            agent_account.checksum_address,
            agent_base_budget,
        )

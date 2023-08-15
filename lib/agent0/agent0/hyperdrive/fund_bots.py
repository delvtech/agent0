"""Fund agent private keys from a user key."""
from __future__ import annotations

import os

from agent0 import build_account_config
from agent0.hyperdrive.agents import HyperdriveAgent
from agent0.hyperdrive.config import get_eth_bots_config
from eth_account.account import Account
from ethpy.base import (
    eth_transfer,
    get_account_balance,
    initialize_web3_with_http_provider,
    load_abi_from_file,
    smart_contract_read,
    smart_contract_transact,
)
from ethpy.hyperdrive import fetch_hyperdrive_address_from_url


def fund_bots():
    """Fund bots using config settings"""

    account_config = build_account_config()

    user_account = HyperdriveAgent(Account().from_key(account_config.USER_KEY))
    agent_accounts = [
        HyperdriveAgent(Account().from_key(agent_private_key)) for agent_private_key in account_config.AGENT_KEYS
    ]

    environment_config, eth_config, _ = get_eth_bots_config()
    # setup web3 & contracts
    web3 = initialize_web3_with_http_provider(eth_config.RPC_URL)
    abi_file_loc = os.path.join(
        os.path.join(eth_config.ABI_DIR, environment_config.base_abi + ".sol"),
        environment_config.base_abi + ".json",
    )

    base_contract_abi = load_abi_from_file(abi_file_loc)
    addresses = fetch_hyperdrive_address_from_url(os.path.join(eth_config.ARTIFACTS_URL, "addresses.json"))
    base_token_contract = web3.eth.contract(
        abi=base_contract_abi, address=web3.to_checksum_address(addresses.base_token)
    )
    for agent_account, agent_eth_budget, agent_base_budget in zip(
        agent_accounts, account_config.AGENT_ETH_BUDGETS, account_config.AGENT_BASE_BUDGETS
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
        if user_base_balance < agent_eth_budget:
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


if __name__ == "__main__":
    # get keys & RPC url from the environment
    fund_bots()

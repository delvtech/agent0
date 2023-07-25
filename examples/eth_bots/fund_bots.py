"""Fund agent private keys from a user key."""
from __future__ import annotations

import json
import os

from dotenv import load_dotenv

from elfpy import eth, hyperdrive_interface

if __name__ == "__main__":
    # get keys & RPC url from the environment
    load_dotenv()
    # USER PRIVATE KEY
    user_key = os.environ.get("USER_KEY")
    if user_key is None:
        raise ValueError("USER_KEY environment variable must be set")
    user_account = eth.accounts.EthAccount(private_key=user_key)
    # LIST OF AGENT PRIVATE KEYS
    # NOTE: The env var should follow the JSON specification: https://www.json.org/json-en.html
    # for example, `export AGENT_KEYS='["foo", "bar"]'`
    key_string = os.environ.get("AGENT_KEYS")
    if key_string is None:
        raise ValueError("AGENT_KEYS environment variable must be set")
    agent_keys = json.loads(key_string)
    agent_accounts = [eth.accounts.EthAccount(private_key=agent_private_key) for agent_private_key in agent_keys]

    # AGENT ETHEREUM FUNDING AMOUNTS
    eth_budget_string = os.environ.get("AGENT_ETH_BUDGETS")
    if eth_budget_string is None:
        raise ValueError("AGENT_ETH_BUDGETS environment variable must be set")
    agent_eth_budgets = [int(budget) for budget in json.loads(eth_budget_string)]

    # AGENT BASE FUNDING AMOUNTS
    base_budget_string = os.environ.get("AGENT_BASE_BUDGETS")
    if base_budget_string is None:
        raise ValueError("AGENT_BASE_BUDGETS environment variable must be set")
    agent_base_budgets = [int(budget) for budget in json.loads(base_budget_string)]

    if len(agent_accounts) != len(agent_eth_budgets) or len(agent_accounts) != len(agent_base_budgets):
        raise AssertionError(
            f"{len(agent_accounts)=} must equal {len(agent_eth_budgets)=} and {len(agent_base_budgets)=}"
        )

    # RPC URL
    rpc_url = os.environ.get("RPC_URL")
    if rpc_url is None:
        raise ValueError("RPC_URL environment variable must be set")

    # ARTIFACTS URL
    artifacts_url = os.environ.get("ARTIFACTS_URL")
    if artifacts_url is None:
        raise ValueError("ARTIFACTS_URL environment variable must be set")

    # ABI
    base_abi_file = os.environ.get("BASE_ABI_FILE")
    if base_abi_file is None:
        raise ValueError("BASE_ABI_FILE environment variable must be set")

    # setup web3 & contracts
    web3 = eth.web3_setup.initialize_web3_with_http_provider(rpc_url)
    base_contract_abi = eth.abi.load_abi_from_file(base_abi_file)
    addresses = hyperdrive_interface.fetch_hyperdrive_address_from_url(os.path.join(artifacts_url, "addresses.json"))
    base_token_contract = web3.eth.contract(
        abi=base_contract_abi, address=web3.to_checksum_address(addresses.base_token)
    )
    for agent_account, agent_eth_budget, agent_base_budget in zip(
        agent_accounts, agent_eth_budgets, agent_base_budgets
    ):
        # fund Ethereum
        user_eth_balance = eth.get_account_balance(web3, user_account.checksum_address)
        if user_eth_balance < agent_eth_budget:
            raise AssertionError(
                f"User account {user_account.checksum_address=} has {user_eth_balance=}, which must be >= {agent_eth_budget=}"
            )
        _ = eth.eth_transfer(
            web3,
            user_account,
            agent_account.checksum_address,
            agent_eth_budget,
        )
        #  fund base
        _ = eth.smart_contract_transact(
            web3,
            base_token_contract,
            user_account,
            "mint(address,uint256)",
            user_account.checksum_address,
            agent_base_budget * 2,
        )
        user_base_balance = eth.smart_contract_read(
            base_token_contract,
            "balanceOf",
            user_account.checksum_address,
        )["value"]
        if user_base_balance < agent_eth_budget:
            raise AssertionError(
                f"User account {user_account.checksum_address=} has {user_base_balance=}, which must be >= {agent_base_budget=}"
            )
        _ = eth.smart_contract_transact(
            web3,
            base_token_contract,
            user_account,
            "transfer",
            agent_account.checksum_address,
            agent_base_budget,
        )
        print(f"Funded {agent_account.checksum_address=} from {user_account.checksum_address=}")

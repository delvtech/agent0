"""Fund agent private keys from a user key."""
from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from eth_account.account import Account

from elfpy import eth, hyperdrive_interface
from examples.eth_bots.eth_bots_config import get_eth_bots_config

if __name__ == "__main__":
    # get keys & RPC url from the environment
    load_dotenv()
    # USER PRIVATE KEY
    user_key = os.environ.get("USER_KEY")
    if user_key is None:
        raise ValueError("USER_KEY environment variable must be set")
    user_account = eth.accounts.EthAgent(Account().from_key(user_key))
    # LIST OF AGENT PRIVATE KEYS
    # NOTE: The env var should follow the JSON specification: https://www.json.org/json-en.html
    # for example, `export AGENT_KEYS='["foo", "bar"]'`
    key_string = os.environ.get("AGENT_KEYS")
    if key_string is None:
        raise ValueError("AGENT_KEYS environment variable must be set")
    agent_keys = json.loads(key_string)
    agent_accounts = [eth.accounts.EthAgent(Account().from_key(agent_private_key)) for agent_private_key in agent_keys]

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

    environment_config, agent_config = get_eth_bots_config()

    # setup web3 & contracts
    web3 = eth.web3_setup.initialize_web3_with_http_provider(environment_config.rpc_url)
    abi_file_loc = os.path.join(
        os.path.join(environment_config.abi_folder, environment_config.base_abi + ".sol"),
        environment_config.base_abi + ".json",
    )
    base_contract_abi = eth.abi.load_abi_from_file(abi_file_loc)
    addresses = hyperdrive_interface.fetch_hyperdrive_address_from_url(
        os.path.join(environment_config.artifacts_url, "addresses.json")
    )
    base_token_contract = web3.eth.contract(
        abi=base_contract_abi, address=web3.to_checksum_address(addresses.base_token)
    )
    for agent_account, agent_eth_budget, agent_base_budget in zip(
        agent_accounts, agent_eth_budgets, agent_base_budgets
    ):
        # fund Ethereum
        user_eth_balance = eth.get_account_balance(web3, user_account.checksum_address)
        if user_eth_balance is None:
            raise AssertionError("User has no Ethereum balance")
        if user_eth_balance < agent_eth_budget:
            raise AssertionError(
                f"User account {user_account.checksum_address=} has {user_eth_balance=}, "
                f"which must be >= {agent_eth_budget=}"
            )
        _ = eth.eth_transfer(
            web3,
            user_account,
            agent_account.checksum_address,
            agent_eth_budget,
        )
        #  fund base
        user_base_balance = eth.smart_contract_read(
            base_token_contract,
            "balanceOf",
            user_account.checksum_address,
        )["value"]
        if user_base_balance < agent_eth_budget:
            raise AssertionError(
                f"User account {user_account.checksum_address=} has {user_base_balance=}, "
                f"which must be >= {agent_base_budget=}"
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

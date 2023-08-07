"""Create agent accounts and fund them."""
from __future__ import annotations

import json
import os

from agent0.base.make_key import make_private_key
from agent0.hyperdrive.agents import HyperdriveAgent
from agent0.hyperdrive.config import get_eth_bots_config
from agent0.hyperdrive.exec import get_web3_and_contracts
from agent0.hyperdrive.fund_bots import fund_bots
from agent0.hyperdrive.generate_env import generate_env
from eth_account.account import Account
from ethpy.base import set_anvil_account_balance, smart_contract_transact


def create_and_fund_user_account() -> HyperdriveAgent:
    """Helper function for funding a base user account

    Returns
    -------
    HyperdriveAgent
        An agent that corresponds to the fake "user"
    """
    # generate fake user account
    user_private_key = make_private_key(extra_entropy="FAKE USER")  # argument value can be any str
    user_account = HyperdriveAgent(Account().from_key(user_private_key))
    # generate environment variable string
    env_string = generate_env(user_private_key)
    # instead of writing to a .env we will just set the environment variables here
    # the environment variables are used elsewhere in the run_hyperdrive_agents pipeline
    for env_setting in env_string.split("\n"):
        env_var, env_val = env_setting.split("=")
        os.environ[env_var] = env_val
    # get required contracts
    environment_config, _ = get_eth_bots_config()
    web3, base_token_contract, _ = get_web3_and_contracts(environment_config)
    # fund the user with ETH
    eth_budget_string = os.environ.get("AGENT_ETH_BUDGETS")
    eth_balance = sum([int(budget) for budget in json.loads(eth_budget_string)]) * 2  # double for good measure
    _ = set_anvil_account_balance(web3, user_account.address, eth_balance)
    # fund the user with Base
    base_budget_string = os.environ.get("AGENT_BASE_BUDGETS")
    base_balance = sum([int(budget) for budget in json.loads(base_budget_string)]) * 2  # double for god measure
    _ = smart_contract_transact(
        web3,
        base_token_contract,
        user_account,
        "mint(address,uint256)",
        user_account.checksum_address,
        base_balance,
    )
    return user_account

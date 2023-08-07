"""Create agent accounts and fund them."""
from __future__ import annotations

import os

from agent0.base.fund_bots import fund_bots
from agent0.base.generate_env import generate_env
from agent0.base.make_key import make_private_key
from agent0.hyperdrive.agents import HyperdriveAgent
from agent0.hyperdrive.config import get_eth_bots_config
from agent0.hyperdrive.exec import get_web3_and_contracts
from eth_account.account import Account
from ethpy.base import smart_contract_transact

# load config
environment_config, agent_config = get_eth_bots_config()
# generate fake user key
user_private_key = make_private_key()
user_account = HyperdriveAgent(Account().from_key(user_private_key))
# generate environment variable string
env_string = generate_env(user_private_key)
# instead of writing to a .env we will just set the environment variables here
for env_setting in env_string.split("\n"):
    env_var, env_val = env_setting.split("=")
    os.environ[env_var] = env_val
# Get required contracts
web3, base_token_contract, hyperdrive_contract = get_web3_and_contracts(environment_config)

# Fund the user with ETH

# Fund the user with Base
_ = smart_contract_transact(
    web3,
    base_token_contract,
    user_account,
    "mint(address,uint256)",
    user_account.checksum_address,
    1 * 10**24,  # 1M BASE
)

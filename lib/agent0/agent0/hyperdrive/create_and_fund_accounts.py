"""Create agent accounts and fund them."""
from __future__ import annotations

from agent0 import AccountKeyConfig
from agent0.base.config import EnvironmentConfig
from agent0.base.make_key import make_private_key
from eth_account.account import Account
from ethpy import EthConfig
from ethpy.base import set_anvil_account_balance, smart_contract_transact
from ethpy.hyperdrive.addresses import HyperdriveAddresses

from .agents.hyperdrive_account import HyperdriveAgent
from .exec.setup_experiment import get_web3_and_contracts


def create_and_fund_user_account(
    eth_config: EthConfig,
    environment_config: EnvironmentConfig,
    account_key_config: AccountKeyConfig,
    contract_addresses: HyperdriveAddresses,
) -> HyperdriveAgent:
    """Helper function for funding a fake user account

    Returns
    -------
    HyperdriveAgent
        An agent that corresponds to the fake "user"
    """
    # generate fake user account
    user_private_key = make_private_key(extra_entropy="FAKE USER")  # argument value can be any str
    user_account = HyperdriveAgent(Account().from_key(user_private_key))

    web3, base_token_contract, _ = get_web3_and_contracts(environment_config, eth_config, contract_addresses)

    eth_balance = sum((int(budget) for budget in account_key_config.AGENT_ETH_BUDGETS)) * 2  # double for good measure
    _ = set_anvil_account_balance(web3, user_account.address, eth_balance)
    # fund the user with Base
    base_balance = sum((int(budget) for budget in account_key_config.AGENT_BASE_BUDGETS)) * 2  # double for good measure
    _ = smart_contract_transact(
        web3,
        base_token_contract,
        user_account,
        "mint(address,uint256)",
        user_account.checksum_address,
        base_balance,
    )
    return user_account

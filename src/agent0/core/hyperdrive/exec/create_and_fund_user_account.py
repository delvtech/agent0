"""Create agent accounts and fund them."""

from __future__ import annotations

from typing import TYPE_CHECKING

from eth_account.account import Account

from agent0.core import AccountKeyConfig
from agent0.core.base.make_key import make_private_key
from agent0.core.hyperdrive import HyperdriveAgent
from agent0.ethpy.base import set_anvil_account_balance, smart_contract_transact
from agent0.ethpy.hyperdrive import HyperdriveReadInterface

if TYPE_CHECKING:
    from web3 import Web3
    from web3.types import RPCResponse, TxReceipt

    from agent0.hypertypes import ERC20MintableContract


def create_user_account() -> HyperdriveAgent:
    """Create a fake HyperdriveAgent.

    Returns
    -------
    HyperdriveAgent
        The fake user.
    """
    user_private_key = make_private_key(extra_entropy="FAKE USER")  # argument value can be any str
    user_account = HyperdriveAgent(Account().from_key(user_private_key))
    return user_account


def fund_user_account(
    web3: Web3,
    account_key_config: AccountKeyConfig,
    user_account: HyperdriveAgent,
    base_token_contract: ERC20MintableContract,
) -> tuple[RPCResponse, TxReceipt]:
    """Fund a user account.

    Arguments
    ---------
    web3: Web3
        Web3 provider object.
    account_key_config: AccountKeyConfig
        Configuration linking to the env file for storing private keys and initial budgets.
        Defines the agents to be funded.
    user_account: HyperdriveAgent
        Object containing a wallet address and Agent for determining trades
    base_token_contract: ERC20MintableContract
        The deployed ERC20 base token contract.

    Returns
    -------
    tuple[RPCResponse, TxReceipt]
        A tuple containing the RPC response from setting the anvil account eth balance
        and the transaction receipt from the mint() base token contract function call.
    """
    eth_balance = sum((int(budget) for budget in account_key_config.AGENT_ETH_BUDGETS)) * 2  # double for good measure
    rpc_response = set_anvil_account_balance(web3, user_account.address, eth_balance)
    # fund the user with Base
    base_balance = sum((int(budget) for budget in account_key_config.AGENT_BASE_BUDGETS)) * 2  # double for good measure
    tx_receipt = smart_contract_transact(
        web3,
        base_token_contract,
        user_account,
        "mint(address,uint256)",
        user_account.checksum_address,
        base_balance,
    )
    return rpc_response, tx_receipt


def create_and_fund_user_account(
    account_key_config: AccountKeyConfig,
    interface: HyperdriveReadInterface,
) -> HyperdriveAgent:
    """Helper function for funding a fake user account.

    Arguments
    ---------
    account_key_config: AccountKeyConfig
        Configuration linking to the env file for storing private keys and initial budgets.
        Defines the agents to be funded.
    interface: HyperdriveReadInterface
        The market on which this agent will be executing trades (MarketActions)

    Returns
    -------
    HyperdriveAgent
        An agent that corresponds to the fake "user"
    """
    # generate fake user account
    user_account = create_user_account()
    _ = fund_user_account(interface.web3, account_key_config, user_account, interface.base_token_contract)
    return user_account

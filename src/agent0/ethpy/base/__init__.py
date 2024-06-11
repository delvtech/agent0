"""Base utilities for working with contracts via web3"""

from .abi import load_abi_from_file, load_all_abis
from .errors import ABIError, UnknownBlockError, decode_error_selector_for_contract
from .receipts import get_event_object, get_transaction_logs
from .rpc_interface import get_account_balance, set_anvil_account_balance
from .transactions import (
    async_eth_transfer,
    async_smart_contract_transact,
    async_wait_for_transaction_receipt,
    eth_transfer,
    fetch_contract_transactions_for_block,
    smart_contract_preview_transaction,
    smart_contract_read,
    smart_contract_transact,
)
from .web3_setup import initialize_web3_with_http_provider

"""Base utilities for working with contracts via web3"""

from .rpc_interface import get_account_balance, set_account_balance
from .transactions import async_wait_for_transaction_receipt
from .web3_setup import initialize_web3_with_http_provider

# The contract address of ethereum on mainnet chain
ETH_CONTRACT_ADDRESS = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"

# We define the earliest block to look for hyperdrive initialize events
# based on chain id (retrieved from web3.eth.chain_id()).
EARLIEST_BLOCK_LOOKUP = {
    # Ethereum
    1: 20180600,
    # Sepolia
    111545111: 6137300,
    # Gnosis
    100: 35732200,
    # Gnosis fork
    42070: 35730000,
    # Linea
    59144: 9245000,
    # Base
    8453: 19730000,
}

from web3.contract.contract import Contract

from fixedpointmath import FixedPoint

from elfpy.data import contract_interface as ci

# define constants
ETHEREUM_NODE = "http://localhost:8545"
CONTRACTS_URL = "http://localhost:80/addresses.json"
BUILD_FOLDER = "./hyperdrive_solidity/.build"
HYPERDRIVE_ABI = "IHyperdrive"
BASE_ABI = "ERC20Mintable"

initial_supply = int(10e18)  # wei
initial_apr = int(0.1e18)
extra_entropy = "BEEP BOOP"

# generate the contract object
web3 = ci.initialize_web3_with_http_provider(ETHEREUM_NODE)
tx_receipt = web3.provider.make_request(method="anvil_reset", params=[])
print(f"\n{web3.eth.gas_price=}")
print(f"{web3.eth.accounts=}")

# get abis & addresses from the Hyperdrive ABI
hyperdrive_abis = ci.load_all_abis(BUILD_FOLDER)
addresses = ci.fetch_address_from_url(CONTRACTS_URL)
print(f"\nhyperdrive contract {addresses=}")

# set up the ERC20 contract for minting base tokens
base_token_contract: Contract = web3.eth.contract(abi=hyperdrive_abis[BASE_ABI], address=addresses.base_token)
print(f"{base_token_contract.functions.totalSupply().call()=}")

# make meta account for paying for approval gas
meta_account = web3.eth.accounts[0]

# check token blance
meta_token_balance = ci.get_account_balance_from_contract(base_token_contract, meta_account)
print(f"\nbase token balance for {meta_account=}:\n\t{meta_token_balance=}")
# check meta account before setting
meta_ether_balance = ci.get_account_balance_from_provider(web3, meta_account)
print(f"ether balance for {meta_account=}:\n\t{meta_ether_balance=}")

# set and check again
meta_funding_amount = int(web3.to_wei(148, "ether"))
rpc_response = ci.set_account_balance(web3, meta_account, meta_funding_amount)
meta_ether_balance = ci.get_account_balance_from_provider(web3, meta_account)
print(f"ether balance after setting for {meta_account=}:\n\t{meta_ether_balance=}")

# set up a test account for initializing the hyperdrive market
test_account = ci.TestAccount(extra_entropy)

# check test account ether balance
test_ether_balance = ci.get_account_balance_from_provider(web3, test_account.checksum_address)
print(f"\nether balance for acccount {test_account.checksum_address=}:\n\t{test_ether_balance=}")
# fund test account with ether
rpc_response = ci.set_account_balance(web3, test_account.checksum_address, int(web3.to_wei(1000, "ether")))
test_ether_balance = ci.get_account_balance_from_provider(web3, test_account.checksum_address)
print(f"ether balance for acccount {test_account.checksum_address=}:\n\t{test_ether_balance=}")

# check token balance
test_token_balance = ci.get_account_balance_from_contract(base_token_contract, test_account.checksum_address)
print(f"token balance for acccount {test_account.checksum_address=}:\n\t{test_token_balance=}")
# fund test account by minting with the ERC20 base account
tx_receipt = ci.mint_tokens(base_token_contract, test_account.checksum_address, initial_supply)
test_token_balance = ci.get_account_balance_from_contract(base_token_contract, test_account.checksum_address)
print(f"token balance AFTER funding for account {test_account.checksum_address=}:\n\t{test_token_balance=}")

# set up hyperdrive contract
hyperdrive_contract: Contract = web3.eth.contract(
    abi=hyperdrive_abis[HYPERDRIVE_ABI],
    address=addresses.mock_hyperdrive,
)


# function to approve hyperdrive contract to withdraw from the base contract
tx_receipt = ci.smart_contract_transact(
    web3, base_token_contract, "approve", test_account, hyperdrive_contract.address, initial_supply
)

# initialize hyperdrive
tx_receipt = ci.smart_contract_transact(
    web3,
    hyperdrive_contract,
    "initialize",
    test_account,
    initial_supply,
    initial_apr,
    test_account.checksum_address,
    True,
)

test_token_balance = ci.get_account_balance_from_contract(base_token_contract, test_account.checksum_address)
print(f"token balance initializing hyperdrive for account {test_account.checksum_address=}:\n\t{test_token_balance=}")

pool_info_data_dict = ci.smart_contract_read_call(hyperdrive_contract, "getPoolInfo")
share_reserves = FixedPoint(scaled_value=pool_info_data_dict["shareReserves"])
share_price = FixedPoint(scaled_value=pool_info_data_dict["sharePrice"])
initial_supply = FixedPoint(scaled_value=initial_supply)
print(f"\n{pool_info_data_dict=}")
print(f"\n{share_reserves=}")
print(f"{initial_supply * share_price=}")
print(f"{(share_reserves - (initial_supply * share_price))=}")


# Helper functions:
# sc read call
# sc write call
# add retries

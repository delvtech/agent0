from web3.contract.contract import Contract

from fixedpointmath import FixedPoint

from elfpy.data import contract_interface as ci

ETHEREUM_NODE = "http://localhost:8545"
CONTRACTS_URL = "http://localhost:80/addresses.json"
BUILD_FOLDER = "./hyperdrive_solidity/.build"
HYPERDRIVE_ABI = "IHyperdrive"
BASE_ABI = "ERC20Mintable"

initial_supply = int(10e18)  # wei
initial_apr = int(0.1e18)
extra_entropy = "BEEP BOOP"

# Generate the contract object
web3 = ci.initialize_web3_with_http_provider(ETHEREUM_NODE)
print(f"\n{web3.eth.gas_price=}")
print(f"{web3.eth.accounts=}")

# get abis & addresses from the Hyperdrive ABI
hyperdrive_abis = ci.load_all_abis(BUILD_FOLDER)
addresses = ci.fetch_address_from_url(CONTRACTS_URL)
print(f"\nhyperdrive contract {addresses=}")

# set up the ERC20 contract for minting base tokens
funding_contract: Contract = web3.eth.contract(abi=hyperdrive_abis[BASE_ABI], address=addresses.base_token)
print(f"{funding_contract.functions.totalSupply().call()=}")

# make meta account for paying for approval gas
meta_account = web3.eth.accounts[0]  # FIXME: What to do if anvil is not supplying accounts?

# FIXME: This does not work -- meta account balance does not change after `set_account_balance`
meta_account_balance = ci.get_account_balance_from_contract(funding_contract, meta_account)
print(f"\nBEFORE funding {meta_account=}:\n{meta_account_balance=}")
meta_funding_amount = int(web3.to_wei(1, "ether"))
print(f"{meta_funding_amount=}")
tx_receipt = ci.set_account_balance(web3, meta_account, meta_funding_amount)
meta_account_balance = ci.get_account_balance_from_contract(funding_contract, meta_account)
print(f"AFTER funding {meta_account=}:\n{meta_account_balance=}")

# initialize the hyperdrive contract
hyperdrive_contract: Contract = web3.eth.contract(
    abi=hyperdrive_abis[HYPERDRIVE_ABI],
    address=addresses.mock_hyperdrive,
)

# function to approve hyperdrive contract to withdraw from the base contract
func_handle = funding_contract.functions.approve(hyperdrive_contract.address, initial_supply)

# estimate gas for the function
gas = func_handle.estimate_gas({"from": meta_account}) * web3.eth.gas_price
print(f"\nHyperdrive initialize estimated {gas/1e18=}")

# set up a test account for initializing the hyperdrive market
test_account = ci.TestAccount(extra_entropy)
test_account_balance = ci.get_account_balance_from_contract(funding_contract, test_account.address)
print(f"\nBEFORE funding {test_account.address=}:\n{test_account_balance=}")

# fund test account from the ERC20 mint account
funding_amount = initial_supply + 2 * gas  # double gas jic
tx_receipt = ci.fund_account(web3, funding_contract, test_account.address, funding_amount, meta_account)
test_account_balance = ci.get_account_balance_from_contract(funding_contract, test_account.address)
print(f"AFTER funding {test_account.address=}:\n{test_account_balance=}")

# FIXME: This fails if I use `"from": test_account` and succeeds if I use `"from": meta_account`, regardless of the test account balance
tx_hash = func_handle.transact(
    {
        "type": "0x2",  # dynamic fee transaction
        "from": meta_account,  # who is providing the funds
        "maxPriorityFeePerGas": 0,  # tip; maxFeePerGas = baseFeePerGas + maxPriorityFeePerGas
    }
)
# wait for approval to complete
tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

# FIXME: Hyperdrive appears to be initialized, but
# 1. the account balance does not go down
print(f"\n{ci.get_account_balance_from_contract(funding_contract, test_account.address)=}")
print(f"{ci.get_account_balance_from_contract(funding_contract, meta_account)=}")

# 2. the share reserves does not match the initial supply * the share price
pool_info_data_dict = ci.smart_contract_read_call(hyperdrive_contract, "getPoolInfo")
share_reserves = FixedPoint(scaled_value=pool_info_data_dict["shareReserves"])
share_price = FixedPoint(scaled_value=pool_info_data_dict["sharePrice"])
initial_supply = FixedPoint(scaled_value=initial_supply)
print(f"\n{pool_info_data_dict=}")
print(f"\n{share_reserves=}")
print(f"{initial_supply * share_price=}")
print(f"{(share_reserves - (initial_supply * share_price))=}")


# TODO:
# def smart_contract_transact(contract, function_name: str, from_address, kwargs):
#    tx_hash = contract.functions.get_attr(function_name)(**kwargs).transact({"from": from_address})
#    # wait for approval to complete
#    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
#    return tx_receipt

"""Sample usage of erc20Contract."""

from pypechain.sample.ERC20Contract import ERC20Contract

# instantiate the contract
erc20Contract = ERC20Contract(address=None)

# get the function, with typehints and autocomplete!
allowance_function = erc20Contract.functions.allowance("0xOWNER", "0xSPENDER")
allowance_function = erc20Contract.functions.allowance("0xOWNER", "Ox")

# call the function
result = allowance_function.call()

# get the function, with typehints and autocomplete!

# perform a transaction
tx_hash = allowance_function.transact()

# get the result
# result = allowance_function.get_result(tx_hash)

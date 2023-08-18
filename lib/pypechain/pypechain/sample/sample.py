"""Sample usage of erc20Contract."""

from pypechain.sample.ERC20Contract import ERC20Contract

# instantiate the contract
erc20Contract = ERC20Contract(address=None)

# get the function, with typehints and autocomplete!
fn = erc20Contract.functions.allowance("0xOWNER", "0xSPENDER")
# call the function
result = fn.call()


# get the function, with typehints and autocomplete!
fn = erc20Contract.functions.approve("0x00", 1)
# call the function
result = fn.call()

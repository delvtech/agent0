"""Sample usage of erc20Contract."""

from build.ERC20Contract import ERC20Contract

erc20Contract = ERC20Contract(address=None)

fn = erc20Contract.functions.allowance("0xOWNER", "0xSPENDER").call()
result = erc20Contract.functions.approve("0x00", 1).call()

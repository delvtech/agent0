"""Bots on Hyperdrive testnet."""

# %%
# Variables by themselves print out dataframes in a nice format in interactive mode
# pylint: disable=pointless-statement
# We expect this to be a script, hence no need for uppercase naming
# pylint: disable=invalid-name
# TODO: add _contract to _pool
# pylint: disable=protected-access

import logging
import os
import time

import numpy as np
from agent0 import IChain, IHyperdrive, PolicyZoo
from agent0.core.base.config import EnvironmentConfig
from agent0.ethpy import build_eth_config
from agent0.ethpy.base import initialize_web3_with_http_provider, smart_contract_transact
from agent0.hypertypes import IHyperdriveContract
from dotenv import load_dotenv
from eth_typing import ChecksumAddress, HexAddress, HexStr
from fixedpointmath import FixedPoint

# %%
# config
load_dotenv()
RANDOM_DAI_14_PRIVATE_KEY = os.getenv("RANDOM_DAI_14")
RANDOM_DAI_30_PRIVATE_KEY = os.getenv("RANDOM_DAI_30")
RANDOM_STETH_14_PRIVATE_KEY = os.getenv("RANDOM_STETH_14")
RANDOM_STETH_30_PRIVATE_KEY = os.getenv("RANDOM_STETH_30")
ARBITRAGE_DAI_PRIVATE_KEY = os.getenv("ARBITRAGE_DAI")
ARBITRAGE_STETH_PRIVATE_KEY = os.getenv("ARBITRAGE_STETH")
SEPOLIA_ENDPOINT = os.getenv("SEPOLIA_ENDPOINT")
CLOUDCHAIN_ENDPOINT = os.getenv("CLOUDCHAIN_ENDPOINT")
CLOUDCHAIN_PRIVATE_KEY = os.getenv("CLOUDCHAIN_PRIVATE_KEY")
assert isinstance(RANDOM_DAI_14_PRIVATE_KEY, str)
assert isinstance(RANDOM_DAI_30_PRIVATE_KEY, str)
assert isinstance(RANDOM_STETH_14_PRIVATE_KEY, str)
assert isinstance(RANDOM_STETH_30_PRIVATE_KEY, str)
assert isinstance(ARBITRAGE_DAI_PRIVATE_KEY, str)
assert isinstance(ARBITRAGE_STETH_PRIVATE_KEY, str)
assert isinstance(SEPOLIA_ENDPOINT, str)
assert isinstance(CLOUDCHAIN_ENDPOINT, str)
assert isinstance(CLOUDCHAIN_PRIVATE_KEY, str)
TARGET_BASE = 10_000
TARGET_STETH = 500
GAS_LIMIT = 1_000_000
RANDSEED = 123
RANDOM_TRADE_CHANCE = 0.04  # every 5 minutes on average
TIMEOUT = 600  # seconds to wait for a transaction receipt

# Get the configuration and initialize the web3 provider.
eth_config = build_eth_config()

# The configuration for the checkpoint bot halts on errors and logs to stdout.
env_config = EnvironmentConfig(
    # Errors
    halt_on_errors=True,
    # Logging
    log_stdout=True,
    log_level=logging.INFO,
)

# %%
# prepare chain and contracts
chain = IChain(SEPOLIA_ENDPOINT)
web3 = initialize_web3_with_http_provider(SEPOLIA_ENDPOINT, reset_provider=False)
dai_abi = '[{"inputs":[{"internalType":"string","name":"name","type":"string"},{"internalType":"string","name":"symbol","type":"string"},{"internalType":"uint8","name":"decimals","type":"uint8"},{"internalType":"address","name":"admin","type":"address"},{"internalType":"bool","name":"isCompetitionMode_","type":"bool"},{"internalType":"uint256","name":"maxMintAmount_","type":"uint256"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"contract Authority","name":"newAuthority","type":"address"}],"name":"AuthorityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"PublicCapabilityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint8","name":"role","type":"uint8"},{"indexed":true,"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"RoleCapabilityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"target","type":"address"},{"indexed":true,"internalType":"contract Authority","name":"authority","type":"address"}],"name":"TargetCustomAuthorityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"uint8","name":"role","type":"uint8"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"UserRoleUpdated","type":"event"},{"inputs":[],"name":"DOMAIN_SEPARATOR","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"authority","outputs":[{"internalType":"contract Authority","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"destination","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"address","name":"target","type":"address"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"}],"name":"canCall","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"}],"name":"doesRoleHaveCapability","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint8","name":"role","type":"uint8"}],"name":"doesUserHaveRole","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"name":"getRolesWithCapability","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"getTargetCustomAuthority","outputs":[{"internalType":"contract Authority","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"getUserRoles","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"name":"isCapabilityPublic","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"isCompetitionMode","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"maxMintAmount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"destination","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"nonces","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"permit","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"contract Authority","name":"newAuthority","type":"address"}],"name":"setAuthority","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setPublicCapability","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setRoleCapability","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"target","type":"address"},{"internalType":"contract Authority","name":"customAuthority","type":"address"}],"name":"setTargetCustomAuthority","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setUserRole","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"}]'
dai_contract = web3.eth.contract(ChecksumAddress(HexAddress(HexStr("0x552ceaDf3B47609897279F42D3B3309B604896f3"))), abi=dai_abi)
dai_contract.name = "Dai"
steth_abi = '[{"inputs":[{"internalType":"uint256","name":"_initialRate","type":"uint256"},{"internalType":"address","name":"_admin","type":"address"},{"internalType":"bool","name":"_isCompetitionMode","type":"bool"},{"internalType":"uint256","name":"_maxMintAmount","type":"uint256"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"contract Authority","name":"newAuthority","type":"address"}],"name":"AuthorityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"PublicCapabilityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint8","name":"role","type":"uint8"},{"indexed":true,"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"RoleCapabilityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"target","type":"address"},{"indexed":true,"internalType":"contract Authority","name":"authority","type":"address"}],"name":"TargetCustomAuthorityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"uint8","name":"role","type":"uint8"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"UserRoleUpdated","type":"event"},{"inputs":[],"name":"DOMAIN_SEPARATOR","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"authority","outputs":[{"internalType":"contract Authority","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"destination","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"address","name":"target","type":"address"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"}],"name":"canCall","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"}],"name":"doesRoleHaveCapability","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint8","name":"role","type":"uint8"}],"name":"doesUserHaveRole","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getBufferedEther","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"uint256","name":"_sharesAmount","type":"uint256"}],"name":"getPooledEthByShares","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getRate","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"name":"getRolesWithCapability","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_ethAmount","type":"uint256"}],"name":"getSharesByPooledEth","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"getTargetCustomAuthority","outputs":[{"internalType":"contract Authority","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getTotalPooledEther","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getTotalShares","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"getUserRoles","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"name":"isCapabilityPublic","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"isCompetitionMode","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"maxMintAmount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"destination","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"nonces","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"permit","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"contract Authority","name":"newAuthority","type":"address"}],"name":"setAuthority","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setPublicCapability","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_rate_","type":"uint256"}],"name":"setRate","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setRoleCapability","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"target","type":"address"},{"internalType":"contract Authority","name":"customAuthority","type":"address"}],"name":"setTargetCustomAuthority","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setUserRole","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_account","type":"address"}],"name":"sharesOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"submit","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"payable","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_recipient","type":"address"},{"internalType":"uint256","name":"_sharesAmount","type":"uint256"}],"name":"transferShares","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_sender","type":"address"},{"internalType":"address","name":"_recipient","type":"address"},{"internalType":"uint256","name":"_sharesAmount","type":"uint256"}],"name":"transferSharesFrom","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}]'
steth_contract = web3.eth.contract(ChecksumAddress(HexAddress(HexStr("0x6977eC5fae3862D3471f0f5B6Dcc64cDF5Cfd959"))), abi=steth_abi)
steth_contract.name = "stETH"
dai_14_address = ChecksumAddress(HexAddress(HexStr("0x392839dA0dACAC790bd825C81ce2c5E264D793a8")))
dai_30_address = ChecksumAddress(HexAddress(HexStr("0xb932F8085399C228b16A9F7FC3219d47FfA2810d")))
steth_14_address = ChecksumAddress(HexAddress(HexStr("0xff33bd6d7ED4119c99C310F3e5f0Fa467796Ee23")))
steth_30_address = ChecksumAddress(HexAddress(HexStr("0x4E38fd41c03ff11b3426efaE53138b86116797b8")))
rng_generator = np.random.default_rng(RANDSEED)
hyperdrive_config = IHyperdrive.Config(preview_before_trade=True, rng=rng_generator, txn_receipt_timeout=TIMEOUT)
dai_14_pool = IHyperdrive(chain, dai_14_address, hyperdrive_config)
dai_30_pool = IHyperdrive(chain, dai_30_address, hyperdrive_config)
steth_14_pool = IHyperdrive(chain, steth_14_address, hyperdrive_config)
steth_30_pool = IHyperdrive(chain, steth_30_address, hyperdrive_config)
dai_14_contract = IHyperdriveContract.factory(w3=web3)(dai_14_address)
dai_30_contract = IHyperdriveContract.factory(w3=web3)(dai_30_address)
steth_14_contract = IHyperdriveContract.factory(w3=web3)(steth_14_address)
steth_30_contract = IHyperdriveContract.factory(w3=web3)(steth_30_address)
pools = [dai_14_pool, dai_30_pool, steth_14_pool, steth_30_pool]

# %%
# make agents
kwargs = {
    "gas_limit": GAS_LIMIT,
    "trade_chance": RANDOM_TRADE_CHANCE,
    "lp_portion": FixedPoint("0.0"),
}
random_dai_14 = dai_14_pool.init_agent(
    private_key=RANDOM_DAI_14_PRIVATE_KEY,
    policy=PolicyZoo.lp_and_arb,
    policy_config=PolicyZoo.lp_and_arb.Config(min_trade_amount_bonds=dai_14_pool.interface.pool_config.minimum_transaction_amount,**kwargs),
)
random_dai_14.agent.TARGET_BASE = FixedPoint(TARGET_BASE)
random_dai_14.agent.name = "random_dai14"
random_dai_14._pool._contract = dai_14_contract
random_dai_14._pool._token = dai_contract

random_dai_30 = dai_30_pool.init_agent(
    private_key=RANDOM_DAI_30_PRIVATE_KEY,
    policy=PolicyZoo.lp_and_arb,
    policy_config=PolicyZoo.lp_and_arb.Config(min_trade_amount_bonds=dai_30_pool.interface.pool_config.minimum_transaction_amount,**kwargs),
)
random_dai_30.agent.TARGET_BASE = FixedPoint(TARGET_BASE)
random_dai_30._pool._contract = dai_30_contract
random_dai_30._pool._token = dai_contract
random_dai_30.agent.name = "random_dai30"

random_steth_14 = steth_14_pool.init_agent(
    private_key=RANDOM_STETH_14_PRIVATE_KEY,
    policy=PolicyZoo.lp_and_arb,
    policy_config=PolicyZoo.lp_and_arb.Config(min_trade_amount_bonds=steth_14_pool.interface.pool_config.minimum_transaction_amount,**kwargs),
)
random_steth_14.agent.TARGET_BASE = FixedPoint(TARGET_STETH)
random_steth_14._pool._contract = steth_14_contract
random_steth_14._pool._token = steth_contract
random_steth_14.agent.name = "random_steth14"

random_steth_30 = steth_30_pool.init_agent(
    private_key=RANDOM_STETH_30_PRIVATE_KEY,
    policy=PolicyZoo.lp_and_arb,
policy_config=PolicyZoo.lp_and_arb.Config(min_trade_amount_bonds=steth_30_pool.interface.pool_config.minimum_transaction_amount,**kwargs),
)
random_steth_30.agent.TARGET_BASE = FixedPoint(TARGET_STETH)
random_steth_30._pool._contract = steth_30_contract
random_steth_30._pool._token = steth_contract
random_steth_30.agent.name = "random_steth30"

agents = [random_dai_14, random_dai_30, random_steth_14, random_steth_30]

# %%
# report agents
for agent in agents:
    print(f"{agent.agent.name:<14} ({agent.agent.checksum_address}) BASE={float(agent.agent.wallet.balance.amount):,.0f} ETH={web3.eth.get_balance(agent.agent.checksum_address)/1e18:,.5f}")

 # %%
# prepare agents
print("preparing agents..")
for agent in agents:
    starting_balance = agent.agent.wallet.balance.amount
    # top up wallets
    if starting_balance < agent.agent.TARGET_BASE:
        print(f"MINT by {agent.agent.name:<14} ({agent.agent.checksum_address}) of {float(agent.agent.TARGET_BASE):,.0f}..", end="")
        fn_args = [agent.agent.TARGET_BASE.scaled_value]
        receipt = smart_contract_transact(web3,agent._pool._token,agent.agent,"mint(uint256)",timeout = TIMEOUT,*fn_args)
        print("success!")
        print(f"checking {agent._pool._token} balance of {agent.agent.name:<14} ({agent.agent.checksum_address})..", end="")
        base_from_chain = agent._pool._token.functions.balanceOf(agent.agent.checksum_address).call()
        print("success!")
        agent.agent.wallet.balance.amount = FixedPoint(scaled_value=base_from_chain)

        print(f"Balance of {agent.agent.name:<14} ({agent.agent.checksum_address}) topped up to {agent.agent.wallet.balance.amount}")
    else:
        print(f"{agent.agent.name:<14} ({agent.agent.checksum_address}) is good to go!")

# %%
# report agents again
for agent in agents:
    print(f"{agent.agent.name:<14} ({agent.agent.checksum_address}) BASE={float(agent.agent.wallet.balance.amount):,.0f} ETH={web3.eth.get_balance(agent.agent.checksum_address)/1e18:,.5f}")

# %%
# check latest block
previous_block = web3.eth.get_block("latest")
print(f"current block  = {previous_block['number']}")
while True:
    print("waiting for new block..", end="")
    while (latest_block := web3.eth.get_block("latest")) == previous_block:
        print(".", end="")
        time.sleep(1)
    print(f"{latest_block['number']}")
    for agent in agents:
        print(f"{agent.agent.name:<14} ({agent.agent.checksum_address}) BASE={float(agent.agent.wallet.balance.amount):,.0f} ETH={web3.eth.get_balance(agent.agent.checksum_address)/1e18:,.5f}")
        print(f"{agent._pool}")
        event_list = agent.execute_policy_action()
        for event in event_list:
            print(f"agent {agent.agent.name}({agent.agent.checksum_address}) decided to trade: {event}")
            print(event)
    previous_block = latest_block

# %%
# manual stuff
# receipt = random_dai_30.open_short(
#     bonds=FixedPoint(1128.792526128924983296),
# )
# print(f"{receipt=}")

# %%

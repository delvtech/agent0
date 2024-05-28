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
from agent0.core.hyperdrive import HyperdriveAgent
from agent0.ethpy import build_eth_config
from agent0.ethpy.base import initialize_web3_with_http_provider, smart_contract_transact
from agent0.hypertypes import IHyperdriveContract
from dotenv import load_dotenv
from eth_typing import ChecksumAddress, HexAddress, HexStr
from fixedpointmath import FixedPoint

# pylint: disable=redefined-outer-name

# %%
# config
load_dotenv()
BASE_FEE_MULTIPLE = 10
PRIORITY_FEE_MULTIPLE = 2
DAI_14_PRIVATE_KEY = os.getenv("DAI_14")
DAI_30_PRIVATE_KEY = os.getenv("DAI_30")
STETH_14_PRIVATE_KEY = os.getenv("STETH_14")
STETH_30_PRIVATE_KEY = os.getenv("STETH_30")
SEPOLIA_ENDPOINT = os.getenv("SEPOLIA_ENDPOINT")
CLOUDCHAIN_ENDPOINT = os.getenv("CLOUDCHAIN_ENDPOINT")
CLOUDCHAIN_PRIVATE_KEY = os.getenv("CLOUDCHAIN_PRIVATE_KEY")
assert isinstance(DAI_14_PRIVATE_KEY, str)
assert isinstance(DAI_30_PRIVATE_KEY, str)
assert isinstance(STETH_14_PRIVATE_KEY, str)
assert isinstance(STETH_30_PRIVATE_KEY, str)
assert isinstance(SEPOLIA_ENDPOINT, str)
assert isinstance(CLOUDCHAIN_ENDPOINT, str)
assert isinstance(CLOUDCHAIN_PRIVATE_KEY, str)
TARGET_BASE = 10_000
TARGET_ETH = 500
GAS_LIMIT = 1_000_000
RANDSEED = 123
RANDOM_TRADE_CHANCE = 0.1  # on average 1 bot trades every block (10 bots)
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
dai_contract = web3.eth.contract(ChecksumAddress(HexAddress(HexStr("0x8fb0c5a09438b36e42c6a7c7fd25b73c140ed3a3"))), abi=dai_abi)
dai_contract.name = "Dai"
steth_abi = '[{"inputs":[{"internalType":"uint256","name":"_initialRate","type":"uint256"},{"internalType":"address","name":"_admin","type":"address"},{"internalType":"bool","name":"_isCompetitionMode","type":"bool"},{"internalType":"uint256","name":"_maxMintAmount","type":"uint256"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"contract Authority","name":"newAuthority","type":"address"}],"name":"AuthorityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"PublicCapabilityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint8","name":"role","type":"uint8"},{"indexed":true,"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"RoleCapabilityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"target","type":"address"},{"indexed":true,"internalType":"contract Authority","name":"authority","type":"address"}],"name":"TargetCustomAuthorityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"uint8","name":"role","type":"uint8"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"UserRoleUpdated","type":"event"},{"inputs":[],"name":"DOMAIN_SEPARATOR","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"authority","outputs":[{"internalType":"contract Authority","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"destination","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"address","name":"target","type":"address"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"}],"name":"canCall","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"}],"name":"doesRoleHaveCapability","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint8","name":"role","type":"uint8"}],"name":"doesUserHaveRole","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getBufferedEther","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"uint256","name":"_sharesAmount","type":"uint256"}],"name":"getPooledEthByShares","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getRate","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"name":"getRolesWithCapability","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_ethAmount","type":"uint256"}],"name":"getSharesByPooledEth","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"getTargetCustomAuthority","outputs":[{"internalType":"contract Authority","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getTotalPooledEther","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getTotalShares","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"getUserRoles","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"name":"isCapabilityPublic","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"isCompetitionMode","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"maxMintAmount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"destination","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"nonces","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"permit","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"contract Authority","name":"newAuthority","type":"address"}],"name":"setAuthority","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setPublicCapability","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_rate_","type":"uint256"}],"name":"setRate","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setRoleCapability","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"target","type":"address"},{"internalType":"contract Authority","name":"customAuthority","type":"address"}],"name":"setTargetCustomAuthority","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setUserRole","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_account","type":"address"}],"name":"sharesOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"submit","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"payable","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_recipient","type":"address"},{"internalType":"uint256","name":"_sharesAmount","type":"uint256"}],"name":"transferShares","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_sender","type":"address"},{"internalType":"address","name":"_recipient","type":"address"},{"internalType":"uint256","name":"_sharesAmount","type":"uint256"}],"name":"transferSharesFrom","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}]'
steth_contract = web3.eth.contract(ChecksumAddress(HexAddress(HexStr("0x60ccc29ee65d935d47bf2916568320815f96c3b2"))), abi=steth_abi)
steth_contract.name = "stETH"
reth_abi = '[{"inputs":[{"internalType":"uint256","name":"_initialRate","type":"uint256"},{"internalType":"address","name":"_admin","type":"address"},{"internalType":"bool","name":"_isCompetitionMode","type":"bool"},{"internalType":"uint256","name":"_maxMintAmount","type":"uint256"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"contract Authority","name":"newAuthority","type":"address"}],"name":"AuthorityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"PublicCapabilityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint8","name":"role","type":"uint8"},{"indexed":true,"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"RoleCapabilityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"target","type":"address"},{"indexed":true,"internalType":"contract Authority","name":"authority","type":"address"}],"name":"TargetCustomAuthorityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"uint8","name":"role","type":"uint8"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"UserRoleUpdated","type":"event"},{"inputs":[],"name":"DOMAIN_SEPARATOR","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"authority","outputs":[{"internalType":"contract Authority","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"destination","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"address","name":"target","type":"address"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"}],"name":"canCall","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"}],"name":"doesRoleHaveCapability","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint8","name":"role","type":"uint8"}],"name":"doesUserHaveRole","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_rethAmount","type":"uint256"}],"name":"getEthValue","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getRate","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_ethAmount","type":"uint256"}],"name":"getRethValue","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"name":"getRolesWithCapability","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"getTargetCustomAuthority","outputs":[{"internalType":"contract Authority","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getTotalPooledEther","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getTotalShares","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"getUserRoles","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"name":"isCapabilityPublic","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"isCompetitionMode","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"isUnrestricted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"maxMintAmount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"destination","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"nonces","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"permit","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"contract Authority","name":"newAuthority","type":"address"}],"name":"setAuthority","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_maxMintAmount","type":"uint256"}],"name":"setMaxMintAmount","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setPublicCapability","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_rate_","type":"uint256"}],"name":"setRate","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setRoleCapability","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"target","type":"address"},{"internalType":"contract Authority","name":"customAuthority","type":"address"}],"name":"setTargetCustomAuthority","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_target","type":"address"},{"internalType":"bool","name":"_status","type":"bool"}],"name":"setUnrestrictedMintStatus","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setUserRole","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"submit","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"payable","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_recipient","type":"address"},{"internalType":"uint256","name":"_sharesAmount","type":"uint256"}],"name":"transferShares","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_sender","type":"address"},{"internalType":"address","name":"_recipient","type":"address"},{"internalType":"uint256","name":"_sharesAmount","type":"uint256"}],"name":"transferSharesFrom","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}]'
reth_contract = web3.eth.contract(ChecksumAddress(HexAddress(HexStr("0xf4a3178bc28dae9a842837a3421f8652cbcdf7bf"))), abi=reth_abi)
reth_contract.name = "rEth"
ezeth_abi = '[{"inputs":[{"internalType":"uint256","name":"_initialRate","type":"uint256"},{"internalType":"address","name":"_admin","type":"address"},{"internalType":"bool","name":"_isCompetitionMode","type":"bool"},{"internalType":"uint256","name":"_maxMintAmount","type":"uint256"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[],"name":"InvalidTokenAmount","type":"error"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"contract Authority","name":"newAuthority","type":"address"}],"name":"AuthorityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"PublicCapabilityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint8","name":"role","type":"uint8"},{"indexed":true,"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"RoleCapabilityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"target","type":"address"},{"indexed":true,"internalType":"contract Authority","name":"authority","type":"address"}],"name":"TargetCustomAuthorityUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"user","type":"address"},{"indexed":true,"internalType":"uint8","name":"role","type":"uint8"},{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"UserRoleUpdated","type":"event"},{"inputs":[],"name":"DOMAIN_SEPARATOR","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"authority","outputs":[{"internalType":"contract Authority","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"destination","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_currentValueInProtocol","type":"uint256"},{"internalType":"uint256","name":"_newValueAdded","type":"uint256"},{"internalType":"uint256","name":"_existingEzETHSupply","type":"uint256"}],"name":"calculateMintAmount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"uint256","name":"_ezETHBeingBurned","type":"uint256"},{"internalType":"uint256","name":"_existingEzETHSupply","type":"uint256"},{"internalType":"uint256","name":"_currentValueInProtocol","type":"uint256"}],"name":"calculateRedeemAmount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[],"name":"calculateTVLs","outputs":[{"internalType":"uint256[][]","name":"","type":"uint256[][]"},{"internalType":"uint256[]","name":"","type":"uint256[]"},{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"address","name":"target","type":"address"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"}],"name":"canCall","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"depositETH","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"}],"name":"doesRoleHaveCapability","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint8","name":"role","type":"uint8"}],"name":"doesUserHaveRole","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"ezETH","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getBufferedEther","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"uint256","name":"_sharesAmount","type":"uint256"}],"name":"getPooledEthByShares","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getRate","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"name":"getRolesWithCapability","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_ethAmount","type":"uint256"}],"name":"getSharesByPooledEth","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"getTargetCustomAuthority","outputs":[{"internalType":"contract Authority","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getTotalPooledEther","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getTotalShares","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"getUserRoles","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"name":"isCapabilityPublic","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"isCompetitionMode","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"isUnrestricted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"contract IERC20","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"lookupTokenAmountFromValue","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"contract IERC20","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"lookupTokenValue","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"contract IERC20[]","name":"","type":"address[]"},{"internalType":"uint256[]","name":"","type":"uint256[]"}],"name":"lookupTokenValues","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[],"name":"maxMintAmount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"destination","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"nonces","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"permit","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"renzoOracle","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"contract Authority","name":"newAuthority","type":"address"}],"name":"setAuthority","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_maxMintAmount","type":"uint256"}],"name":"setMaxMintAmount","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setPublicCapability","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_rate_","type":"uint256"}],"name":"setRate","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bytes4","name":"functionSig","type":"bytes4"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setRoleCapability","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"target","type":"address"},{"internalType":"contract Authority","name":"customAuthority","type":"address"}],"name":"setTargetCustomAuthority","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_target","type":"address"},{"internalType":"bool","name":"_status","type":"bool"}],"name":"setUnrestrictedMintStatus","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint8","name":"role","type":"uint8"},{"internalType":"bool","name":"enabled","type":"bool"}],"name":"setUserRole","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_account","type":"address"}],"name":"sharesOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"submit","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"payable","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalPooledEther","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalShares","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_recipient","type":"address"},{"internalType":"uint256","name":"_sharesAmount","type":"uint256"}],"name":"transferShares","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_sender","type":"address"},{"internalType":"address","name":"_recipient","type":"address"},{"internalType":"uint256","name":"_sharesAmount","type":"uint256"}],"name":"transferSharesFrom","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}]'
ezeth_contract = web3.eth.contract(ChecksumAddress(HexAddress(HexStr("0x3b57e3b2531a376ee5b248943bb6de99e333bb5d"))), abi=ezeth_abi)
ezeth_contract.name = "ezETH"
dai_14_address = ChecksumAddress(HexAddress(HexStr("0x0776F49B14718Fd735F74aAe8eAa9782730115c3")))
dai_30_address = ChecksumAddress(HexAddress(HexStr("0xC2dedf898EFd2a3c0467d37f08bb38dd212E2DAC")))
steth_14_address = ChecksumAddress(HexAddress(HexStr("0x74B556fbD2284c2aa7c673773572303E161E153B")))
steth_30_address = ChecksumAddress(HexAddress(HexStr("0xe74F13a3E38f1a0bD867255B547d837cbCF2e8Aa")))
reth_14_address = ChecksumAddress(HexAddress(HexStr("0xA975225D750dFC948171710739F1b3BBAd5d7451")))
reth_30_address = ChecksumAddress(HexAddress(HexStr("0x5a28f5Dc994d231DBfdcF3Eb7F450f5bdF55d3A9")))
ezeth_14_address = ChecksumAddress(HexAddress(HexStr("0xdeC715C6EAbad704A50deCB400bb18Ef4cde2240")))
ezeth_30_address = ChecksumAddress(HexAddress(HexStr("0x496c57E03B63911ED37cd1ffc95d49b60AA22107")))
morpho_14_address = ChecksumAddress(HexAddress(HexStr("0x2F8702a0f20Bd6C152381D59a39DBe8cA87db9c2")))
morpho_30_address = ChecksumAddress(HexAddress(HexStr("0xb4E605E079B4D9ed50B7202Ca0d008EE473A8de4")))\
rng_generator = np.random.default_rng(RANDSEED)
hyperdrive_config = IHyperdrive.Config(
    preview_before_trade=True,
    rng=rng_generator,
    txn_receipt_timeout=TIMEOUT,
    txn_options_base_fee_multiple=BASE_FEE_MULTIPLE,
    txn_options_priority_fee_multiple=PRIORITY_FEE_MULTIPLE,
)

# initialize pools
dai_14_pool = IHyperdrive(chain, dai_14_address, hyperdrive_config)
dai_30_pool = IHyperdrive(chain, dai_30_address, hyperdrive_config)
steth_14_pool = IHyperdrive(chain, steth_14_address, hyperdrive_config)
steth_30_pool = IHyperdrive(chain, steth_30_address, hyperdrive_config)
reth_14_pool = IHyperdrive(chain, reth_14_address, hyperdrive_config)
reth_30_pool = IHyperdrive(chain, reth_30_address, hyperdrive_config)
ezeth_14_pool = IHyperdrive(chain, ezeth_14_address, hyperdrive_config)
ezeth_30_pool = IHyperdrive(chain, ezeth_30_address, hyperdrive_config)
morpho_14_pool = IHyperdrive(chain, morpho_14_address, hyperdrive_config)
morpho_30_pool = IHyperdrive(chain, morpho_30_address, hyperdrive_config)

# initialize contracts
dai_14_contract = IHyperdriveContract.factory(w3=web3)(dai_14_address)
dai_30_contract = IHyperdriveContract.factory(w3=web3)(dai_30_address)
steth_14_contract = IHyperdriveContract.factory(w3=web3)(steth_14_address)
steth_30_contract = IHyperdriveContract.factory(w3=web3)(steth_30_address)
reth_14_contract = IHyperdriveContract.factory(w3=web3)(reth_14_address)
reth_30_contract = IHyperdriveContract.factory(w3=web3)(reth_30_address)
ezeth_14_contract = IHyperdriveContract.factory(w3=web3)(ezeth_14_address)
ezeth_30_contract = IHyperdriveContract.factory(w3=web3)(ezeth_30_address)
morpho_14_contract = IHyperdriveContract.factory(w3=web3)(morpho_14_address)
morpho_30_contract = IHyperdriveContract.factory(w3=web3)(morpho_30_address)

# concatenate pools
pools = [dai_14_pool, dai_30_pool, steth_14_pool, steth_30_pool, reth_14_pool, reth_30_pool, ezeth_14_pool, ezeth_30_pool, morpho_14_pool, morpho_30_pool]

# %%
# make agents
kwargs = {
    "gas_limit": GAS_LIMIT,
    "trade_chance": RANDOM_TRADE_CHANCE,
    "lp_portion": FixedPoint("0.0"),
}
DAI_14 = dai_14_pool.init_agent(
    private_key=DAI_14_PRIVATE_KEY,
    policy=PolicyZoo.lp_and_arb,
    policy_config=PolicyZoo.lp_and_arb.Config(min_trade_amount_bonds=dai_14_pool.interface.pool_config.minimum_transaction_amount * FixedPoint(2), **kwargs),
)
DAI_14.agent.TARGET_BASE = FixedPoint(TARGET_BASE)
DAI_14.agent.name = "dai14"
DAI_14._pool._contract = dai_14_contract
DAI_14._pool._token = dai_contract

DAI_30 = dai_30_pool.init_agent(
    private_key=DAI_30_PRIVATE_KEY,
    policy=PolicyZoo.lp_and_arb,
    policy_config=PolicyZoo.lp_and_arb.Config(min_trade_amount_bonds=dai_30_pool.interface.pool_config.minimum_transaction_amount * FixedPoint(2), **kwargs),
)
DAI_30.agent.TARGET_BASE = FixedPoint(TARGET_BASE)
DAI_30._pool._contract = dai_30_contract
DAI_30._pool._token = dai_contract
DAI_30.agent.name = "dai30"

STETH_14 = steth_14_pool.init_agent(
    private_key=STETH_14_PRIVATE_KEY,
    policy=PolicyZoo.lp_and_arb,
    policy_config=PolicyZoo.lp_and_arb.Config(min_trade_amount_bonds=steth_14_pool.interface.pool_config.minimum_transaction_amount * FixedPoint(2), **kwargs),
)
STETH_14.agent.TARGET_BASE = FixedPoint(TARGET_ETH)
STETH_14._pool._contract = steth_14_contract
STETH_14._pool._token = steth_contract
STETH_14.agent.name = "steth14"

STETH_30 = steth_30_pool.init_agent(
    private_key=STETH_30_PRIVATE_KEY,
    policy=PolicyZoo.lp_and_arb,
    policy_config=PolicyZoo.lp_and_arb.Config(min_trade_amount_bonds=steth_30_pool.interface.pool_config.minimum_transaction_amount * FixedPoint(2), **kwargs),
)
STETH_30.agent.TARGET_BASE = FixedPoint(TARGET_ETH)
STETH_30._pool._contract = steth_30_contract
STETH_30._pool._token = steth_contract
STETH_30.agent.name = "steth30"

RETH_14 = reth_14_pool.init_agent(
    private_key=RETH_14_PRIVATE_KEY,
    policy=PolicyZoo.lp_and_arb,
    policy_config=PolicyZoo.lp_and_arb.Config(min_trade_amount_bonds=reth_14_pool.interface.pool_config.minimum_transaction_amount * FixedPoint(2), **kwargs),
)
RETH_14.agent.TARGET_BASE = FixedPoint(TARGET_ETH)
RETH_14._pool._contract = reth_14_contract
RETH_14._pool._token = reth_contract
RETH_14.agent.name = "reth14"

RETH_30 = reth_30_pool.init_agent(
    private_key=RETH_30_PRIVATE_KEY,
    policy=PolicyZoo.lp_and_arb,
    policy_config=PolicyZoo.lp_and_arb.Config(min_trade_amount_bonds=reth_30_pool.interface.pool_config.minimum_transaction_amount * FixedPoint(2), **kwargs),
)
RETH_30.agent.TARGET_BASE = FixedPoint(TARGET_ETH)
RETH_30._pool._contract = reth_30_contract
RETH_30._pool._token = reth_contract
RETH_30.agent.name = "reth30

EZETH_14 = ezeth_14_pool.init_agent(
    private_key=EZETH_14_PRIVATE_KEY,
    policy=PolicyZoo.lp_and_arb,
    policy_config=PolicyZoo.lp_and_arb.Config(min_trade_amount_bonds=ezeth_14_pool.interface.pool_config.minimum_transaction_amount * FixedPoint(2), **kwargs),
)
EZETH_14.agent.TARGET_BASE = FixedPoint(TARGET_ETH)
EZETH_14._pool._contract = ezeth_14_contract
EZETH_14._pool._token = ezeth_contract
EZETH_14.agent.name = "ezeth14"

EZETH_30 = ezeth_30_pool.init_agent(
    private_key=EZETH_30_PRIVATE_KEY,
    policy=PolicyZoo.lp_and_arb,
    policy_config=PolicyZoo.lp_and_arb.Config(min_trade_amount_bonds=ezeth_30_pool.interface.pool_config.minimum_transaction_amount * FixedPoint(2), **kwargs),
)
EZETH_30.agent.TARGET_BASE = FixedPoint(TARGET_ETH)
EZETH_30._pool._contract = ezeth_30_contract
EZETH_30._pool._token = ezeth_contract
EZETH_30.agent.name = "ezeth30"

MORPHO_14 = morpho_14_pool.init_agent(
    private_key=MORPHO_14_PRIVATE_KEY,
    policy=PolicyZoo.lp_and_arb,
    policy_config=PolicyZoo.lp_and_arb.Config(min_trade_amount_bonds=morpho_14_pool.interface.pool_config.minimum_transaction_amount * FixedPoint(2), **kwargs),
)
MORPHO_14.agent.TARGET_BASE = FixedPoint(TARGET_BASE)
MORPHO_14._pool._contract = morpho_14_contract
MORPHO_14._pool._token = morpho_contract
MORPHO_14.agent.name = "morpho14"

MORPHO_30 = morpho_30_pool.init_agent(
    private_key=MORPHO_30_PRIVATE_KEY,
    policy=PolicyZoo.lp_and_arb,
    policy_config=PolicyZoo.lp_and_arb.Config(min_trade_amount_bonds=morpho_30_pool.interface.pool_config.minimum_transaction_amount * FixedPoint(2), **kwargs),
)
MORPHO_30.agent.TARGET_BASE = FixedPoint(TARGET_BASE)
MORPHO_30._pool._contract = morpho_30_contract
MORPHO_30._pool._token = morpho_contract
MORPHO_30.agent.name = "morpho30"

# concatenate agents
agents = [DAI_14, DAI_30, STETH_14, STETH_30, RETH_14, RETH_30, EZETH_14, EZETH_30, MORPHO_14, MORPHO_30]

# %%
# report agents
for agent in agents:
    print(f"{agent.agent.name:<14} ({agent.agent.checksum_address}) BASE={float(agent.agent.wallet.balance.amount):,.0f} ETH={web3.eth.get_balance(agent.agent.checksum_address)/1e18:,.5f}")


# %%
# prepare agents
def mint(agent: HyperdriveAgent):
    print(f"MINT by {agent.agent.name:<14} ({agent.agent.checksum_address}) of {float(agent.agent.TARGET_BASE):,.0f}..",end="",)
    fn_args = [agent.agent.TARGET_BASE.scaled_value]
    smart_contract_transact(
        web3,
        agent._pool._token,
        agent.agent,
        "mint(uint256)",
        timeout=TIMEOUT,
        txn_options_base_fee_multiple=BASE_FEE_MULTIPLE,
        txn_options_priority_fee_multiple=PRIORITY_FEE_MULTIPLE,
        *fn_args,
    )
    print("success!")
    # print(f"checking {agent._pool._token.name} balance of {agent.agent.name:<14} ({agent.agent.checksum_address})..", end="")
    base_from_chain = agent._pool._token.functions.balanceOf(agent.agent.checksum_address).call()
    # print("success!")
    agent.agent.wallet.balance.amount = FixedPoint(scaled_value=base_from_chain)
    print(f"Balance of {agent.agent.name:<14} ({agent.agent.checksum_address}) topped up to {agent.agent.wallet.balance.amount}")


print("preparing agents..")
for agent in agents:
    if agent.agent.wallet.balance.amount < agent.agent.TARGET_BASE:
        mint(agent)
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
        print(f"===POOL INFO===\n{agent._pool.interface.current_pool_state.pool_info}")
        if agent.agent.wallet.balance.amount < agent.agent.TARGET_BASE:
            mint(agent)
        event_list = agent.execute_policy_action()
        for event in event_list:
            print(f"agent {agent.agent.name}({agent.agent.checksum_address}) decided to trade: {event}")
            print(event)
    previous_block = latest_block

# %%
# manual stuff
# receipt = DAI_30.open_short(
#     bonds=FixedPoint(1128.792526128924983296),
# )
# print(f"{receipt=}")

# %%

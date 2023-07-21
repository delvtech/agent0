"""Setup helper function for running eth bot experiments"""
from __future__ import annotations

import os

import numpy as np
from numpy.random._generator import Generator as NumpyGenerator
from web3 import Web3
from web3.contract.contract import Contract

from elfpy import eth, hyperdrive_interface
from elfpy.bots import DEFAULT_USERNAME, EnvironmentConfig
from elfpy.utils import logs


def setup_experiment(environment_config: EnvironmentConfig) -> tuple[NumpyGenerator, Web3, Contract, Contract]:
    """Get agents according to provided config, provide eth, base token and approve hyperdrive.

    Arguments
    ---------
    environment_config : EnvironmentConfig
        Dataclass containing all of the user environment settings

    Returns
    -------
    tuple[NumpyGenerator, Web3, Contract, Contract]
        A tuple containing the stateful random generator, the web3 container, the base ERC20 contract, and the hyperdrive contract
    """
    # this random number generator should be used everywhere so that the experiment is repeatable
    # rng stores the state of the random number generator, so that we can pause and restart experiments from any point
    rng = np.random.default_rng(environment_config.random_seed)
    # setup logging
    logs.setup_logging(
        log_filename=environment_config.log_filename,
        max_bytes=environment_config.max_bytes,
        log_level=environment_config.log_level,
        delete_previous_logs=environment_config.delete_previous_logs,
        log_stdout=environment_config.log_stdout,
        log_format_string=environment_config.log_formatter,
    )
    # Check for default name and exit if is default
    if environment_config.username == DEFAULT_USERNAME:
        raise ValueError("Default username detected, please update 'username' in config.py")
    # point to chain env
    web3 = eth.web3_setup.initialize_web3_with_http_provider(environment_config.rpc_url, reset_provider=False)
    # setup base contract interface
    hyperdrive_abis = eth.abi.load_all_abis(environment_config.build_folder)
    addresses = hyperdrive_interface.fetch_hyperdrive_address_from_url(
        os.path.join(environment_config.artifacts_url, "addresses.json")
    )
    # set up the ERC20 contract for minting base tokens
    base_token_contract: Contract = web3.eth.contract(
        abi=hyperdrive_abis[environment_config.base_abi], address=web3.to_checksum_address(addresses.base_token)
    )
    # set up hyperdrive contract
    hyperdrive_contract: Contract = web3.eth.contract(
        abi=hyperdrive_abis[environment_config.hyperdrive_abi],
        address=web3.to_checksum_address(addresses.mock_hyperdrive),
    )
    return rng, web3, base_token_contract, hyperdrive_contract

"""Defines the eth chain connection configuration."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class EthConfig:
    """The configuration dataclass for postgres connections.

    Attributes
    ----------
    ARTIFACTS_URL: str
        The url of the artifacts server from which we get addresses.
    RPC_URL: URI | str
        The url to the ethereum node
    ABI_DIR: str
        The path to the abi directory
    """

    # default values for local contracts
    # Matching environment variables to search for
    # pylint: disable=invalid-name
    ARTIFACTS_URL: str = "http://localhost:8080"
    RPC_URL: str = "http://localhost:8545"
    ABI_DIR: str = "./packages/hyperdrive/src/"


def build_eth_config() -> EthConfig:
    """Build an eth config that looks for environmental variables.
    If env var exists, use that, otherwise, default.

    Returns
    -------
    EthConfig
        Config settings required to connect to the eth node
    """
    # Look for and load local config if it exists
    load_dotenv("eth.env")

    artifacts_url = os.getenv("ARTIFACTS_URL")
    rpc_url = os.getenv("RPC_URL")
    abi_dir = os.getenv("ABI_DIR")

    arg_dict = {}
    if artifacts_url is not None:
        arg_dict["ARTIFACTS_URL"] = artifacts_url
    if rpc_url is not None:
        arg_dict["RPC_URL"] = rpc_url
    if abi_dir is not None:
        arg_dict["ABI_DIR"] = abi_dir
    return EthConfig(**arg_dict)

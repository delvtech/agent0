"""Defines the eth chain connection configuration from env vars."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from eth_typing import URI


@dataclass
class EthConfig:
    """The configuration dataclass for postgres connections.

    Attributes
    ----------
    artifacts_uri: URI | str
        The uri of the artifacts server from which we get addresses.
    rpc_uri: URI | str
        The uri to the ethereum node.
    abi_dir: str
        The path to the abi directory.
    """

    artifacts_uri: URI | str = URI("http://localhost:8080")
    rpc_uri: URI | str = URI("http://localhost:8545")
    abi_dir: str = "./packages/hyperdrive/src/abis"

    def __post_init__(self):
        if isinstance(self.artifacts_uri, str):
            self.artifacts_uri = URI(self.artifacts_uri)
        if isinstance(self.rpc_uri, str):
            self.rpc_uri = URI(self.rpc_uri)


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

    artifacts_uri = os.getenv("ARTIFACTS_URI")
    rpc_uri = os.getenv("RPC_URI")
    abi_dir = os.getenv("ABI_DIR")

    arg_dict = {}
    if artifacts_uri is not None:
        arg_dict["artifacts_uri"] = artifacts_uri
    if rpc_uri is not None:
        arg_dict["rpc_uri"] = rpc_uri
    if abi_dir is not None:
        arg_dict["abi_dir"] = abi_dir
    return EthConfig(**arg_dict)

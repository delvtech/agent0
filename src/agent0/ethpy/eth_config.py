"""Defines the eth chain connection configuration from env vars."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from eth_typing import URI


@dataclass
class EthConfig:
    """The configuration dataclass for postgres connections."""

    artifacts_uri: URI | str = URI("http://localhost:8080")
    """The uri of the artifacts server from which we get addresses."""
    rpc_uri: URI | str = URI("http://localhost:8545")
    """The uri to the ethereum node."""
    database_api_uri: URI | str | None = URI("http://localhost:5002")
    """The uri to the database server. If set to None, we don't use the database."""
    abi_dir: str = "./packages/hyperdrive/src/abis"
    """The path to the abi directory."""
    preview_before_trade: bool = False
    """Whether to preview the trade before submitting it. Defaults to False."""

    def __post_init__(self):
        if isinstance(self.artifacts_uri, str):
            self.artifacts_uri = URI(self.artifacts_uri)
        if isinstance(self.rpc_uri, str):
            self.rpc_uri = URI(self.rpc_uri)
        if isinstance(self.database_api_uri, str):
            self.database_api_uri = URI(self.database_api_uri)


def build_eth_config(dotenv_file: str = "eth.env") -> EthConfig:
    """Build an eth config that looks for environmental variables.
    If env var exists, use that, otherwise, default.

    Arguments
    ---------
    dotenv_file: str, optional
        The path location of the dotenv file to load from.
        Defaults to "eth.env".

    Returns
    -------
    EthConfig
        Config settings required to connect to the eth node
    """
    # Look for and load local config if it exists
    if os.path.exists(dotenv_file):
        load_dotenv(dotenv_file)

    artifacts_uri = os.getenv("ARTIFACTS_URI")
    rpc_uri = os.getenv("RPC_URI")
    database_api_uri = os.getenv("DATABASE_API_URI")
    abi_dir = os.getenv("ABI_DIR")
    preview_before_trade = os.getenv("PREVIEW_BEFORE_TRADE")

    arg_dict = {}
    if artifacts_uri is not None:
        arg_dict["artifacts_uri"] = artifacts_uri
    if rpc_uri is not None:
        arg_dict["rpc_uri"] = rpc_uri
    if database_api_uri is not None:
        arg_dict["database_api_uri"] = database_api_uri
    if abi_dir is not None:
        arg_dict["abi_dir"] = abi_dir
    if preview_before_trade is not None:
        arg_dict["preview_before_trade"] = preview_before_trade
    return EthConfig(**arg_dict)

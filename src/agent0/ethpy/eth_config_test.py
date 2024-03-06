"""Test for the eth_config.py class and functions."""

from __future__ import annotations

import os

from eth_typing import URI

from .eth_config import build_eth_config


class TestBuildEthConfig:
    """Tests for eth_config.py::build_eth_config()."""

    def test_build_eth_config_from_env(self):
        """Test building the eth config from the environment."""
        # Get the current environment variables before changing them
        rpc_uri = os.environ["RPC_URI"] if "RPC_URI" in os.environ else None
        artifacts_uri = os.environ["ARTIFACTS_URI"] if "ARTIFACTS_URI" in os.environ else None
        database_api_uri = os.environ["DATABASE_API_URI"] if "DATABASE_API_URI" in os.environ else None
        abi_dir = os.environ["ABI_DIR"] if "ABI_DIR" in os.environ else None

        # Set the environment varialbes to known values
        os.environ["RPC_URI"] = "http://localhost:9999"
        os.environ["ARTIFACTS_URI"] = "http://localhost:9999"
        os.environ["DATABASE_API_URI"] = "http://localhost:9999"
        os.environ["ABI_DIR"] = "./packages/hyperdrive/src/abis/test"

        # Get the eth config, which should construct an EthConfig from the environment variables
        eth_config = build_eth_config("")

        # Check values
        assert eth_config.rpc_uri == URI("http://localhost:9999")
        assert eth_config.artifacts_uri == URI("http://localhost:9999")
        assert eth_config.database_api_uri == URI("http://localhost:9999")
        assert eth_config.abi_dir == "./packages/hyperdrive/src/abis/test"

        # Reset the Environment variables if they were set before the test
        if rpc_uri is not None:
            os.environ["RPC_URI"] = rpc_uri
        if artifacts_uri is not None:
            os.environ["ARTIFACTS_URI"] = artifacts_uri
        if database_api_uri is not None:
            os.environ["DATABASE_API_URI"] = database_api_uri
        if abi_dir is not None:
            os.environ["ABI_DIR"] = abi_dir

    def test_build_eth_config_from_env_file(self, tmp_path):
        """Test building the eth config from an environment file.

        Arguments
        ---------
        tmp_path: pathlib.Path
            Pytest fixture for a temporary path; it is deleted after the test finishes.

        """
        # Create a temporary dotenv file
        dotenv_file = tmp_path / "eth.env"
        dotenv_file.write_text(
            """
            # Local connection
            RPC_URI="http://localhost:9999"
            ARTIFACTS_URI="http://localhost:9999"
            DATABASE_API_URI="http://localhost:9999"
            ABI_DIR="./packages/hyperdrive/src/abis/test"
            """
        )

        # Get the eth config, which should construct an EthConfig from the dotenv file
        eth_config = build_eth_config(str(dotenv_file))

        # Check values
        assert eth_config.rpc_uri == URI("http://localhost:9999")
        assert eth_config.artifacts_uri == URI("http://localhost:9999")
        assert eth_config.database_api_uri == URI("http://localhost:9999")
        assert eth_config.abi_dir == "./packages/hyperdrive/src/abis/test"

    def test_build_eth_config_defaults(self):
        """Test building the eth config from an environment file."""
        # Get the current environment variables before changing them
        # Then delete all of the variables
        if "RPC_URI" in os.environ:
            rpc_uri = os.environ["RPC_URI"]
            del os.environ["RPC_URI"]
        else:
            rpc_uri = None
        if "ARTIFACTS_URI" in os.environ:
            artifacts_uri = os.environ["ARTIFACTS_URI"]
            del os.environ["ARTIFACTS_URI"]
        else:
            artifacts_uri = None
        if "DATABASE_API_URI" in os.environ:
            database_api_uri = os.environ["DATABASE_API_URI"]
            del os.environ["DATABASE_API_URI"]
        else:
            database_api_uri = None
        if "ABI_DIR" in os.environ:
            abi_dir = os.environ["ABI_DIR"]
            del os.environ["ABI_DIR"]
        else:
            abi_dir = None

        # Get the eth config, which should construct an EthConfig with default values
        eth_config = build_eth_config("")

        # Check values
        assert eth_config.artifacts_uri == URI("http://localhost:8080")
        assert eth_config.rpc_uri == URI("http://localhost:8545")
        assert eth_config.database_api_uri == URI("http://localhost:5002")
        assert eth_config.abi_dir == "./packages/hyperdrive/src/abis"

        # Reset the Environment variables if they were set before the test
        if rpc_uri is not None:
            os.environ["RPC_URI"] = rpc_uri
        if artifacts_uri is not None:
            os.environ["ARTIFACTS_URI"] = artifacts_uri
        if database_api_uri is not None:
            os.environ["DATABASE_API_URI"] = database_api_uri
        if abi_dir is not None:
            os.environ["ABI_DIR"] = abi_dir

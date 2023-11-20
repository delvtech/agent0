"""The chain objects that encapsulates a chain."""
from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import docker
from chainsync import PostgresConfig
from docker.errors import NotFound
from ethpy.base import initialize_web3_with_http_provider
from web3.types import RPCEndpoint, RPCResponse


class Chain:
    """A chain object that connects to a chain. Also launches a postgres docker container for data."""

    @dataclass
    class Config:
        """The configuration for launching a local anvil node in a subprocess.

        Attributes
        ----------
        db_port: int
            The port to bind for the postgres container. Will fail if this port is being used.
        remove_existing_db_container: bool
            Whether to remove the existing container if it exists on container launch
        """

        db_port: int = 5433
        remove_existing_db_container: bool = True

    def __init__(self, rpc_uri: str, config: Config | None = None):
        """The constructor for the Chain class that connects to an existing chain. Also launches
        a postgres docker container for gathering data.

        Attributes
        ----------
        rpc_uri: str
            The uri for the chain to connect to, e.g., `http://127.0.0.1:8545`.
        config: Config | None
            The chain configuration.
        """
        if config is None:
            config = self.Config()
        self.rpc_uri = rpc_uri
        # Initialize web3 here for rpc calls
        self._web3 = initialize_web3_with_http_provider(self.rpc_uri, reset_provider=False)
        # Remove protocol and replace . and : with dashes
        formatted_rpc_url = (
            self.rpc_uri.replace("http://", "").replace("https://", "").replace(".", "-").replace(":", "-")
        )
        db_container_name = "postgres-interactive-hyperdrive-" + formatted_rpc_url
        self.postgres_config, self.postgres_container = self._initialize_postgres_container(
            db_container_name, config.db_port, config.remove_existing_db_container
        )

    def __del__(self):
        # Kill postgres container in this class' destructor.
        # Docker doesn't play nice with types
        try:
            self.postgres_container.kill()  # type: ignore
        except Exception:
            pass

    def advance_time(self, time_delta: int | timedelta) -> RPCResponse:
        """Advances time for this chain using the `evm_mine` RPC call.
        This function looks at the timestamp of the current block, then
        mines a block explicitly setting the timestamp to the current block timestamp + time_delta
        NOTE: this advances the chain for all pool connected to this chain.

        Attributes
        ----------
        time_delta: int | timedelta
            The amount of time to advance. Can either be a `datetime.timedelta` object or an integer in seconds.
        """
        if isinstance(time_delta, timedelta):
            time_delta = int(time_delta.total_seconds())

        # We explicitly set the next block timestamp to be exactly time_delta seconds after the previous block
        # Hence, we first get the current block, followed by an explicit set of the next block timestamp, followed by a mine.
        latest_blocktime = self._web3.eth.get_block("latest").get("timestamp", None)
        if latest_blocktime is None:
            raise AssertionError("The provided block has no timestamp")
        next_blocktime = latest_blocktime + time_delta

        return self._web3.provider.make_request(method=RPCEndpoint("evm_mine"), params=[next_blocktime])

    def get_deployer_account_private_key(self):
        """Gets the private key of the deployer account."""
        # TODO this function only makes sense in the context of the LocalChain object,
        # need to support allowing an argument in deploy hyperdrive for specifying the deployer.
        # Will implement once we find a use case for connecting to an existing chain.
        raise NotImplementedError

    def _initialize_postgres_container(self, container_name: str, db_port: int, remove_existing_db_container: bool):
        # Attempt to use the default socket if it exists
        try:
            client = docker.from_env()
        except Exception:  # pylint: disable=broad-exception-caught
            home_dir = os.path.expanduser("~")
            socket_path = Path(f"{home_dir}") / ".docker" / "desktop" / "docker.sock"
            if socket_path.exists():
                logging.debug("Docker not found at default socket, using %s..", socket_path)
                client = docker.DockerClient(base_url=f"unix://{socket_path}")
            else:
                logging.debug("Docker not found.")
                client = docker.from_env()

        postgres_config = PostgresConfig(
            POSTGRES_USER="admin",
            POSTGRES_PASSWORD="password",
            POSTGRES_DB="",  # Filled in by the pool as needed
            POSTGRES_HOST="127.0.0.1",
            POSTGRES_PORT=db_port,
        )

        # Kill the test container if it already exists
        try:
            existing_container = client.containers.get(container_name)
        except NotFound:
            # Container doesn't exist, ignore
            existing_container = None

        if existing_container is not None and remove_existing_db_container:
            existing_container.remove(v=True, force=True)  # type:ignore

        # TODO ensure this container auto removes by itself
        container = client.containers.run(
            image="postgres",
            auto_remove=True,
            environment={
                "POSTGRES_USER": postgres_config.POSTGRES_USER,
                "POSTGRES_PASSWORD": postgres_config.POSTGRES_PASSWORD,
            },
            name=container_name,
            ports={"5432/tcp": ("127.0.0.1", postgres_config.POSTGRES_PORT)},
            detach=True,
            remove=True,
        )

        return postgres_config, container


class LocalChain(Chain):
    """Launches a local anvil chain in a subprocess."""

    @dataclass
    class Config(Chain.Config):
        """
        The configuration for launching a local anvil node in a subprocess

        Attributes
        ----------
        block_time: int
            If None, mines per transaction. Otherwise mines every `block_time` seconds.
        block_timestamp_interval: int
            Number of seconds to advance time for every mined block. Uses real time if None.
        chain_port: int
            The port to bind for the anvil chain. Will fail if this port is being used.
        """

        block_time: int | None = None
        block_timestamp_interval: int | None = None
        chain_port: int = 10000

    def __init__(self, config: Config | None = None):
        """The constructor for the Chain class that connects to an existing chain. Also launches
        a postgres docker container for gathering data.

        Attributes
        ----------
        config: Config | None
            The local chain configuration.
        """
        if config is None:
            config = self.Config()

        anvil_launch_args = [
            "anvil",
            "--host",
            "127.0.0.1",
            "--port",
            str(config.chain_port),
            "--code-size-limit",
            "9999999999",
        ]
        if config.block_time is not None:
            anvil_launch_args.append("--block-time")
            anvil_launch_args.append(str(config.block_time))

        self.anvil_process = subprocess.Popen(anvil_launch_args)  # pylint: disable=consider-using-with

        rpc_url = "http://127.0.0.1:" + str(config.chain_port)
        super().__init__(rpc_url, config)

        if config.block_timestamp_interval is not None:
            # TODO make RPC call for setting block timestamp
            raise NotImplementedError("Block timestamp interval not implemented yet")

    def __del__(self):
        # Kill subprocess in this class' destructor.
        try:
            self.anvil_process.kill()
        except Exception:
            pass
        super().__del__()

    def get_deployer_account_private_key(self):
        """Gets the private key of the deployer account."""
        # TODO this is the deployed account for anvil, get this programmatically
        return "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

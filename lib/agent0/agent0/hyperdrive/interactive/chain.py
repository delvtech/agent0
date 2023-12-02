"""The chain objects that encapsulates a chain."""

from __future__ import annotations

import contextlib
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import docker
from chainsync import PostgresConfig
from chainsync.db.hyperdrive.import_export_data import export_db_to_file, import_to_db
from docker.errors import NotFound
from docker.models.containers import Container
from ethpy.base import initialize_web3_with_http_provider
from web3.types import RPCEndpoint, RPCResponse

if TYPE_CHECKING:
    from .interactive_hyperdrive import InteractiveHyperdrive


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
        """Initialize the Chain class that connects to an existing chain.

        Also launches a postgres docker container for gathering data.

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
        db_container_name = f"postgres-interactive-hyperdrive-{formatted_rpc_url}"
        self.postgres_config, self.postgres_container = self._initialize_postgres_container(
            db_container_name, config.db_port, config.remove_existing_db_container
        )
        assert isinstance(self.postgres_container, Container)

        # Snapshot bookkeeping
        self._saved_snapshot_id: str
        self._has_saved_snapshot = False
        self._deployed_hyperdrive_pools: list[InteractiveHyperdrive] = []

    def cleanup(self):
        """Kills the postgres container in this class."""
        # Runs cleanup on all deployed pools
        for pool in self._deployed_hyperdrive_pools:
            pool.cleanup()
        self.postgres_container.kill()

    def __del__(self):
        """Kill postgres container in this class' destructor."""
        with contextlib.suppress(Exception):
            self.cleanup()

    def advance_time(self, time_delta: int | timedelta) -> RPCResponse:
        """Advance time for this chain using the `evm_mine` RPC call.

        This function looks at the timestamp of the current block, then
        mines a block explicitly setting the timestamp to the current block timestamp + time_delta.

        .. note:: This advances the chain for all pool connected to this chain.

        Arguments
        ---------
        time_delta: int | timedelta
            The amount of time to advance. Can either be a `datetime.timedelta` object or an integer in seconds.

        Returns
        -------
        RPCResponse
            A TypedDict returned from the RPC with the result of the call.
        """
        if isinstance(time_delta, timedelta):
            time_delta = int(time_delta.total_seconds())

        # We explicitly set the next block timestamp to be exactly time_delta seconds
        # after the previous block. Hence, we first get the current block, followed by
        # an explicit set of the next block timestamp, followed by a mine.
        latest_blocktime = self._web3.eth.get_block("latest").get("timestamp", None)
        if latest_blocktime is None:
            raise AssertionError("The provided block has no timestamp")
        next_blocktime = latest_blocktime + time_delta

        return self._web3.provider.make_request(method=RPCEndpoint("evm_mine"), params=[next_blocktime])

    def save_snapshot(self) -> None:
        """Saves a snapshot using the `evm_snapshot` RPC call.
        The chain can store one snapshot at a time, saving another snapshot overwrites the previous snapshot.
        Saving/loading snapshot only persist on the same chain, not across chains.
        """
        response = self._web3.provider.make_request(method=RPCEndpoint("evm_snapshot"), params=[])
        if "result" not in response:
            raise KeyError("Response did not have a result.")
        self._saved_snapshot_id = response["result"]

        # Save the db state
        self._dump_db()

        self._has_saved_snapshot = True

    def load_snapshot(self) -> None:
        """Loads the previous snapshot using the `evm_revert` RPC call. Can load the snapshot multiple times.
        Note: Saving/loading snapshot only persist on the same chain, not across chains.
        """
        # Loads the previous snapshot
        # When reverting snapshots, the chain deletes the previous snapshot, while we want it to persist.
        # Hence, in this function, we first revert the snapshot, then immediately create a new snapshot
        # to keep the original snapshot.

        if not self._has_saved_snapshot:
            raise ValueError("No saved snapshot to load")

        response = self._web3.provider.make_request(method=RPCEndpoint("evm_revert"), params=[self._saved_snapshot_id])
        if "result" not in response:
            raise KeyError("Response did not have a result.")
        assert response["result"]

        # load snapshot database state
        self._load_db()

        # The hyperdrive interface in deployed pools need to wipe it's cache
        for pool in self._deployed_hyperdrive_pools:
            pool._reinit_state_after_load_snapshot()  # pylint: disable=protected-access

        self.save_snapshot()

    def get_deployer_account_private_key(self):
        """Get the private key of the deployer account."""
        # TODO this function only makes sense in the context of the LocalChain object,
        # need to support allowing an argument in deploy hyperdrive for specifying the deployer.
        # Will implement once we find a use case for connecting to an existing chain.
        raise NotImplementedError

    def _initialize_postgres_container(
        self, container_name: str, db_port: int, remove_existing_db_container: bool
    ) -> tuple[PostgresConfig, Container]:
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
            assert isinstance(existing_container, Container)
        except NotFound:
            # Container doesn't exist, ignore
            existing_container = None

        if existing_container is not None and remove_existing_db_container:
            existing_container.remove(v=True, force=True)

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
        assert isinstance(container, Container)

        return postgres_config, container

    def _add_deployed_pool_to_bookkeeping(self, pool: InteractiveHyperdrive):
        if self._has_saved_snapshot:
            raise ValueError("Cannot add a new pool after saving a snapshot")
        self._deployed_hyperdrive_pools.append(pool)

    def _dump_db(self):
        # TODO parameterize the save path
        for pool in self._deployed_hyperdrive_pools:
            export_path = ".interactive_state/snapshot/" + pool._db_name  # pylint: disable=protected-access
            os.makedirs(export_path, exist_ok=True)
            export_db_to_file(export_path, pool.db_session, raw=True)

    def _load_db(self):
        # TODO parameterize the load path, careful since this is referencing the container path, not the local path.
        for pool in self._deployed_hyperdrive_pools:
            import_path = ".interactive_state/snapshot/" + pool._db_name  # pylint: disable=protected-access
            import_to_db(pool.db_session, import_path, drop=True)


class LocalChain(Chain):
    """Launches a local anvil chain in a subprocess."""

    @dataclass
    class Config(Chain.Config):
        """The configuration for launching a local anvil node in a subprocess.

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
        """Initialize the Chain class that connects to an existing chain.

        Also launch a postgres docker container for gathering data.

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
            anvil_launch_args.extend(("--block-time", str(config.block_time)))
        # This process never stops, so we run this in the background and explicitly clean up later
        self.anvil_process = subprocess.Popen(  # pylint: disable=consider-using-with
            # Suppressing output of anvil
            anvil_launch_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        super().__init__(f"http://127.0.0.1:{str(config.chain_port)}", config)

        if config.block_timestamp_interval is not None:
            # TODO make RPC call for setting block timestamp
            raise NotImplementedError("Block timestamp interval not implemented yet")

        # TODO hack, wait for chain to init
        time.sleep(1)

    def cleanup(self):
        """Kills the subprocess in this class' destructor."""
        self.anvil_process.kill()
        super().cleanup()

    def __del__(self):
        """Kill subprocess in this class' destructor."""
        with contextlib.suppress(Exception):
            self.cleanup()
        super().__del__()

    def get_deployer_account_private_key(self) -> str:
        """Get the private key of the deployer account.

        Returns
        -------
        str
            The private key for the deployer account.
        """
        # TODO this is the deployed account for anvil, get this programmatically
        return "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

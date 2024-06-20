"""The chain objects that encapsulates a chain."""

from __future__ import annotations

import atexit
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Type

import docker
import numpy as np
import pandas as pd
from docker import DockerClient
from docker.errors import NotFound
from docker.models.containers import Container
from numpy.random import Generator
from web3.types import BlockData, Timestamp

from agent0.chainsync import PostgresConfig
from agent0.chainsync.dashboard.usernames import build_user_mapping
from agent0.chainsync.db.base import get_addr_to_username, initialize_session
from agent0.chainsync.db.hyperdrive import get_hyperdrive_addr_to_name
from agent0.chainsync.postgres_config import build_postgres_config_from_env
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
from agent0.ethpy.base import initialize_web3_with_http_provider
from agent0.hyperlogs import close_logging, setup_logging

from .hyperdrive_agent import HyperdriveAgent

if TYPE_CHECKING:
    from .hyperdrive import Hyperdrive


class Chain:
    """A class that represents a ethereum node."""

    # Lots of config
    # pylint: disable=too-many-instance-attributes
    @dataclass(kw_only=True)
    class Config:
        """The configuration for the chain object."""

        # Logging parameters
        log_filename: str | None = None
        """Path and name of the log file. Won't log to file if None. Defaults to None."""
        log_max_bytes: int | None = None
        """Maximum size of the log file in bytes. Defaults to hyperlogs.DEFAULT_LOG_MAXBYTES."""
        log_level: int | None = None
        """Log level to track. Defaults to hyperlogs.DEFAULT_LOG_LEVEL."""
        delete_previous_logs: bool = False
        """Whether to delete previous log file if it exists. Defaults to False."""
        log_to_stdout: bool = True
        """Whether to log to standard output. Defaults to True."""
        log_format_string: str | None = None
        """Log formatter object. Defaults to None."""
        keep_previous_handlers: bool = False
        """Whether to keep previous handlers. Defaults to False."""

        # Execution config
        exception_on_policy_error: bool = True
        """When executing agent policies, whether to raise an exception if an error is encountered. Defaults to True."""
        exception_on_policy_slippage: bool = False
        """
        When executing agent policies, whether to raise an exception if the slippage is too large. Defaults to False.
        """
        preview_before_trade: bool = False
        """Whether to preview the position before executing a trade. Defaults to False."""

        # Logging and crash reporting
        log_to_rollbar: bool = False
        """Whether to log crash reports to rollbar. Defaults to False."""
        rollbar_log_prefix: str | None = None
        """Additional prefix for this hyperdrive to log to rollbar."""
        crash_log_level: int = logging.CRITICAL
        """The log level to log crashes at. Defaults to critical."""
        crash_report_additional_info: dict[str, Any] | None = None
        """Additional information to include in the crash report."""
        always_execute_policy_post_action: bool = False
        """
        Whether to execute the policy `post_action` function after non-policy trades. 
        If True, the policy `post_action` function always be called after any agent trade.
        If False, the policy `post_action` function will only be called after `execute_policy_action`.
        Defaults to False.
        """

        # Data pipeline parameters
        calc_pnl: bool = True
        """Whether to calculate pnl. Defaults to True."""

        use_existing_postgres: bool = False
        """
        If True, will connect to a remote postgres instance using environmental variables (see env.sample).
        If False, will manage a local postgres instance. Defaults to False.
        """
        # DB parameters
        db_port: int = 5433
        """
        The port to bind for the postgres container. Will fail if this port is being used.
        Defaults to 5433.
        Not used if `use_existing_postgres` is True.
        """
        remove_existing_db_container: bool = True
        """
        Whether to remove the existing container if it exists on container launch. Defaults to True.
        Not used if `use_existing_postgres` is True.
        """

        # RNG config
        rng_seed: int | None = None
        """The seed for the random number generator. Defaults to None."""
        rng: Generator | None = None
        """
        The experiment's stateful random number generator. Defaults to creating a generator from
        the provided random seed if not set.
        """

        # Txn config
        txn_receipt_timeout: float | None = None
        """The timeout for waiting for a transaction receipt in seconds. Defaults to 120."""
        gas_limit: int | None = None
        """
        The maximum gas to use when executing transactions. This gas limit controls
        any transactions that are executed on the chain.
        NOTE: the policies `gas_limit` overwrites this value if it is set.
        """
        # TODO we only use gas_limit currently for policy trades and `create_checkpoint` in advance time,
        # need to propagate this to other trades
        txn_signature: bytes | None = None
        """
        The signature for transactions. Defaults to `0xa0`.
        """

        def __post_init__(self):
            """Create the random number generator if not set."""
            if self.rng is None:
                self.rng = np.random.default_rng(self.rng_seed)

    def __init__(self, rpc_uri: str, config: Config | None = None):
        """Initialize the Chain class that connects to an existing chain.
        Also launches a postgres docker container for gathering data.

        Arguments
        ---------
        rpc_uri: str
            The uri for the chain to connect to, e.g., `http://localhost:8545`.
        config: Chain.Config | None, optional
            The chain configuration. Will use defaults if not provided.
        """
        if config is None:
            config = self.Config()

        setup_logging(
            log_filename=config.log_filename,
            max_bytes=config.log_max_bytes,
            log_level=config.log_level,
            delete_previous_logs=config.delete_previous_logs,
            log_stdout=config.log_to_stdout,
            log_format_string=config.log_format_string,
            keep_previous_handlers=config.keep_previous_handlers,
        )

        self.rpc_uri = rpc_uri
        # Initialize web3 here for rpc calls
        self._web3 = initialize_web3_with_http_provider(self.rpc_uri, reset_provider=False)

        self.docker_client = None
        self.postgres_container = None
        if config.use_existing_postgres:
            self.postgres_config = build_postgres_config_from_env()
            self.chain_id = str(self.postgres_config.POSTGRES_PORT)
        else:
            # Set up db connections
            # We use the db port as the container name
            # TODO we may want to use the actual chain id for this when we start
            # caching the db specific to the chain id
            self.chain_id = str(config.db_port)
            obj_name = type(self).__name__.lower()
            db_container_name = f"agent0-{obj_name}-{self.chain_id}"

            self.docker_client, self.postgres_config, self.postgres_container = self._initialize_postgres_container(
                db_container_name, config.db_port, config.remove_existing_db_container
            )
            assert isinstance(self.postgres_container, Container)

        # Update the database field to use a unique name for this pool using the hyperdrive contract address
        self.db_session = initialize_session(self.postgres_config, ensure_database_created=True)
        self._db_name = self.postgres_config.POSTGRES_DB

        self.config = config

        # Registers the cleanup function to run when the python script exist.
        # NOTE this isn't guaranteed to run (e.g., in notebook and vscode debugging environment)
        # so still best practice to manually call cleanup at the end of scripts.
        atexit.register(self.cleanup)

    # Allow this to be used as a context manager
    def __enter__(self):
        # Nothing needs to be done when entered, the constructor handles everything
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Call cleanup when exited
        self.cleanup()

    def _initialize_postgres_container(
        self, container_name: str, db_port: int, remove_existing_db_container: bool
    ) -> tuple[DockerClient, PostgresConfig, Container]:
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
            POSTGRES_DB="agent0_db",
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

        # There's a race condition here where the container gets removed between
        # checking the container and attempting to remove it.
        # Hence, we ignore any errors from attempting to remove

        if existing_container is not None and remove_existing_db_container:
            exception = None
            for _ in range(5):
                try:
                    existing_container.remove(v=True, force=True)
                    break
                except Exception as e:  # pylint: disable=broad-except
                    exception = e
            if exception is not None:
                logging.warning("Failed to remove existing container: %s", repr(exception))

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

        return client, postgres_config, container

    def cleanup(self):
        """General cleanup of resources of interactive hyperdrive."""
        db_engine = None
        if self.db_session is not None:
            db_engine = self.db_session.get_bind()

        try:
            if self.db_session is not None:
                self.db_session.close()
        except Exception:  # pylint: disable=broad-except
            pass

        try:
            if db_engine is not None:
                db_engine.dispose()  # type: ignore
        except Exception:  # pylint: disable=broad-except
            pass

        try:
            if self.postgres_container is not None:
                self.postgres_container.kill()
        except Exception:  # pylint: disable=broad-except
            pass

        try:
            if self.postgres_container is not None:
                self.postgres_container.remove()
        except Exception:  # pylint: disable=broad-except
            pass

        try:
            if self.docker_client is not None:
                self.docker_client.close()
        except Exception:  # pylint: disable=broad-except
            pass

        try:
            close_logging()
        except Exception:  # pylint: disable=broad-except
            pass

    def block_number(self) -> int:
        """Get the current block number on the chain.

        Returns
        -------
        int
            The current block number
        """
        return self._web3.eth.get_block_number()

    def block_data(self) -> BlockData:
        """Get the current block on the chain.

        Returns
        -------
        int
            The current block number
        """
        return self._web3.eth.get_block("latest")

    def block_time(self) -> Timestamp:
        """Get the current block time on the chain.

        Returns
        -------
        int
            The current block number
        """
        block = self.block_data()
        block_timestamp = block.get("timestamp", None)
        if block_timestamp is None:
            raise AssertionError("The provided block has no timestamp")
        return block_timestamp

    @property
    def is_local_chain(self) -> bool:
        """Returns if this object is a local chain."""
        return False

    ################
    # Agent functions
    ################

    def _handle_policy_config(
        self,
        policy: Type[HyperdriveBasePolicy] | None = None,
        policy_config: HyperdriveBasePolicy.Config | None = None,
    ) -> HyperdriveBasePolicy.Config | None:
        if policy is None:
            return None
        return_policy_config = None
        # Policy config might be frozen, we create a new one while setting these variables
        if policy_config is not None:
            policy_dict = asdict(policy_config)
            # If the underlying policy's rng isn't set, we use the one from the chain object
            if policy_config.rng is None and policy_config.rng_seed is None:
                policy_dict["rng"] = self.config.rng
            # If the underlying policy's `gas_limit` isn't set, we use the one from the chain object
            if policy_config.gas_limit is None:
                policy_dict["gas_limit"] = self.config.gas_limit
            return_policy_config = policy.Config(**policy_dict)
        else:
            return_policy_config = policy.Config(rng=self.config.rng, gas_limit=self.config.gas_limit)
        return return_policy_config

    def init_agent(
        self,
        private_key: str | None = None,
        public_address: str | None = None,
        pool: Hyperdrive | None = None,
        policy: Type[HyperdriveBasePolicy] | None = None,
        policy_config: HyperdriveBasePolicy.Config | None = None,
        name: str | None = None,
    ) -> HyperdriveAgent:
        """Initialize an agent object given a private key.

        .. note::
            Due to the underlying bookkeeping, each agent object needs a unique private key.

        Arguments
        ---------
        private_key: str, optional
            The private key of the associated account.
            Must be supplied to allow this agent to do any transactions.
        public_address: str | None, optional
            The public address of the associated account. This allows this agent
            to be used for analyzing data.
            Can't be used in conjunction with private_key.
        pool: LocalHyperdrive, optional
            An optional pool to set as the active pool.
        policy: HyperdrivePolicy, optional
            An optional policy to set as the active policy.
        policy_config: HyperdrivePolicy, optional
            The configuration for the attached policy.
        name: str, optional
            The name of the agent. Defaults to the wallet address.

        Returns
        -------
        HyperdriveAgent
            The agent object for a user to execute trades with.
        """
        # pylint: disable=too-many-arguments

        policy_config = self._handle_policy_config(policy, policy_config)

        out_agent = HyperdriveAgent(
            name=name,
            chain=self,
            pool=pool,
            policy=policy,
            policy_config=policy_config,
            private_key=private_key,
            public_address=public_address,
        )
        return out_agent

    ################
    # Helper functions
    ################

    # TODO should likely move these to chainsync
    # or have the db query automatically add these columns to the result

    def _add_username_to_dataframe(self, df: pd.DataFrame, addr_column: str):
        addr_to_username = get_addr_to_username(self.db_session)

        # Get corresponding usernames
        usernames = build_user_mapping(df[addr_column], addr_to_username)["username"]
        out = df.copy()
        # Weird pandas type error
        out.insert(df.columns.get_loc(addr_column), "username", usernames)  # type: ignore
        return out

    def _add_hyperdrive_name_to_dataframe(self, df: pd.DataFrame, addr_column: str):
        hyperdrive_addr_to_name = get_hyperdrive_addr_to_name(self.db_session)

        # Do lookup from address to name
        hyperdrive_name = (
            df[addr_column]
            .to_frame()
            .merge(hyperdrive_addr_to_name, how="left", left_on=addr_column, right_on="hyperdrive_address")
        )["name"]
        # Weird pandas type error
        out = df.copy()
        out.insert(df.columns.get_loc(addr_column), "hyperdrive_name", hyperdrive_name)  # type: ignore
        return out

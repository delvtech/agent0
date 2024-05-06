"""The chain objects that encapsulates a chain."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass

from web3.types import BlockData, Timestamp

from agent0.ethpy.base import initialize_web3_with_http_provider
from agent0.hyperlogs import setup_logging


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

    def __init__(self, rpc_uri: str, config: Config | None = None):
        """Initialize the Chain class that connects to an existing chain.
        Also launches a postgres docker container for gathering data.

        Arguments
        ---------
        rpc_uri: str
            The uri for the chain to connect to, e.g., `http://localhost:8545`.

        config: Chain.Config
            The chain configuration.
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

    def cleanup(self):
        """General cleanup of resources of interactive hyperdrive."""

    def __del__(self):
        """General cleanup of resources of interactive hyperdrive."""
        with contextlib.suppress(Exception):
            self.cleanup()

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

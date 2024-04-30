"""The chain objects that encapsulates a chain."""

import contextlib

from web3.types import BlockData

from agent0.ethpy.base import initialize_web3_with_http_provider


class Chain:
    """A class that represents a ethereum node."""

    def __init__(self, rpc_uri: str):
        """Initialize the Chain class that connects to an existing chain.
        Also launches a postgres docker container for gathering data.

        Arguments
        ---------
        rpc_uri: str
            The uri for the chain to connect to, e.g., `http://localhost:8545`.
        """
        self.rpc_uri = rpc_uri
        # Initialize web3 here for rpc calls
        self._web3 = initialize_web3_with_http_provider(self.rpc_uri, reset_provider=False)
        self._account_addrs: dict[str, bool] = {}

    def cleanup(self):
        """General cleanup of resources of interactive hyperdrive."""

    def __del__(self):
        """General cleanup of resources of interactive hyperdrive."""
        with contextlib.suppress(Exception):
            self.cleanup()

    def _ensure_no_duplicate_addrs(self, addr: str):
        if addr in self._account_addrs:
            raise ValueError(
                f"Wallet address {addr} already in use. "
                "Cannot manage a separate interactive hyperdrive agent with the same address."
            )
        self._account_addrs[addr] = True

    def curr_block_number(self) -> int:
        """Get the current block number on the chain.

        Returns
        -------
        int
            The current block number
        """
        return self._web3.eth.get_block_number()

    def curr_block_data(self) -> BlockData:
        """Get the current block number on the chain.

        Returns
        -------
        int
            The current block number
        """
        return self._web3.eth.get_block("latest")

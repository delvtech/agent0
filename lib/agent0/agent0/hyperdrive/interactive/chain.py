import contextlib

from ethpy.base import initialize_web3_with_http_provider


class Chain:
    """A class that represents a ethereum node."""

    def __init__(self, rpc_uri: str):
        """Initialize the Chain class that connects to an existing chain.
        Also launches a postgres docker container for gathering data.

        Arguments
        ---------
        rpc_uri: str
            The uri for the chain to connect to, e.g., `http://127.0.0.1:8545`.
        """
        self.rpc_uri = rpc_uri
        # Initialize web3 here for rpc calls
        self._web3 = initialize_web3_with_http_provider(self.rpc_uri, reset_provider=False)

    def cleanup(self):
        pass

    def __del__(self):
        """Kill postgres container in this class' destructor."""
        with contextlib.suppress(Exception):
            self.cleanup()

from __future__ import annotations

import os
from dataclasses import asdict, dataclass

import nest_asyncio
import numpy as np
from ethpy import EthConfig
from ethpy.hyperdrive import HyperdriveAddresses, HyperdriveReadWriteInterface, fetch_hyperdrive_address_from_uri
from numpy.random._generator import Generator

from agent0.base.interactive.chain import Chain
from agent0.hyperdrive.interactive.interactive_hyperdrive_agent import InteractiveHyperdriveAgent

# In order to support both scripts and jupyter notebooks with underlying async functions,
# we use the nest_asyncio package so that we can execute asyncio.run within a running event loop.
nest_asyncio.apply()


class Hyperdrive:
    @dataclass(kw_only=True)
    class Config:
        """
        Attributes
        ----------
        preview_before_trade: bool, optional
            Whether to preview the position before executing a trade. Defaults to False.
        rng_seed: int | None, optional
            The seed for the random number generator. Defaults to None.
        rng: Generator | None, optional
            The experiment's stateful random number generator. Defaults to creating a generator from
            the provided random seed if not set.
        """

        preview_before_trade: bool = False
        rng_seed: int | None = None
        rng: Generator | None = None

        def __post_init__(self):
            if self.rng is None:
                self.rng = np.random.default_rng(self.rng_seed)

    class Addresses(HyperdriveAddresses):
        # Subclass from the underlying addresses named tuple
        # We simply define a class method to initialize the address from
        # artifacts uri

        @classmethod
        def from_artifacts_uri(cls, artifacts_uri: str) -> Hyperdrive.Addresses:
            """Builds hyperdrive addresses from artifacts uri.

            Parameters
            ----------
            artifacts_uri: str
                The uri of the artifacts server from which we get addresses.
                E.g., `http://localhost:8080/artifacts.json`.
            """
            out = fetch_hyperdrive_address_from_uri(artifacts_uri)
            return cls._from_ethpy_addresses(out)

        @classmethod
        def _from_ethpy_addresses(cls, addresses: HyperdriveAddresses) -> Hyperdrive.Addresses:
            return Hyperdrive.Addresses(**asdict(addresses))

    def __init__(
        self,
        chain: Chain,
        hyperdrive_addresses: Addresses,
        config: Config | None = None,
    ):
        if config is None:
            self.config = self.Config()
        else:
            self.config = config

        # Define agent0 configs with this setup
        # TODO currently getting the path based on this file's path
        # This requires the entire monorepo to be check out, and will likely not work when
        # installing agent0 by itself.
        # This should get fixed when abis are exported in hypertypes.
        full_path = os.path.realpath(__file__)
        current_file_dir, _ = os.path.split(full_path)
        abi_dir = os.path.join(current_file_dir, "..", "..", "..", "..", "..", "packages", "hyperdrive", "src", "abis")

        self.eth_config = EthConfig(
            artifacts_uri="not_used",
            rpc_uri=chain.rpc_uri,
            abi_dir=abi_dir,
            preview_before_trade=self.config.preview_before_trade,
        )

        self.interface = HyperdriveReadWriteInterface(
            self.eth_config,
            hyperdrive_addresses,
            web3=chain._web3,
        )

        self._pool_agents: list[InteractiveHyperdriveAgent] = []

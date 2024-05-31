"""Defines the interactive hyperdrive class that encapsulates a hyperdrive pool."""

from __future__ import annotations

from dataclasses import dataclass

import nest_asyncio
import pandas as pd
from eth_typing import ChecksumAddress

from agent0.chainsync.db.hyperdrive import add_hyperdrive_addr_to_name
from agent0.ethpy.hyperdrive import (
    HyperdriveReadWriteInterface,
    generate_name_for_hyperdrive,
    get_hyperdrive_addresses_from_registry,
)

from .chain import Chain

# In order to support both scripts and jupyter notebooks with underlying async functions,
# we use the nest_asyncio package so that we can execute asyncio.run within a running event loop.
# TODO: nest_asyncio may cause compatibility issues with other libraries.
# Also, Jupyter and ASYNC compatibility might be improved, removing the need for this.
# See https://github.com/python/cpython/issues/66435.
nest_asyncio.apply()


class Hyperdrive:
    """Interactive Hyperdrive class that supports connecting to an existing hyperdrive deployment."""

    # Lots of config
    # pylint: disable=too-many-instance-attributes
    @dataclass(kw_only=True)
    class Config:
        """The configuration for the interactive hyperdrive class."""

    @classmethod
    def get_hyperdrive_addresses_from_registry(
        cls,
        chain: Chain,
        registry_contract_addr: str,
    ) -> dict[str, ChecksumAddress]:
        """Gather deployed Hyperdrive pool addresses.

        Arguments
        ---------
        chain: Chain
            The Chain object connected to a chain.
        registry_contract_addr: str
            The address of the Hyperdrive factory contract.

        Returns
        -------
        dict[str, ChecksumAddress]
            A dictionary keyed by the pool's name, valued by the pool's address
        """
        # pylint: disable=protected-access
        return get_hyperdrive_addresses_from_registry(registry_contract_addr, chain._web3)

    def _initialize(self, chain: Chain, hyperdrive_address: ChecksumAddress, name: str | None):
        self.chain = chain

        self.interface = HyperdriveReadWriteInterface(
            hyperdrive_address,
            rpc_uri=chain.rpc_uri,
            web3=chain._web3,  # pylint: disable=protected-access
            txn_receipt_timeout=self.chain.config.txn_receipt_timeout,
        )

        # Register the username if it was provided
        if name is None:
            # Build the name in this case
            name = generate_name_for_hyperdrive(
                self.hyperdrive_address,
                self.chain._web3,  # pylint: disable=protected-access
            )

        add_hyperdrive_addr_to_name(name, self.hyperdrive_address, self.chain.db_session)

    def __init__(
        self,
        chain: Chain,
        hyperdrive_address: ChecksumAddress,
        config: Config | None = None,
        name: str | None = None,
    ):
        """Initialize the interactive hyperdrive class.

        Arguments
        ---------
        chain: Chain
            The chain to interact with
        hyperdrive_address: ChecksumAddress
            The address of the hyperdrive contract
        config: Config | None
            The configuration for the interactive hyperdrive class
        name: str | None, optional
            The logical name of the pool.
        """
        if config is None:
            self.config = self.Config()
        else:
            self.config = config

        # Since the hyperdrive objects manage data ingestion into the singular database
        # held by the chain object, we want to ensure that we dont mix and match
        # local vs non-local hyperdrive objects. Hence, we ensure that any hyperdrive
        # objects must come from a base Chain object and not a LocalChain.
        # We use `type` instead of `isinstance` to explicitly check for
        # the base Chain type instead of any subclass.
        # pylint: disable=unidiomatic-typecheck
        if type(chain) != Chain:
            raise TypeError("The chain parameter must be a Chain object, not a LocalChain.")

        self._initialize(chain, hyperdrive_address, name)

    def get_positions(self, show_closed_positions: bool = False, coerce_float: bool = False) -> pd.DataFrame:
        """Gets all current positions of this pool and their corresponding pnl
        and returns as a pandas dataframe.

        This function is not implemented for remote hyperdrive, as gathering this data
        is expensive. In the future, we can explicitly make this call gather data from
        the remote chain.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.
        show_closed_positions: bool
            Whether to show positions closed positions (i.e., positions with zero balance). Defaults to False.
            When False, will only return currently open positions. Useful for gathering currently open positions.
            When True, will also return any closed positions. Useful for calculating overall pnl of all positions.

        Returns
        -------
        pd.Dataframe
            A dataframe consisting of currently open positions and their corresponding pnl.
        """
        raise NotImplementedError

    def get_trade_events(self, all_token_deltas: bool = False, coerce_float: bool = False) -> pd.DataFrame:
        """Gets the ticker history of all trades and the corresponding token deltas for each trade.

        This function is not implemented for remote hyperdrive, as gathering this data
        is expensive. In the future, we can explicitly make this call gather data from
        the remote chain.

        Arguments
        ---------
        all_token_deltas: bool
            When removing liquidity that results in withdrawal shares, the events table returns
            two entries for this transaction to keep track of token deltas (one for lp tokens and
            one for withdrawal shares). If this flag is true, will return all entries in the table,
            which is useful for calculating token positions. If false, will drop the duplicate
            withdrawal share entry (useful for returning a ticker).
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            A dataframe of trade events.
        """
        raise NotImplementedError

    def get_historical_positions(self, coerce_float: bool = False) -> pd.DataFrame:
        """Gets the history of all positions over time and their corresponding pnl
        and returns as a pandas dataframe.

        This function is not implemented for remote hyperdrive, as gathering this data
        is expensive. In the future, we can explicitly make this call gather data from
        the remote chain.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            A dataframe consisting of positions over time and their corresponding pnl.
        """
        raise NotImplementedError

    def get_historical_pnl(self, coerce_float: bool = False) -> pd.DataFrame:
        """Gets total pnl for each wallet for each block, aggregated across all open positions.

        This function is not implemented for remote hyperdrive, as gathering this data
        is expensive. In the future, we can explicitly make this call gather data from
        the remote chain.

        Arguments
        ---------
        coerce_float: bool
            If True, will coerce underlying Decimals to floats.

        Returns
        -------
        pd.Dataframe
            A dataframe of aggregated wallet pnl per block
        """
        raise NotImplementedError

    @property
    def hyperdrive_address(self) -> ChecksumAddress:
        """Returns the hyperdrive addresses for this pool.

        Returns
        -------
        ChecksumAddress
            The hyperdrive addresses for this pool
        """
        # pylint: disable=protected-access
        return self.interface.hyperdrive_address

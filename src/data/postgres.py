"""Initialize Postgres Server."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Type

import numpy as np
import pandas as pd
import sqlalchemy
from sqlalchemy import URL, Engine, MetaData, Table, create_engine, exc, func, inspect
from sqlalchemy.orm import Session, sessionmaker

from src.data.db_schema import Base, Transaction, UserMap, WalletDelta, WalletInfo
from src.data.hyperdrive.db_schema import CheckpointInfo, PoolInfo
from src.data.hyperdrive.postgres import get_pool_info

# classes for sqlalchemy that define table schemas have no methods.
# pylint: disable=too-few-public-methods


@dataclass
class PostgresConfig:
    """The configuration dataclass for postgress connections.

    Replace the user, password, and db_name with the credentials of your setup.

    Attributes
    ----------
    POSTGRES_USER : str
        The username to authentiate with
    POSTGRES_PASSWORD : str
        The password to authentiate with
    POSTGRES_DB : str
        The name of the database
    POSTGRES_HOST : str
        The hostname to connect to
    POSTGRES_PORT : int
        The port to connect to
    """

    # default values for local postgres
    # Matching environemnt variables to search for
    # pylint: disable=invalid-name
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "postgres_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432


def build_postgres_config() -> PostgresConfig:
    """Build a PostgresConfig that looks for environmental variables.

    If env var exists, use that, otherwise, default

    Returns
    -------
    config : PostgresConfig
        Config settings required to connect to and use the database
    """
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DB")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")

    arg_dict = {}
    if user is not None:
        arg_dict["POSTGRES_USER"] = user
    if password is not None:
        arg_dict["POSTGRES_PASSWORD"] = password
    if database is not None:
        arg_dict["POSTGRES_DB"] = database
    if host is not None:
        arg_dict["POSTGRES_HOST"] = host
    if port is not None:
        arg_dict["POSTGRES_PORT"] = int(port)

    return PostgresConfig(**arg_dict)


def query_tables(session: Session) -> list[str]:
    """Return a list of tables in the database.

    Arguments
    ---------
    session : Session
        The initialized session object

    Returns
    -------
    list[str]
        A list of table names in the database
    """
    inspector = inspect(session.bind)  # nice gadget
    assert inspector is not None, "inspector is None"
    return inspector.get_table_names()


def drop_table(session: Session, table_name: str) -> None:
    """Drop a table from the database.

    Arguments
    ---------
    session : Session
        The initialized session object
    table_name : str
        The name of the table to be dropped
    """
    metadata = MetaData()
    table = Table(table_name, metadata)
    bind = session.bind
    assert isinstance(bind, sqlalchemy.engine.base.Engine), "bind is not an engine"
    # checkfirst=true automatically adds an "IF EXISTS" clause
    table.drop(checkfirst=True, bind=bind)


def initialize_engine() -> Engine:
    """Initializes the postgres engine from config

    Returns
    -------
    Engine
        The initialized engine object connected to postgres
    """
    postgres_config = build_postgres_config()

    # TODO add waiting in connecting to postgres to avoid exiting out before postgres spins up
    url_object = URL.create(
        drivername="postgresql",
        username=postgres_config.POSTGRES_USER,
        password=postgres_config.POSTGRES_PASSWORD,
        host=postgres_config.POSTGRES_HOST,
        port=postgres_config.POSTGRES_PORT,
        database=postgres_config.POSTGRES_DB,
    )
    return create_engine(url_object)


def initialize_session() -> Session:
    """Initialize the database if not already initialized.

    Returns
    -------
    session : Session
        The initialized session object
    """

    engine = initialize_engine()

    # create a configured "Session" class
    session_class = sessionmaker(bind=engine)

    # create a session
    session = session_class()

    # create tables
    Base.metadata.create_all(engine)

    # commit the transaction
    session.commit()

    return session


def close_session(session: Session) -> None:
    """Close the session.

    Arguments
    ---------
    session: Session
        The initialized session object
    """
    session.close()


def add_transactions(transactions: list[Transaction], session: Session) -> None:
    """Add transactions to the poolinfo table.

    Arguments
    ---------
    transactions : list[Transaction]
        A list of Transaction objects to insert into postgres
    session : Session
        The initialized session object
    """
    for transaction in transactions:
        session.add(transaction)
    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        print(f"{transactions=}")
        raise err


def add_user_map(username: str, addresses: list[str], session: Session) -> None:
    """Add username mapping to postgres during evm_bots initialization.

    Arguments
    ---------
    username : str
        The logical username to attach to the wallet address
    addresses : list[str]
        A list of wallet addresses to map to the username
    session : Session
        The initialized session object
    """
    for address in addresses:
        # Below is a best effort check against the database to see if the address is registered to another username
        # This is best effort because there's a race condition here, e.g.,
        # I read (address_1, user_1), someone else writes (address_1, user_2), I write (address_1, user_1)
        # Because the call below is a `merge`, the final entry in the db is (address_1, user_1).
        existing_user_map = get_user_map(session, address)
        if len(existing_user_map) == 0:
            # Address doesn't exist, all good
            pass
        elif len(existing_user_map) == 1:
            existing_username = existing_user_map.iloc[0]["username"]
            if existing_username != username:
                raise ValueError(f"Wallet {address=} already registered to {existing_username}")
        else:
            # Should never be more than one address in table
            raise ValueError("Fatal error: postgres returning multiple entries for primary key")

        # This merge adds the row if not exist (keyed by address), otherwise will overwrite with this entry
        session.merge(UserMap(address=address, username=username))

    try:
        session.commit()
    except exc.DataError as err:
        print(f"{username=}, {addresses=}")
        raise err


def get_transactions(session: Session, start_block: int | None = None, end_block: int | None = None) -> pd.DataFrame:
    """Get all transactions and returns as a pandas dataframe.

    Arguments
    ---------
    session : Session
        The initialized session object
    start_block : int | None
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried transactions data
    """
    query = session.query(Transaction)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(Transaction, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(Transaction, session) + end_block + 1

    if start_block is not None:
        query = query.filter(Transaction.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(Transaction.blockNumber < end_block)

    return pd.read_sql(query.statement, con=session.connection()).set_index("blockNumber")


def get_all_wallet_info(session: Session, start_block: int | None = None, end_block: int | None = None) -> pd.DataFrame:
    """Get all of the wallet_info data in history and returns as a pandas dataframe.

    Arguments
    ---------
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried wallet info data
    """
    query = session.query(WalletInfo)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletInfo, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletInfo, session) + end_block + 1

    if start_block is not None:
        query = query.filter(WalletInfo.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(WalletInfo.blockNumber < end_block)

    return pd.read_sql(query.statement, con=session.connection())


def get_wallet_info_history(session: Session) -> dict[str, pd.DataFrame]:
    """Get the history of all wallet info over block time.

    Arguments
    ---------
    session : Session
        The initialized session object

    Returns
    -------
    dict[str, DataFrame]
        A dictionary keyed by the wallet address, where the values is a DataFrame
        where the index is the block number, and the columns is the number of each
        token the address has at that block number, plus a timestamp and the share price of the block
    """
    # Get data
    all_wallet_info = get_all_wallet_info(session)
    pool_info_lookup = get_pool_info(session)[["timestamp", "sharePrice"]]

    # Pivot tokenType to columns, keeping walletAddress and blockNumber
    all_wallet_info = all_wallet_info.pivot(
        values="tokenValue", index=["walletAddress", "blockNumber"], columns=["tokenType"]
    )
    # Forward fill nans here, as no data means no change
    all_wallet_info = all_wallet_info.fillna(method="ffill")

    # Convert walletAddress to outer dictionary
    wallet_info_dict = {}
    for addr in all_wallet_info.index.get_level_values(0).unique():
        addr_wallet_info = all_wallet_info.loc[addr]
        # Reindex block number to be continuous, filling values with the last entry
        addr_wallet_info = addr_wallet_info.reindex(pool_info_lookup.index, method="ffill")
        addr_wallet_info["timestamp"] = pool_info_lookup.loc[addr_wallet_info.index, "timestamp"]
        addr_wallet_info["sharePrice"] = pool_info_lookup.loc[addr_wallet_info.index, "sharePrice"]
        # Drop all rows where BASE tokens are nan
        addr_wallet_info = addr_wallet_info.dropna(subset="BASE")
        # Fill the rest with 0 values
        addr_wallet_info = addr_wallet_info.fillna(0)
        # Remove name from column index
        addr_wallet_info.columns.name = None
        wallet_info_dict[addr] = addr_wallet_info

    return wallet_info_dict


def get_current_wallet_info(
    session: Session, start_block: int | None = None, end_block: int | None = None
) -> pd.DataFrame:
    """Get the balance of a wallet and a given end_block.

    Note
    ----
    Here, you can specify a start_block for performance reasons,
    but if a trade happens before the start_block,
    that token won't show up in the result.

    Arguments
    ---------
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried wallet info data
    """
    all_wallet_info = get_all_wallet_info(session, start_block=start_block, end_block=end_block)
    # Get last entry in the table of each wallet address and token type
    # This should always return a dataframe
    # Pandas doesn't play nice with types
    result = (
        all_wallet_info.sort_values("blockNumber", ascending=False)
        .groupby(["walletAddress", "tokenType"])
        .agg(
            {
                "tokenValue": "first",
                "baseTokenType": "first",
                "maturityTime": "first",
                "blockNumber": "first",
                "sharePrice": "first",
            }
        )
    )
    assert isinstance(result, pd.DataFrame), "result is not a dataframe"
    current_wallet_info: pd.DataFrame = result

    # Rename blockNumber column
    current_wallet_info = current_wallet_info.rename({"blockNumber": "latestUpdateBlock"}, axis=1)
    # Filter current_wallet_info to remove 0 balance tokens
    current_wallet_info = current_wallet_info[current_wallet_info["tokenValue"] > 0]

    return current_wallet_info


def get_wallet_deltas(session: Session, start_block: int | None = None, end_block: int | None = None) -> pd.DataFrame:
    """Get all wallet_delta data in history and returns as a pandas dataframe.

    Arguments
    ---------
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried wallet info data
    """
    query = session.query(WalletDelta)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletDelta, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletDelta, session) + end_block + 1

    if start_block is not None:
        query = query.filter(WalletDelta.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(WalletDelta.blockNumber < end_block)

    return pd.read_sql(query.statement, con=session.connection())


def get_agents(session: Session, start_block: int | None = None, end_block: int | None = None) -> list[str]:
    """Get the list of all agents from the WalletInfo table.

    Arguments
    ---------
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]

    Returns
    -------
    list[str]
        A list of agent addresses
    """
    query = session.query(WalletInfo.walletAddress)
    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletInfo, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletInfo, session) + end_block + 1

    if start_block is not None:
        query = query.filter(WalletInfo.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(WalletInfo.blockNumber < end_block)

    if query is None:
        return []
    query = query.distinct()

    results = pd.read_sql(query.statement, con=session.connection())

    return results["walletAddress"].to_list()


def get_user_map(session: Session, address: str | None = None) -> pd.DataFrame:
    """Get all usermapping and returns as a pandas dataframe.

    Arguments
    ---------
    session : Session
        The initialized session object
    address : str | None, optional
        The wallet address to filter the results on. Return all if None

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool config data
    """
    query = session.query(UserMap)
    if address is not None:
        query = query.filter(UserMap.address == address)
    return pd.read_sql(query.statement, con=session.connection())


def get_latest_block_number(session: Session) -> int:
    """Get the latest block number based on the pool info table in the db.

    Arguments
    ---------
    session : Session
        The initialized session object

    Returns
    -------
    int
        The latest block number in the poolinfo table
    """
    return get_latest_block_number_from_table(PoolInfo, session)


def get_latest_block_number_from_table(
    table_obj: Type[WalletInfo | WalletDelta | PoolInfo | Transaction | CheckpointInfo], session: Session
) -> int:
    """Get the latest block number based on the specified table in the db.

    Arguments
    ---------
    table_obj : Type[WalletInfo | PoolInfo | Transaction | CheckpointInfo]
        The sqlalchemy class that contains the blockNumber column
    session : Session
        The initialized session object

    Returns
    -------
    int
        The latest block number from the specified table
    """
    # For some reason, pylint doesn't like func.max from sqlalchemy
    result = session.query(func.max(table_obj.blockNumber)).first()  # pylint: disable=not-callable
    # If table doesn't exist
    if result is None:
        return 0
    # If table exists but no data
    if result[0] is None:
        return 0
    return int(result[0])


@dataclass
class AgentPosition:
    """Details what the agent holds, how it's changed over time, and how much it's worth.

    Notes
    -----
    At a high level "position" refers to the entire portfolio of holdings.
    The portfolio is comprised of multiple positions, built up through multiple trades over time.
    - At most, the agent can have positions equal to the number of checkpoints (trades within a checkpoint are fungible)
    - DataFrames are [blocks, positions] in shape, for convenience and vectorization
    - Series are [blocks] in shape

    Examples
    --------
    To create an agent position you only need to pass in the wallet, from `pg.get_wallet_info_history(session)`:

    >>> agent_position = AgentPosition(pg.get_wallet_info_history(session))

    Use the same index across multiple tables:
    >>> block = 69
    >>> position = 3
    >>> position_name = agent_position.positions.columns[position]
    >>> holding = agent_position.positions.loc[block, position]
    >>> open_share_price = agent_position.open_share_price.loc[block, position]
    >>> pnl = agent_position.pnl.loc[block, position]
    >>> print(f"agent holds {holding} bonds in {position_name} at block {block} worth {pnl}"})
    agent holds  55.55555556 bonds in LONG-20240715 at block 69 worth 50

    Attributes
    ----------
    positions : pd.DataFrame
        The agent's holding of a single position, in bonds (# of longs or shorts).
    deltas : pd.DataFrame
        Change in each position, from the previous block.
    open_share_price : pd.DataFrame
        Weighted average open share price of each position
    pnl : pd.Series
        Value of the agent's positions.
    share_price : pd.Series
        Share price at the time of the current block.
    timestamp : pd.Series
        Timestamp of the current block.
    """

    positions: pd.DataFrame
    deltas: pd.DataFrame
    open_share_price: pd.DataFrame
    share_price: pd.Series
    timestamp: pd.Series
    pnl: pd.Series = field(default_factory=pd.Series)
    share_price: pd.Series = field(default_factory=pd.Series)
    timestamp: pd.Series = field(default_factory=pd.Series)

    def __init__(self, wallet_history: pd.DataFrame):
        """Calculate multiple relevant historical breakdowns of an agent's position."""
        # Prepare PNL Series filled with NaNs, in the shape of [blocks]
        self.pnl = pd.Series(data=np.nan, index=wallet_history.index)

        # Scrap the wallet history for parts. First we extract the share price and timestamp.
        self.share_price = wallet_history["sharePrice"]
        self.timestamp = wallet_history["timestamp"]
        # Then we keep track of every other column, to extract them into other tables.
        other_columns = [col for col in wallet_history.columns if col not in ["sharePrice", "timestamp"]]

        # Create positions dataframe which tracks aggregate holdings.
        self.positions = wallet_history.loc[:, other_columns].copy()

        # Create deltas dataframe which tracks change in holdings.
        self.deltas = self.positions.diff()
        # After the diff() call above, the first row of the deltas table will be NaN.
        # Replace them with the first row of the positions table, effectively capturing a delta from 0.
        self.deltas.iloc[0] = self.positions.iloc[0]

        # Prepare tables filled with NaNs, in the shape of [blocks, positions]
        share_price_on_increases = pd.DataFrame(
            data=np.nan,  # type: ignore
            index=self.deltas.index,  # type: ignore
            columns=self.deltas.columns,  # type: ignore
        )
        self.open_share_price = pd.DataFrame(
            data=np.nan,  # type: ignore
            index=self.deltas.index,  # type: ignore
            columns=self.deltas.columns,  # type: ignore
        )

        # When we have an increase in position, we use the current block's share_price
        share_price_on_increases = share_price_on_increases.mask(self.deltas > 0, self.share_price, axis=0)

        # Fill forward to replace NaNs. Table is now full of share prices, sourced only from increases in position.
        share_price_on_increases.fillna(method="ffill", inplace=True, axis=0)

        # Calculate weighted average share price across all deltas (couldn't figure out how to do this vector-wise).
        # vectorised attempt: ap.open_share_price = (share_price_on_increases * deltas).cumsum(axis=0) / positions
        # First row of weighted average open share price is equal to the share
        # price on increases since there's nothing to weight.
        self.open_share_price.iloc[0] = share_price_on_increases.iloc[0]

        # Now we loop across the remaining rows, updated the weighted averages for positions that change.
        for row in self.deltas.index[1:]:
            # An update is required for columns which increase in size this row, identified by a positive delta.
            update_required = self.deltas.loc[row, :].values > 0  # boolean values where we have positive deltas.
            cols = self.deltas.columns[update_required].to_list()  # associated column names

            new_price = []
            if len(update_required) > 0:
                # calculate update, per this general formula:
                # new_price = (delta_amount * current_price + old_amount * old_price) / (old_amount + delta_amount)
                new_price = (
                    share_price_on_increases.loc[row, cols] * self.deltas.loc[row, cols]  # type: ignore
                    + self.open_share_price.loc[row - 1, cols] * self.positions.loc[row - 1, cols]  # type: ignore
                ) / (
                    self.deltas.loc[row, cols] + self.positions.loc[row - 1, cols]  # type: ignore
                )

            # Keep previous result where an update isn't required, otherwise replace with new_price
            self.open_share_price.loc[row, :] = self.open_share_price.loc[row - 1, :].where(
                ~update_required, new_price, axis=0
            )


def get_agent_positions(session: Session, filter_addr: list[str] | None = None) -> dict[str, AgentPosition]:
    """Create an AgentPosition for each agent in the wallet history.

    Arguments
    ---------
    session : Session
        The initialized session object
    filter_addr : list[str] | None
        Only return these addresses. Returns all if None

    Returns
    -------
    dict[str, AgentPosition]
        Returns a dictionary keyed by wallet address, value of an agent's position
    """
    if filter_addr is None:
        return {agent: AgentPosition(wallet) for agent, wallet in get_wallet_info_history(session).items()}
    return {
        agent: AgentPosition(wallet)
        for agent, wallet in get_wallet_info_history(session).items()
        if agent in filter_addr
    }

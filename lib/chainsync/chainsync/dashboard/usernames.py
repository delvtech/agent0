"""Helper functions for mapping addresses to usernames."""
import pandas as pd
from sqlalchemy.orm import Session


def build_user_mapping(session: Session, addresses: pd.Series) -> pd.DataFrame:
    """Given a pd.Series of wallet addresses, we build a corresponding dataframe that contains
    the mapping between that wallet address and any additional aliases that address may have.
    Specifically, the output dataframe contains the following columns:
        address: The original wallet address
        abbr_address: The wallet address abbreviated (e.g., 0x0000...0000)
        username: The one-to-one mapped username for that address gathered from the `addr_to_username` postgres table
        user: The many username to one user gathered from the `username_to_user` postgres table
        format_name: A formatted name for labels combining username with abbr_addrs

    If the address doesn't exist in the lookup, the username and user will reflect the abbr_address.

    Arguments
    ---------
    session: Session
        The initialized postgres session object
    addresses: pd.Series
        The list of addresses to build the user map for.

    Returns
    -------
    pd.Dataframe
        A dataframe with 5 columns (address, abbr_address, username, user, format_name)
    """
    # TODO
    pass


def map_addresses(key: pd.Series | list | str, user_map: pd.DataFrame, map_column=None) -> pd.DataFrame:
    """Helper function to look up the aliases for an address.

    Arguments
    ---------
    key: pd.Series | list | str
        The pd.Series, list, or individual key(s) to look up.
    user_map: pd.DataFrame
        The lookup dataframe returned from build_user_mapping
    map_column: str | None
        The column that key is mapped to. If None, will default to address.

    Returns
    -------
    pd.Dataframe
        A dataframe with 4 columns (address, abbr_address, username, user, format_name) in the same order as
        the input addresses series.
    """
    # TODO
    pass


def abbreviate_address(addresses: pd.Series) -> pd.Series:
    """Given a series of addresses, return the corresponding addresses in a human readable way.

    Arguments
    ---------
    addresses: pd.Series

    Returns
    -------
    pd.Series
        The corresponding abbreviated addresses in the same order (with the same indices)
    """

    return addresses.str[:6] + "..." + addresses.str[-4:]

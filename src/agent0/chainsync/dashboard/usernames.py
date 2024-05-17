"""Helper functions for mapping addresses to usernames."""

from __future__ import annotations

from typing import overload

import pandas as pd


def build_user_mapping(addresses: pd.Series, addr_to_username: pd.DataFrame) -> pd.DataFrame:
    """Builds a mapping from wallet addresses to usernames and any additional aliases
    that address may have.

    Given a pd.Series of wallet addresses, we build a corresponding dataframe that contains
    the mapping between that wallet address and any additional aliases that address may have.
    Specifically, the output dataframe contains the following columns:
        address: The original wallet address
        abbr_address: The wallet address abbreviated (e.g., 0x0000...0000)
        username: The one-to-one mapped username for that address gathered from the `addr_to_username` postgres table
        format_name: A formatted name for labels combining username with abbr_address

    If the address doesn't exist in the lookup, the username and user will reflect the abbr_address.

    Arguments
    ---------
    addresses: pd.Series
        The list of addresses to build the user map for.
    addr_to_username: pd.DataFrame
        The mapping of addresses to username returned from `get_addr_to_username`.

    Returns
    -------
    pd.Dataframe
        A dataframe with 4 columns (address, abbr_address, username, format_name)
    """
    # Create dataframe from input
    out = addresses.to_frame().copy()
    out.columns = ["address"]
    out["abbr_address"] = abbreviate_address(out["address"])

    out = out.merge(addr_to_username, how="left", left_on="address", right_on="address")
    # Fill user/username with abbr_username if address doesn't exist in the lookup
    out["username"] = out["username"].fillna(out["abbr_address"])

    # Generate formatted name
    # TODO there is a case where the format name is not unique
    out["format_name"] = out["username"] + " - " + out["abbr_address"]
    return out


@overload
def map_addresses(key: str, user_map: pd.DataFrame, map_column=None) -> pd.Series: ...


@overload
def map_addresses(key: pd.Series | list, user_map: pd.DataFrame, map_column=None) -> pd.Series: ...


def map_addresses(key: pd.Series | list | str, user_map: pd.DataFrame, map_column=None) -> pd.DataFrame | pd.Series:
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
    pd.Dataframe | pd.Series
        A dataframe or series with 5 columns (address, abbr_address, username, user, format_name) in the same order as
        the input addresses series.
        Will return a dataframe if a series or list is passed in
        Will return a series if a single key is passed in
    """
    if map_column is None:
        map_column = "address"

    # It's assumed that the key must exist in user_map, otherwise it will throw an error.
    # In practice this shouldn't be an issue since any addresses
    # passed into this function should have a corresponding mapping in user_map due to
    # `build_user_mapping` handling missing keys.
    out = user_map.set_index(map_column).loc[key]

    # Set output's index as the original key's index if a series was passed in
    if isinstance(key, (pd.Series, list)):
        # Move map_column back as a column
        out = out.reset_index()
        if isinstance(key, pd.Series):
            # If input was a series, we reset the original index
            out.index = key.index
    else:
        # Move query back as an element
        out[map_column] = key

    # Reorder columns in order of user_map
    out = out[user_map.columns]
    return out


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

"""Helper functions for mapping addresses to usernames."""
import pandas as pd


def combine_usernames(username: pd.Series) -> pd.DataFrame:
    """Map usernames to a single user (e.g., combine click with bots)."""
    # TODO Hard coded mapping, should be a config file somewhere
    user_mapping = {
        "Charles St. Louis (click)": "Charles St. Louis",
        "Alim Khamisa (click)": "Alim Khamisa",
        "Danny Delott (click)": "Danny Delott",
        "Gregory Lisa (click)": "Gregory Lisa",
        "Jonny Rhea (click)": "Jonny Rhea",
        "Matt Brown (click)": "Matt Brown",
        "Giovanni Effio (click)": "Giovanni Effio",
        "Mihai Cosma (click)": "Mihai Cosma",
        "Ryan Goree (click)": "Ryan Goree",
        "Alex Towle (click)": "Alex Towle",
        "Adelina Ruffolo (click)": "Adelina Ruffolo",
        "Jacob Arruda (click)": "Jacob Arruda",
        "Dylan Paiton (click)": "Dylan Paiton",
        "Sheng Lundquist (click)": "Sheng Lundquist",
        "ControlC Schmidt (click)": "ControlC Schmidt",
        "George Towle (click)": "George Towle",
        "Jack Burrus (click)": "Jack Burrus",
        "Jordan J (click)": "Jordan J",
        # Bot accounts
        "slundquist (bots)": "Sheng Lundquist",
    }
    user_mapping = pd.DataFrame.from_dict(user_mapping, orient="index")
    user_mapping.columns = ["user"]
    # Use merge in case mapping doesn't exist
    username_column = username.name
    user = username.to_frame().merge(user_mapping, how="left", left_on=username_column, right_index=True)
    return user


def get_click_addresses() -> pd.DataFrame:
    """Return a dataframe of hard coded click addresses."""
    # TODO Hard coded mapping, should be a config file somewhere
    addresses = {
        "0x004dfC2dBA6573fa4dFb1E86e3723e1070C0CfdE": "Charles St. Louis (click)",
        "0x005182C62DA59Ff202D53d6E42Cef6585eBF9617": "Alim Khamisa (click)",
        "0x005BB73FddB8CE049eE366b50d2f48763E9Dc0De": "Danny Delott (click)",
        "0x0065291E64E40FF740aE833BE2F68F536A742b70": "Gregory Lisa (click)",
        "0x0076b154e60BF0E9088FcebAAbd4A778deC5ce2c": "Jonny Rhea (click)",
        "0x00860d89A40a5B4835a3d498fC1052De04996de6": "Matt Brown (click)",
        "0x00905A77Dc202e618d15d1a04Bc340820F99d7C4": "Giovanni Effio (click)",
        "0x009ef846DcbaA903464635B0dF2574CBEE66caDd": "Mihai Cosma (click)",
        "0x00D5E029aFCE62738fa01EdCA21c9A4bAeabd434": "Ryan Goree (click)",
        "0x020A6F562884395A7dA2be0b607Bf824546699e2": "Alex Towle (click)",
        "0x020a898437E9c9DCdF3c2ffdDB94E759C0DAdFB6": "Adelina Ruffolo (click)",
        "0x020b42c1E3665d14275E2823bCef737015c7f787": "Jacob Arruda (click)",
        "0x02147558D39cE51e19de3A2E1e5b7c8ff2778829": "Dylan Paiton (click)",
        "0x021f1Bbd2Ec870FB150bBCAdaaA1F85DFd72407C": "Sheng Lundquist (click)",
        "0x02237E07b7Ac07A17E1bdEc720722cb568f22840": "ControlC Schmidt (click)",
        "0x022ca016Dc7af612e9A8c5c0e344585De53E9667": "George Towle (click)",
        "0x0235037B42b4c0575c2575D50D700dD558098b78": "Jack Burrus (click)",
        "0x0238811B058bA876Ae5F79cFbCAcCfA1c7e67879": "Jordan J (click)",
    }
    addresses = pd.DataFrame.from_dict(addresses, orient="index")
    addresses = addresses.reset_index()
    addresses.columns = ["address", "username"]

    return addresses


def get_user_lookup(traders: list[str], user_map: pd.DataFrame) -> pd.DataFrame:
    """Generate username to address mapping.

    Arguments
    ---------
    traders: list[str]
        A list of all traders to build a lookup for
    user_map: pd.DataFrame
        A dataframe with "username" and "address" columns that map from bot address to a username
        generated from `get_bot_map`

    Returns
    -------
    pd.DataFrame
        A dataframe with an "username" and "address" columns that provide a lookup
        between a registered username and a wallet address. The lookup contains all entries from
        `traders`, with the wallet address itself if an address isn't registered.
    """
    # Get data
    user_map = user_map.copy()
    # Usernames in postgres are bots
    user_map["username"] = user_map["username"] + " (bots)"
    # TODO move this to reading from a config file
    click_map = get_click_addresses()
    # Add click users to map
    user_map = pd.concat([click_map, user_map], axis=0)

    # Generate a lookup of users -> address, taking into account that some addresses don't have users
    # Reindex looks up agent addresses against user_map, adding nans if it doesn't exist
    options_map = user_map.set_index("address").reindex(traders)

    # Set username as address if agent doesn't exist
    na_idx = options_map["username"].isna()
    # If there are any nan usernames, set address itself as username
    if na_idx.any():
        options_map.loc[na_idx, "username"] = options_map.index[na_idx].values
    return options_map.reset_index()


def address_to_username(lookup: pd.DataFrame, selected_list: pd.Series) -> pd.Series:
    """Look up selected users/addrs to all addresses.

    Arguments
    ---------
    lookup: pd.DataFrame
        The lookup dataframe from `get_user_lookup` call
    selected_list: list[str]
        A list of addresses to look up usernames to

    Returns
    -------
    list[str]
        A list of usernames based on selected_list
    """
    selected_list_column = selected_list.name
    out = selected_list.to_frame().merge(lookup, how="left", left_on=selected_list_column, right_on="address")
    return out["username"]

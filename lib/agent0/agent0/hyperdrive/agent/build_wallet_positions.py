"""Functions to help build agent wallets from various sources."""

import pandas as pd
from ethpy.hyperdrive import AssetIdPrefix, encode_asset_id
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from hypertypes import ERC20MintableContract, IERC4626HyperdriveContract

from agent0.base import Quantity, TokenType

from .hyperdrive_wallet import HyperdriveWallet, Long, Short


def build_wallet_positions_from_chain(
    wallet_addr: str, hyperdrive_contract: IERC4626HyperdriveContract, base_contract: ERC20MintableContract
) -> HyperdriveWallet:
    """Builds a wallet position based on gathered data.

    Arguments
    ---------
    wallet_addr: str
        The checksum wallet address
    hyperdrive_contract: Contract
        The Hyperdrive contract to query the data from
    base_contract: Contract
        The base contract to query the base amount from

    Returns
    -------
    HyperdriveWallet
        The wallet object build from the provided data
    """
    # pylint: disable=too-many-locals

    # Contract call to get base balance
    base_amount: int = base_contract.functions.balanceOf(wallet_addr).call()
    # TODO do we need to do error checking here?
    base_obj = Quantity(amount=FixedPoint(scaled_value=base_amount), unit=TokenType.BASE)

    # Contract call to get lp balance
    asset_id = encode_asset_id(AssetIdPrefix.LP, 0)
    lp_amount: int = hyperdrive_contract.functions.balanceOf(asset_id, wallet_addr).call()
    lp_obj = FixedPoint(scaled_value=lp_amount)

    # Contract call to get withdrawal positions
    asset_id = encode_asset_id(AssetIdPrefix.WITHDRAWAL_SHARE, 0)
    withdraw_amount: int = hyperdrive_contract.functions.balanceOf(asset_id, wallet_addr).call()
    withdraw_obj = FixedPoint(scaled_value=withdraw_amount)

    # We need to gather all longs and shorts from events
    # and rebuild the current long/short positions
    # Open Longs
    open_long_events = hyperdrive_contract.events.OpenLong.get_logs(fromBlock=0)
    long_obj: dict[int, Long] = {}
    for event in open_long_events:
        maturity_time = event["args"]["maturityTime"]
        long_amount = FixedPoint(scaled_value=event["args"]["bondAmount"])
        # Add this balance to the wallet if it exists, create the long object if not
        if maturity_time in long_obj:
            long_obj[maturity_time].balance += long_amount
        else:
            long_obj[maturity_time] = Long(balance=long_amount, maturity_time=maturity_time)
    # Close Longs
    close_long_events = hyperdrive_contract.events.CloseLong.get_logs(fromBlock=0)
    for event in close_long_events:
        maturity_time = event["args"]["maturityTime"]
        long_amount = FixedPoint(scaled_value=event["args"]["bondAmount"])
        assert maturity_time in long_obj, "ERROR: close event found without corresponding open event."
        long_obj[maturity_time].balance -= long_amount
    # Iterate through longs and remove any zero balance
    for k in list(long_obj.keys()):
        # Sanity check
        assert long_obj[k].balance >= FixedPoint(0), "ERROR: wallet deltas added up to be negative."
        if long_obj[k].balance == FixedPoint(0):
            del long_obj[k]

    # Open Shorts
    open_short_events = hyperdrive_contract.events.OpenShort.get_logs(fromBlock=0)
    short_obj: dict[int, Short] = {}
    for event in open_short_events:
        maturity_time = event["args"]["maturityTime"]
        short_amount = FixedPoint(scaled_value=event["args"]["bondAmount"])
        # Add this balance to the wallet if it exists, create the short object if not
        if maturity_time in short_obj:
            short_obj[maturity_time].balance += short_amount
        else:
            short_obj[maturity_time] = Short(balance=short_amount, maturity_time=maturity_time)
    # Close Shorts
    close_short_events = hyperdrive_contract.events.CloseShort.get_logs(fromBlock=0)
    for event in close_short_events:
        maturity_time = event["args"]["maturityTime"]
        short_amount = FixedPoint(scaled_value=event["args"]["bondAmount"])
        assert maturity_time in short_obj, "ERROR: close event found without corresponding open event."
        short_obj[maturity_time].balance -= short_amount
    # Iterate through longs and remove any zero balance
    for k in list(short_obj.keys()):
        # Sanity check
        assert short_obj[k].balance >= FixedPoint(0), "ERROR: wallet deltas added up to be negative."
        if short_obj[k].balance == FixedPoint(0):
            del short_obj[k]

    return HyperdriveWallet(
        address=HexBytes(wallet_addr),
        balance=base_obj,
        lp_tokens=lp_obj,
        withdraw_shares=withdraw_obj,
        longs=long_obj,
        shorts=short_obj,
    )


def build_wallet_positions_from_db(
    wallet_addr: str, db_balances: pd.DataFrame, base_contract: ERC20MintableContract
) -> HyperdriveWallet:
    """Builds a wallet position based on gathered data.

    Arguments
    ---------
    wallet_addr: str
        The checksum wallet address
    db_balances: pd.DataFrame
        The current positions dataframe gathered from the db (from the `balance_of` api call)
    base_contract: Contract
        The base contract to query the base amount from

    Returns
    -------
    HyperdriveWallet
        The wallet object build from the provided data
    """
    # pylint: disable=too-many-locals
    # Contract call to get base balance
    base_amount: int = base_contract.functions.balanceOf(wallet_addr).call()
    # TODO do we need to do error checking here?
    base_obj = Quantity(amount=FixedPoint(scaled_value=base_amount), unit=TokenType.BASE)

    # TODO We can also get lp and withdraw shares from chain?
    wallet_balances = db_balances[db_balances["wallet_address"] == wallet_addr]

    # Get longs
    long_balances = wallet_balances[wallet_balances["base_token_type"] == "LONG"]
    long_obj = {}
    # Casting maturity_time to int due to values getting encoded as strings
    for _, row in long_balances.iterrows():
        maturity_time = int(row["maturity_time"])
        long_obj[maturity_time] = Long(balance=FixedPoint(row["value"]), maturity_time=maturity_time)

    short_balances = wallet_balances[wallet_balances["base_token_type"] == "SHORT"]
    short_obj = {}
    # Casting maturity_time to int due to values getting encoded as strings
    for _, row in short_balances.iterrows():
        maturity_time = int(row["maturity_time"])
        short_obj[maturity_time] = Short(balance=FixedPoint(row["value"]), maturity_time=maturity_time)

    lp_balances = wallet_balances[wallet_balances["base_token_type"] == "LP"]
    assert len(lp_balances) <= 1
    if len(lp_balances) == 0:
        lp_obj = FixedPoint(0)
    else:
        lp_obj = FixedPoint(lp_balances.iloc[0]["value"])

    withdraw_balances = wallet_balances[wallet_balances["base_token_type"] == "WITHDRAWAL_SHARE"]
    assert len(withdraw_balances) <= 1
    if len(withdraw_balances) == 0:
        withdraw_obj = FixedPoint(0)
    else:
        withdraw_obj = FixedPoint(withdraw_balances.iloc[0]["value"])

    return HyperdriveWallet(
        address=HexBytes(wallet_addr),
        balance=base_obj,
        lp_tokens=lp_obj,
        withdraw_shares=withdraw_obj,
        longs=long_obj,
        shorts=short_obj,
    )

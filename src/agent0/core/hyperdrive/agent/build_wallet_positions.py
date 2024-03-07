"""Functions to help build agent wallets from various sources."""

import pandas as pd
from fixedpointmath import FixedPoint
from hexbytes import HexBytes

from agent0.core.base import Quantity, TokenType
from agent0.ethpy.hyperdrive import AssetIdPrefix, decode_asset_id, encode_asset_id
from agent0.hypertypes import ERC20MintableContract, IERC4626HyperdriveContract

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
    # pylint: disable=too-many-branches

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

    # We need to gather all transfers of longs and shorts from events
    # and rebuild the current long/short positions
    long_obj: dict[int, Long] = {}
    short_obj: dict[int, Short] = {}

    # Get all transfer events with tokens going to the wallet and add to wallet objects
    tokens_to_addr = hyperdrive_contract.events.TransferSingle.get_logs(
        fromBlock="earliest",
        argument_filters={"to": wallet_addr},
    )
    for event in tokens_to_addr:
        token_id = event["args"]["id"]
        token_value = event["args"]["value"]
        event_prefix, event_maturity_time = decode_asset_id(token_id)
        if event_prefix == AssetIdPrefix.LONG.value:
            assert event_maturity_time > 0, "ERROR: Long token found without maturity time"
            # Add this balance to the wallet if it exists, create the object if not
            if event_maturity_time in long_obj:
                long_obj[event_maturity_time].balance += FixedPoint(scaled_value=token_value)
            else:
                long_obj[event_maturity_time] = Long(
                    balance=FixedPoint(scaled_value=token_value), maturity_time=event_maturity_time
                )
        elif event_prefix == AssetIdPrefix.SHORT.value:
            assert event_maturity_time > 0, "ERROR: Short token found without maturity time"
            # Add this balance to the wallet if it exists, create the object if not
            if event_maturity_time in short_obj:
                short_obj[event_maturity_time].balance += FixedPoint(scaled_value=token_value)
            else:
                short_obj[event_maturity_time] = Short(
                    balance=FixedPoint(scaled_value=token_value), maturity_time=event_maturity_time
                )

    # Get all transfer events with tokens from the wallet and subtract from wallet objects
    tokens_from_addr = hyperdrive_contract.events.TransferSingle.get_logs(
        fromBlock="earliest",
        argument_filters={"from": wallet_addr},
    )
    for event in tokens_from_addr:
        token_id = event["args"]["id"]
        token_value = event["args"]["value"]
        event_prefix, event_maturity_time = decode_asset_id(token_id)
        if event_prefix == AssetIdPrefix.LONG.value:
            assert event_maturity_time > 0, "ERROR: Long token found without maturity time."
            assert event_maturity_time in long_obj, "ERROR: transfer to found without corresponding transfer from."
            long_obj[event_maturity_time].balance -= FixedPoint(scaled_value=token_value)
        elif event_prefix == AssetIdPrefix.SHORT.value:
            assert event_maturity_time > 0, "ERROR: Short token found without maturity time."
            assert event_maturity_time in long_obj, "ERROR: transfer to found without corresponding transfer from."
            short_obj[event_maturity_time].balance -= FixedPoint(scaled_value=token_value)

    # Iterate through longs and shorts to remove any zero balance
    for k in list(long_obj.keys()):
        # Sanity check
        assert long_obj[k].balance >= FixedPoint(0), "ERROR: wallet deltas added up to be negative."
        if long_obj[k].balance == FixedPoint(0):
            del long_obj[k]
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

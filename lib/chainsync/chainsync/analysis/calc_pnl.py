"""Plots the pnl."""
from __future__ import annotations

import logging
from decimal import Decimal

import numpy as np
import pandas as pd
from agent0.base.config import EnvironmentConfig
from chainsync.dashboard import calculate_spot_price
from eth_typing import ChecksumAddress, HexAddress, HexStr
from ethpy.base import initialize_web3_with_http_provider, load_all_abis, smart_contract_preview_transaction
from ethpy.hyperdrive import fetch_hyperdrive_address_from_url
from ethpy.hyperdrive.interface import get_hyperdrive_contract
from fixedpointmath import FixedPoint
from web3 import Web3
from web3.contract.contract import Contract


def calc_single_closeout(
    position: pd.DataFrame, contract: Contract, pool_info: pd.DataFrame, min_output: int, as_underlying: bool
):
    """Calculate the closeout pnl for a single position.

    Arguments
    ---------
    position: pd.DataFrame
        The position to calculate the closeout pnl for (one row in current_wallet)
    contract: Contract
        The contract object
    pool_info: pd.DataFrame
        The pool info
    min_output: int
        The minimum output to be accepted, as part of slippage tolerance
    as_underlying: bool
        Whether or not to use the underlying token
    """
    if position["baseTokenType"] == "BASE" or position["delta"] == 0:
        position["closeout_pnl"] = position["pnl"]
        return position
    assert len(position.shape) == 1, "Only one position at a time for add_unrealized_pnl_closeout"
    amount = FixedPoint(str(position["delta"])).scaled_value
    address = position.name[0]  # first item in multi-index
    tokentype = position["baseTokenType"]
    sender = ChecksumAddress(HexAddress(HexStr(address)))
    preview_result = None
    maturity = 0
    if tokentype in ["LONG", "SHORT"]:
        maturity = position["maturityTime"]
        assert isinstance(maturity, Decimal)
        maturity = int(maturity)
        assert isinstance(maturity, int)
    assert isinstance(tokentype, str)
    if tokentype == "LONG":
        fn_args = (maturity, amount, min_output, address, as_underlying)
        preview_result = smart_contract_preview_transaction(contract, sender, "closeLong", *fn_args)
        position.at["closeout_pnl"] = Decimal(preview_result["value"]) / Decimal(1e18)
    elif tokentype == "SHORT":
        fn_args = (maturity, amount, min_output, address, as_underlying)
        preview_result = smart_contract_preview_transaction(contract, sender, "closeShort", *fn_args)
        position.at["closeout_pnl"] = preview_result["value"] / Decimal(1e18)
    elif tokentype == "LP":
        fn_args = (amount, min_output, address, as_underlying)
        preview_result = smart_contract_preview_transaction(contract, sender, "removeLiquidity", *fn_args)
        position.at["closeout_pnl"] = Decimal(
            preview_result["baseProceeds"]
            + preview_result["withdrawalShares"]
            * pool_info["sharePrice"].values[-1]
            * pool_info["lpSharePrice"].values[-1]
        ) / Decimal(1e18)
    elif tokentype == "WITHDRAWAL_SHARE":
        fn_args = (amount, min_output, address, as_underlying)
        preview_result = smart_contract_preview_transaction(contract, sender, "redeemWithdrawalShares", *fn_args)
        position.at["closeout_pnl"] = preview_result["proceeds"] / Decimal(1e18)
    return position


def calc_closeout_pnl(current_wallet: pd.DataFrame, pool_info: pd.DataFrame, env_config: EnvironmentConfig):
    """Calculate closeout value of agent positions."""
    web3: Web3 = initialize_web3_with_http_provider(env_config.rpc_url, request_kwargs={"timeout": 60})

    # send a request to the local server to fetch the deployed contract addresses and
    # all Hyperdrive contract addresses from the server response
    addresses = fetch_hyperdrive_address_from_url(env_config.artifacts_url)
    abis = load_all_abis(env_config.abi_folder)
    contract = get_hyperdrive_contract(web3, abis, addresses)

    # Define a function to handle the calculation for each group
    current_wallet["closeout_pnl"] = np.nan
    return current_wallet.apply(
        calc_single_closeout,  # type: ignore
        contract=contract,
        pool_info=pool_info,
        min_output=0,
        as_underlying=True,
        axis=1,
    )


def calc_total_returns(
    pool_config: pd.Series, pool_info: pd.DataFrame, wallet_deltas: pd.DataFrame
) -> tuple[pd.Series, pd.DataFrame]:
    """Calculate the most current pnl values.

    Calculate_spot_price_for_position calculates the spot price for a position that has matured by some amount.

    Arguments
    ---------
    pool_config : pd.Series
        Time-invariant pool configuration.
    pool_info : pd.DataFrame
        Pool information like reserves. This can contain multiple blocks, but only the most recent is used.
    wallet_deltas: pd.DataFrame
        Wallet deltas for each agent and position.

    Returns
    -------
    pd.Series
        Calculated pnl for each row in current_wallet.
    """
    # pylint: disable=too-many-locals
    # Most current block timestamp
    latest_pool_info = pool_info.loc[pool_info.index.max()]
    block_timestamp = Decimal(latest_pool_info["timestamp"].timestamp())

    # Calculate unrealized gains
    current_wallet = wallet_deltas.groupby(["walletAddress", "tokenType"]).agg(
        {"delta": "sum", "baseTokenType": "first", "maturityTime": "first"}
    )

    # Sanity check, no tokens except base should dip below 0
    # TODO there's rounding issues between decimal and floating point here, fix
    assert (current_wallet["delta"][current_wallet["baseTokenType"] != "BASE"] >= -1e-9).all()

    # Calculate for base
    # Base is valued at 1:1, since that's our numéraire (https://en.wikipedia.org/wiki/Num%C3%A9raire)
    wallet_base = current_wallet[current_wallet["baseTokenType"] == "BASE"]
    base_returns = wallet_base["delta"]

    # Calculate for lp
    # LP value = users_LP_tokens * sharePrice
    # derived from:
    #   total_lp_value = lpTotalSupply * sharePrice
    #   share_of_pool = users_LP_tokens / lpTotalSupply
    #   users_LP_value = share_of_pool * total_lp_value
    #   users_LP_value = users_LP_tokens / lpTotalSupply * lpTotalSupply * sharePrice
    #   users_LP_value = users_LP_tokens * sharePrice
    wallet_lps = current_wallet[current_wallet["baseTokenType"] == "LP"]
    lp_returns = wallet_lps["delta"] * latest_pool_info["sharePrice"]

    # Calculate for withdrawal shares. Same as for LPs.
    wallet_withdrawal = current_wallet[current_wallet["baseTokenType"] == "WITHDRAWAL_SHARE"]
    withdrawal_returns = wallet_withdrawal["delta"] * latest_pool_info["sharePrice"]

    # Calculate for shorts
    # Short value = users_shorts * ( 1 - spot_price )
    # this could also be valued at 1 + ( p1 - p2 ) but we'd have to know their entry price (or entry base 🤔)
    # TODO shorts inflate the pnl calculation. When opening a short, the "amount spent" is
    # how much base is put up for collateral, but the amount of short shares are being calculated at some price
    # This really should be, how much base do I get back if I close this short right now
    wallet_shorts = current_wallet[current_wallet["baseTokenType"] == "SHORT"]
    # This calculation isn't quite right, this is not accounting for the trade spot price
    # Should take into account the spot price slipping during the actual trade
    # This will get fixed when we call preview smart contract transaction for pnl calculations
    short_spot_prices = calculate_spot_price_for_position(
        share_reserves=latest_pool_info["shareReserves"],
        bond_reserves=latest_pool_info["bondReserves"],
        time_stretch=pool_config["invTimeStretch"],
        initial_share_price=pool_config["initialSharePrice"],
        position_duration=pool_config["positionDuration"],
        maturity_timestamp=wallet_shorts["maturityTime"],
        block_timestamp=block_timestamp,
    )
    shorts_returns = wallet_shorts["delta"] * (1 - short_spot_prices)

    # Calculate for longs
    # Long value = users_longs * spot_price
    wallet_longs = current_wallet[current_wallet["baseTokenType"] == "LONG"]
    long_spot_prices = calculate_spot_price_for_position(
        share_reserves=latest_pool_info["shareReserves"],
        bond_reserves=latest_pool_info["bondReserves"],
        time_stretch=pool_config["invTimeStretch"],
        initial_share_price=pool_config["initialSharePrice"],
        position_duration=pool_config["positionDuration"],
        maturity_timestamp=wallet_longs["maturityTime"],
        block_timestamp=block_timestamp,
    )
    long_returns = wallet_longs["delta"] * long_spot_prices

    # Add pnl to current_wallet information
    # Current_wallet and *_pnl dataframes have the same index
    current_wallet.loc[base_returns.index, "pnl"] = base_returns
    current_wallet.loc[lp_returns.index, "pnl"] = lp_returns
    current_wallet.loc[shorts_returns.index, "pnl"] = shorts_returns
    current_wallet.loc[long_returns.index, "pnl"] = long_returns
    current_wallet.loc[withdrawal_returns.index, "pnl"] = withdrawal_returns
    return current_wallet.reset_index().groupby("walletAddress")["pnl"].sum(), current_wallet


def calculate_spot_price_for_position(
    share_reserves: pd.Series,
    bond_reserves: pd.Series,
    time_stretch: pd.Series,
    initial_share_price: pd.Series,
    position_duration: pd.Series,
    maturity_timestamp: pd.Series,
    block_timestamp: Decimal,
):
    """Calculate the spot price given the pool info data.

    This is calculated in a vectorized way, with every input being a scalar except for maturity_timestamp.

    Arguments
    ---------
    share_reserves : pd.Series
        The share reserves
    bond_reserves : pd.Series
        The bond reserves
    time_stretch : pd.Series
        The time stretch
    initial_share_price : pd.Series
        The initial share price
    position_duration : pd.Series
        The position duration
    maturity_timestamp : pd.Series
        The maturity timestamp
    block_timestamp : Decimal
        The block timestamp
    """
    # pylint: disable=too-many-arguments
    full_term_spot_price = calculate_spot_price(share_reserves, bond_reserves, initial_share_price, time_stretch)
    time_left_seconds = maturity_timestamp - block_timestamp  # type: ignore
    if isinstance(time_left_seconds, pd.Timedelta):
        time_left_seconds = time_left_seconds.total_seconds()
    time_left_in_years = time_left_seconds / position_duration
    logging.info(
        " spot price is weighted average of %s(%s) and 1 (%s)",
        full_term_spot_price,
        time_left_in_years,
        1 - time_left_in_years,
    )
    return full_term_spot_price * time_left_in_years + 1 * (1 - time_left_in_years)

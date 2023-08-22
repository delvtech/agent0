"""Functions to gather data from postgres, do analysis, and add back into postgres"""
import logging
from typing import Type

import numpy as np
import pandas as pd
from chainsync.db.base import Base
from chainsync.db.hyperdrive import (
    CurrentWallet,
    PoolAnalysis,
    Ticker,
    WalletPNL,
    get_current_wallet,
    get_pool_info,
    get_transactions,
    get_wallet_deltas,
)
from sqlalchemy import exc
from sqlalchemy.orm import Session
from web3.contract.contract import Contract

from .calc_base_buffer import calc_base_buffer
from .calc_fixed_rate import calc_fixed_rate
from .calc_pnl import calc_closeout_pnl
from .calc_spot_price import calc_spot_price
from .calc_ticker import calc_ticker

pd.set_option("display.max_columns", None)


def _df_to_db(insert_df: pd.DataFrame, schema_obj: Type[Base], session: Session, index=True):
    """Helper function to add a dataframe to a database"""
    table_name = schema_obj.__tablename__
    insert_df.to_sql(table_name, con=session.connection(), if_exists="append", method="multi", index=index)
    # commit the transaction
    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        logging.error("Error on adding %s: %s", table_name, err)
        raise err


def calc_total_wallet_delta(wallet_deltas: pd.DataFrame) -> pd.DataFrame:
    """Calculates total wallet deltas from wallet_delta for every wallet type and position"""
    return wallet_deltas.groupby(["walletAddress", "tokenType"]).agg(
        {"delta": "sum", "baseTokenType": "first", "maturityTime": "first"}
    )


def calc_current_wallet(wallet_deltas_df: pd.DataFrame, latest_wallet: pd.DataFrame) -> pd.DataFrame:
    """Calculates the current wallet positions given the wallet deltas
    This function takes a batch of wallet deltas and calculates the current wallet position for each
    sample of delta using cumsum. Positions are then added to the latest wallet positions (if they exist)

    Arguments
    ---------
    wallet_deltas_df: pd.DataFrame
        The dataframe of wallet deltas, following the schema of WalletDelta
    latest_wallet: pd.DataFrame
        The dataframe of the latest wallet positions, following the schema of CurrentWallet

    Returns
    -------
    pd.DataFrame
        A dataframe of the current wallet positions, following the schema of CurrentWallet
    """

    # Ensure wallet_deltas are sorted by blockNumber
    wallet_deltas_df = wallet_deltas_df.sort_values("blockNumber")
    # Using np.cumsum because of decimal objects in dataframe
    wallet_delta_by_block = wallet_deltas_df.groupby(["walletAddress", "tokenType"])["delta"].apply(np.cumsum)
    # Use only the index of the original df
    wallet_delta_by_block.index = wallet_delta_by_block.index.get_level_values(2)
    # Add column
    wallet_deltas_df["value"] = wallet_delta_by_block
    # Drop unnecessary columns to match schema
    wallet_deltas_df = wallet_deltas_df.drop(["id", "transactionHash", "delta"], axis=1)

    # If there was a initial wallet, add deltas to initial wallet to calculate current positions
    if len(latest_wallet) > 0:
        wallet_deltas_df = wallet_deltas_df.set_index(["walletAddress", "tokenType", "blockNumber"])
        latest_wallet = latest_wallet.set_index(["walletAddress", "tokenType"])

        # Add the latest wallet to each wallet delta position to calculate most current positions
        # We broadcast latest wallet across all blockNumbers. If a position does not exist in latest_wallet,
        # it will treat it as 0 (based on fill_value)
        wallet_deltas_df["value"] = wallet_deltas_df["value"].add(latest_wallet["value"], fill_value=0)
        wallet_deltas_df = wallet_deltas_df.reset_index()

        # In the case where latest_wallet has positions not in wallet_deltas, we can ignore them
        # since if they're not in wallet_deltas, there's no change in positions

    # Need to keep zero positions in the db since a delta could have made the current wallet 0
    # We can filter zero positions after the query of current positions
    return wallet_deltas_df


# TODO this function shouldn't need hyperdrive_contract eventually
# instead, should call rust implementation
# TODO clean up this function
# pylint: disable=too-many-locals, too-many-arguments
def data_to_analysis(
    start_block: int,
    end_block: int,
    pool_config: pd.Series,
    db_session: Session,
    hyperdrive_contract: Contract,
) -> None:
    """Function to query postgres data tables and insert to analysis tables"""
    # Get data
    pool_info = get_pool_info(db_session, start_block, end_block, coerce_float=False)

    # Calculate spot prices
    spot_price = calc_spot_price(
        pool_info["shareReserves"],
        pool_info["bondReserves"],
        pool_config["initialSharePrice"],
        pool_config["invTimeStretch"],
    )

    # Calculate fixed rate
    fixed_rate = calc_fixed_rate(spot_price, pool_config["positionDuration"])

    # Calculate base buffer
    base_buffer = calc_base_buffer(
        pool_info["longsOutstanding"], pool_info["sharePrice"], pool_config["minimumShareReserves"]
    )

    pool_analysis_df = pd.concat([spot_price, fixed_rate, base_buffer], axis=1)
    pool_analysis_df.columns = ["spot_price", "fixed_rate", "base_buffer"]
    _df_to_db(pool_analysis_df, PoolAnalysis, db_session, index=True)

    # TODO calculate current wallet positions for this block
    # This should be done from the deltas, not queries from chain
    wallet_deltas_df = get_wallet_deltas(db_session, start_block, end_block, coerce_float=False)
    # Explicit check for empty wallet_deltas here
    if len(wallet_deltas_df) == 0:
        return

    # Get current wallet of previous timestamp here
    # If it doesn't exist, should be an empty dataframe
    latest_wallet = get_current_wallet(db_session, end_block=start_block, coerce_float=False)
    current_wallet_df = calc_current_wallet(wallet_deltas_df, latest_wallet)
    _df_to_db(current_wallet_df, CurrentWallet, db_session, index=False)

    # calculate pnl through closeout pnl
    # TODO this function might be slow due to contract call on chain
    # and calculating for every position, wallet, and block
    # This will get better when we have the rust implementation of `smart_contract_preview_transaction`.
    # Alternatively, set sample rate so we don't calculate this every block
    # We can set a sample rate by doing batch processing on this function
    # since we only get the current wallet for the end_block
    wallet_pnl = get_current_wallet(db_session, end_block=end_block, coerce_float=False)
    pnl_df = calc_closeout_pnl(wallet_pnl, pool_info, hyperdrive_contract)

    # This sets the pnl to the current wallet dataframe, but there may be scaling issues here.
    # This is because the `CurrentWallet` table has one entry per change in wallet position,
    # and the `get_current_wallet` function handles getting all current positions at a block.
    # If we add this current_wallet (plus pnl) to the database here, the final size in the db is
    # number_of_blocks * number_of_addresses * number_of_open_positions, which is not scalable.
    # We alleviate this by sampling periodically, and not calculate this for every block
    # TODO implement sampling by setting the start + end block parameters in the caller of this function
    # TODO If sampling, might want to move this to be a separate function, with the caller controlling
    # the sampling rate. Otherwise, the e.g., ticker updates will also be on the sampling rate (won't miss data,
    # just lower frequency updates)
    # TODO do scaling tests to see the limit of this
    wallet_pnl["pnl"] = pnl_df
    # Add wallet_pnl to the database
    _df_to_db(wallet_pnl, WalletPNL, db_session, index=False)

    # Build ticker from wallet delta
    transactions = get_transactions(db_session, start_block, end_block, coerce_float=False)
    ticker_df = calc_ticker(wallet_deltas_df, transactions, pool_info)
    # TODO add ticker to database
    _df_to_db(ticker_df, Ticker, db_session, index=False)

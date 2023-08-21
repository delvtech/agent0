"""Functions to gather data from postgres, do analysis, and add back into postgres"""
import logging
from typing import Type

import numpy as np
import pandas as pd
from chainsync.db.base import Base
from chainsync.db.hyperdrive import CurrentWallet, PoolAnalysis, get_current_wallet, get_pool_info, get_wallet_deltas
from sqlalchemy import exc
from sqlalchemy.orm import Session

from .calc_base_buffer import calc_base_buffer
from .calc_fixed_rate import calc_fixed_rate
from .calc_spot_price import calc_spot_price

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


def _filter_zero_positions(wallet: pd.DataFrame) -> pd.DataFrame:
    pos_values = wallet["value"] > 0
    is_base = wallet["tokenType"] == "BASE"
    return wallet[pos_values | is_base]


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

    return _filter_zero_positions(wallet_deltas_df)


def data_to_analysis(start_block: int, end_block: int, session: Session, pool_config: pd.Series) -> None:
    """Function to query postgres data tables and insert to analysis tables"""
    # Get data
    pool_info = get_pool_info(session, start_block, end_block, coerce_float=False)

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
    _df_to_db(pool_analysis_df, PoolAnalysis, session, index=True)

    # TODO calculate current wallet positions for this block
    # This should be done from the deltas, not queries from chain
    wallet_deltas_df = get_wallet_deltas(session, start_block, end_block, coerce_float=False)

    # Get current wallet of previous timestamp here
    # If it doesn't exist, should be an empty dataframe
    if start_block > 0:
        latest_wallet = get_current_wallet(session, end_block=start_block, coerce_float=False)
    else:
        latest_wallet = pd.DataFrame([])

    current_wallet_df = calc_current_wallet(wallet_deltas_df, latest_wallet)
    _df_to_db(current_wallet_df, CurrentWallet, session, index=False)

    # TODO calculate pnl through closeout pnl

    # TODO Build ticker from wallet delta

    pass

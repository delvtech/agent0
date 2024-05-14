"""Functions to gather data from postgres, do analysis, and add back into postgres"""

from decimal import Decimal

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from agent0.chainsync.db.hyperdrive import (
    PoolAnalysis,
    PositionSnapshot,
    get_checkpoint_info,
    get_current_positions,
    get_pool_info
)
from agent0.chainsync.df_to_db import df_to_db
from agent0.ethpy.hyperdrive import HyperdriveReadInterface

from .calc_base_buffer import calc_base_buffer
from .calc_fixed_rate import calc_fixed_rate
from .calc_pnl import calc_closeout_value
from .calc_spot_price import calc_spot_price
from .calc_ticker import calc_ticker

pd.set_option("display.max_columns", None)


def calc_total_wallet_delta(wallet_deltas: pd.DataFrame) -> pd.DataFrame:
    """Calculates total wallet deltas from wallet_delta for every wallet type and position.

    Arguments
    ---------
    wallet_deltas: pd.DataFrame
        The dataframe of wallet deltas, from the output of `get_wallet_deltas`.

    Returns
    -------
    pd.DataFrame
        A dataframe of the total wallet deltas.

    """
    return wallet_deltas.groupby(["wallet_address", "token_type"]).agg(
        {"delta": "sum", "base_token_type": "first", "maturity_time": "first"}
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
    # There's a chance multiple wallet deltas can happen from the same address at the same block
    # Hence, we group all deltas into a single delta for cumsum
    wallet_deltas_df = (
        wallet_deltas_df.groupby(["wallet_address", "token_type", "block_number"])
        .agg(
            {
                "base_token_type": "first",
                "maturity_time": "first",
                "delta": "sum",
            }
        )
        .reset_index()
    )

    # Ensure wallet_deltas are sorted by block_number
    wallet_deltas_df = wallet_deltas_df.sort_values("block_number")
    # Using np.cumsum because of decimal objects in dataframe
    wallet_delta_by_block = wallet_deltas_df.groupby(["wallet_address", "token_type"])["delta"].apply(np.cumsum)
    # Use only the index of the original df
    wallet_delta_by_block.index = wallet_delta_by_block.index.get_level_values(2)
    # Add column
    wallet_deltas_df["value"] = wallet_delta_by_block
    # Drop unnecessary columns to match schema
    wallet_deltas_df = wallet_deltas_df.drop(["delta"], axis=1)

    # If there was a initial wallet, add deltas to initial wallet to calculate current positions
    if len(latest_wallet) > 0:
        wallet_deltas_df = wallet_deltas_df.set_index(["wallet_address", "token_type", "block_number"])
        latest_wallet = latest_wallet.set_index(["wallet_address", "token_type"])

        # Add the latest wallet to each wallet delta position to calculate most current positions
        # We broadcast latest wallet across all block_numbers. If a position does not exist in latest_wallet,
        # it will treat it as 0 (based on fill_value)
        wallet_deltas_df["value"] = wallet_deltas_df["value"].add(latest_wallet["value"], fill_value=0)
        # In the case where latest_wallet has positions not in wallet_deltas, we can ignore them
        # since if they're not in wallet_deltas, there's no change in positions
        wallet_deltas_df = wallet_deltas_df.reset_index()

    # Need to keep zero positions in the db since a delta could have made the current wallet 0
    # We can filter zero positions after the query of current positions
    return wallet_deltas_df


def _decimal_to_str_scaled_value(in_val: Decimal):
    return str(int(in_val * 10**18))


def _pd_decimal_to_str_scaled_value(in_pd: pd.Series):
    return (in_pd * 10**18).astype(int).astype(str)


# TODO this function shouldn't need hyperdrive_contract eventually
# instead, should call rust implementation
# TODO clean up this function
# pylint: disable=too-many-locals, too-many-arguments
def data_to_analysis(
    start_block: int,
    end_block: int,
    pool_config_df: pd.DataFrame,
    db_session: Session,
    interfaces: list[HyperdriveReadInterface],
    calc_pnl: bool = True,
) -> None:
    """Function to query postgres data tables and insert to analysis tables.
    Executes analysis on a batch of blocks, defined by start and end block.

    Arguments
    ---------
    start_block: int
        The block to start analysis on.
    end_block: int
        The block to end analysis on.
    pool_config_df: pd.DataFrame
        The pool config data for all pools.
    db_session: Session
        The initialized db session.
    interfaces: list[HyperdriveReadInterface] | None, optional
        A collection of Hyperdrive interface objects, each connected to a pool.
    calc_pnl: bool
        Whether to calculate pnl. Defaults to True.
    """
    # Get data
    for interface in interfaces:
        hyperdrive_address = interface.hyperdrive_address
        pool_config = pool_config_df[pool_config_df["hyperdrive_address"] == hyperdrive_address]
        assert len(pool_config) == 1
        pool_config = pool_config.iloc[0]
        # Note end block here is not inclusive
        pool_info = get_pool_info(db_session, hyperdrive_address, start_block, end_block, coerce_float=False)

        # Calculate all open positions for the end block
        current_pool_positions = get_current_positions(
            db_session, hyperdrive_address=hyperdrive_address, query_block=end_block, coerce_float=False
        )
        if len(current_pool_positions) > 0:
            # Calculate pnl for these positions if flag is set
            if calc_pnl:
                checkpoint_info = get_checkpoint_info(db_session, coerce_float=False)
                pnl_df = calc_closeout_value(current_pool_positions, checkpoint_info, interface)
                current_pool_positions["pnl"] = pnl_df
            # Add wallet_pnl to the database
            df_to_db(current_pool_positions, PositionSnapshot, db_session)

        # We add pool analysis last since this table is what's being used to determine how far the data pipeline is.
        # Calculate spot price
        # TODO ideally we would call hyperdrive interface directly to get the spot price and fixed rate.
        # However, we need to be able to query e.g., pool_info for a specific block. Hence here, we use the
        # pool info from the db and directly call hyperdrivepy to get the spot price.
        spot_price = calc_spot_price(
            pool_info["share_reserves"],
            pool_info["share_adjustment"],
            pool_info["bond_reserves"],
            pool_config["initial_vault_share_price"],
            pool_config["time_stretch"],
        )

        # Calculate fixed rate
        fixed_rate = calc_fixed_rate(spot_price, pool_config["position_duration"])

        # Calculate base buffer
        base_buffer = calc_base_buffer(
            pool_info["longs_outstanding"], pool_info["vault_share_price"], pool_config["minimum_share_reserves"]
        )

        pool_analysis_df = pd.concat([pool_info["block_number"], spot_price, fixed_rate, base_buffer], axis=1)
        pool_analysis_df.columns = ["block_number", "spot_price", "fixed_rate", "base_buffer"]
        pool_analysis_df["hyperdrive_address"] = hyperdrive_address
        df_to_db(pool_analysis_df, PoolAnalysis, db_session)

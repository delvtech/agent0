"""Functions to gather data from postgres, do analysis, and add back into postgres"""
import logging
from typing import Type

import pandas as pd
from chainsync.db.base import Base
from chainsync.db.hyperdrive import PoolAnalysis, get_pool_info
from sqlalchemy import exc
from sqlalchemy.orm import Session

from .calc_base_buffer import calc_base_buffer
from .calc_fixed_rate import calc_fixed_rate
from .calc_spot_price import calc_spot_price


def _df_to_db(insert_df: pd.DataFrame, schema_obj: Type[Base], session: Session):
    """Helper function to add a dataframe to a database"""
    table_name = schema_obj.__tablename__
    insert_df.to_sql(table_name, con=session.connection(), if_exists="append", method="multi")
    # commit the transaction
    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        logging.error("Error on adding %s: %s", table_name, err)
        raise err


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
    _df_to_db(pool_analysis_df, PoolAnalysis, session)

    # TODO calculate current wallet positions for this block
    # This should be done from the deltas, not queries from chain

    # TODO calculate pnl through closeout pnl

    # TODO Build ticker from wallet delta

    pass

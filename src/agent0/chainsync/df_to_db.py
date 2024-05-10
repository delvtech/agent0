"""Helper function to add a dataframe to a database."""

import logging
from typing import Type

import pandas as pd
from sqlalchemy import exc
from sqlalchemy.orm import Session

from agent0.chainsync.db.base import Base

MAX_BATCH_SIZE = 10000


def df_to_db(insert_df: pd.DataFrame, schema_obj: Type[Base], session: Session):
    """Helper function to add a dataframe to a database.

    Arguments
    ---------
    insert_df: pd.DataFrame
        The dataframe to insert.
    schema_obj: Type[Base]
        The schema object to use.
    session: Session
        The initialized session object.
    """
    table_name = schema_obj.__tablename__

    # dataframe to_sql needs data types from the schema object
    dtype = {c.name: c.type for c in schema_obj.__table__.columns}
    # Pandas doesn't play nice with types
    insert_df.to_sql(
        table_name,
        con=session.connection(),
        if_exists="append",
        method="multi",
        index=False,
        dtype=dtype,  # type: ignore
        chunksize=MAX_BATCH_SIZE,
    )
    # commit the transaction
    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        logging.error("Error on adding %s: %s", table_name, err)
        raise err

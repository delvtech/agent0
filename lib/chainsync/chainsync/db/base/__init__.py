"""Generic database utilities"""

from .interface import (
    TableWithBlockNumber,
    add_user_map,
    close_session,
    drop_table,
    get_latest_block_number_from_table,
    get_user_map,
    initialize_engine,
    initialize_session,
    query_tables,
)
from .schema import Base, UserMap

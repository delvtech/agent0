"""Logging setup and defaults"""

import logging

from .json_encoder import ExtendedJSONEncoder
from .logs import (
    DEFAULT_LOG_DATETIME,
    DEFAULT_LOG_FORMATTER,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_MAXBYTES,
    add_file_handler,
    add_stdout_handler,
    close_logging,
    get_root_logger,
    setup_logging,
)

# Setup barebones logging without a handler for users to adapt to their needs.
logging.getLogger(__name__).addHandler(logging.NullHandler())

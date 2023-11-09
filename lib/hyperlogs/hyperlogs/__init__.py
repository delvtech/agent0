"""Logging setup and defaults"""

import logging

# Setup barebones logging without a handler for users to adapt to their needs.
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Logging defaults
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMATTER = "\n%(asctime)s: %(levelname)s: %(module)s.%(funcName)s:\n%(message)s"
DEFAULT_LOG_DATETIME = "%y-%m-%d %H:%M:%S"
DEFAULT_LOG_MAXBYTES = int(2e6)  # 2MB

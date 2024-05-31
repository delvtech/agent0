"""Utilities for rollbar."""

from __future__ import annotations

import datetime
import getpass
import logging
import os
import platform

import rollbar
from dotenv import load_dotenv

from agent0.ethpy.base.errors import ContractCallException

load_dotenv(".env")
ROLLBAR_API_KEY = os.getenv("ROLLBAR_API_KEY")


def initialize_rollbar(environment_name: str) -> bool:
    """Initializes the rollbar sdk.

    Arguments
    ---------
    environment_name: str
        The name of the environment.  Should be something like localfuzzbots or aws.fuzzbots

    Returns
    -------
    bool
        True if rollbar is initialized.
    """
    log_to_rollbar = bool(ROLLBAR_API_KEY)
    if log_to_rollbar:
        logging.info("logging to rollbar enabled.")
        rollbar.init(
            access_token=ROLLBAR_API_KEY,
            environment=environment_name,
            code_version="1.0",
        )
        env_details = {
            "environment": os.getenv("APP_ENV", "development"),  # e.g., 'production', 'development'
            "platform": platform.system(),  # e.g., 'Linux', 'Windows'
            "platform_version": platform.version(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "time": datetime.datetime.utcnow().isoformat(),
            "user": getpass.getuser(),
        }

        rollbar.report_message("rollbar initialized", "info", extra_data=env_details)

    return log_to_rollbar


def log_rollbar_message(message: str, log_level: int, extra_data: dict | None = None):
    """Logs a message to the rollbar service.

    Arguments
    ---------
    message: str
        The message to send to rollbar.
    log_level: int
        The logging level enum value.
    extra_data: dict, optional.
        Extra data to send to rollbar.  This is usually the custom crash report data.
    """
    log_level_name = logging.getLevelName(log_level)
    rollbar.report_message(message, log_level_name, extra_data=extra_data)


def log_rollbar_exception(
    exception: Exception, log_level: int, extra_data: dict | None = None, rollbar_log_prefix: str | None = None
):
    """Logs an exception to the rollbar service.

    Arguments
    ---------
    exception: Exception
        The exception to log.
    log_level: int
        The logging level enum value.
    extra_data: dict, optional.
        Extra data to send to rollbar. This usually contains the custom crash report json
    rollbar_log_prefix: str, optional
        The prefix to prepend to rollbar exception messages
    """
    log_level_name = logging.getLevelName(log_level).lower()
    if rollbar_log_prefix is None:
        log_message = ""
    else:
        log_message = rollbar_log_prefix + ": "
    log_message += repr(exception)
    if isinstance(exception, ContractCallException):
        log_message += ": " + repr(exception.orig_exception)
    rollbar.report_message(log_message, log_level_name, extra_data=extra_data)

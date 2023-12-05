"""Utilities for rollbar."""
import datetime
import getpass
import logging
import os
import platform
import sys

import rollbar
from dotenv import load_dotenv

load_dotenv("rollbar.env")
ROLLBAR_API_KEY = os.getenv("ROLLBAR_API_KEY")

env_details = {
    "environment": os.getenv("APP_ENV", "development"),  # e.g., 'production', 'development'
    "platform": platform.system(),  # e.g., 'Linux', 'Windows'
    "platform_version": platform.version(),
    "hostname": platform.node(),
    "python_version": platform.python_version(),
    "time": datetime.datetime.utcnow().isoformat(),
    "user": getpass.getuser(),
}

# You might also want to add application-specific information
app_details = {
    "app_version": "1.0.0",  # Replace with your app's version
    # Add other relevant app-specific details here
}

# Combine the details
extra_data = {
    "environment_details": env_details,
    "application_details": app_details,
    # Add any other details you deem necessary
}


def initialize_rollbar(environment_name: str) -> bool:
    """Initializes the rollbar sdk.

    Parameters
    ----------
    environment_name : str
        The name of the environment.  Should be something like 'local.fuzzbots' or 'aws.fuzzbots'

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
        rollbar.report_message("rollbar initialized", "info", payload_data=extra_data)

    return log_to_rollbar


def log_rollbar_message(message: str, log_level: int, payload: dict):
    """Logs a message to the rollbar service.

    Parameters
    ----------
    message: str
        The message to send to rollbar.
    log_level : int
        The logging level enum value.
    payload : dict
        Extra data to send to rollbar.
    """
    log_level_name = logging.getLevelName(log_level)
    rollbar.report_message(message, log_level_name, payload_data=payload, extra_data=extra_data)


def log_rollbar_exception(exception: BaseException, log_level: int, payload: dict):
    """Logs an exception to the rollbar service.

    Parameters
    ----------
    exception : BaseException
        The exception to log.
    log_level : int
        The logging level enum value.
    payload : dict
        Extra data to send to rollbar.
    """
    log_level_name = logging.getLevelName(log_level)
    try:
        raise exception
    except Exception:  # pylint: disable=broad-exception-caught
        rollbar.report_exc_info(sys.exc_info(), log_level_name, payload_data=payload, extra_data=extra_data)

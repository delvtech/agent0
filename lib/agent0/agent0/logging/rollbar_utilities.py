"""Utilities for rollbar."""
import os

import rollbar
from dotenv import load_dotenv

ROLLBAR_API_KEY = os.getenv("ROLLBAR_API_KEY")


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

    load_dotenv("rollbar.env")
    log_to_rollbar = bool(ROLLBAR_API_KEY)
    if log_to_rollbar:
        print("logging to rollbar enabled.")
        rollbar.init(
            access_token=ROLLBAR_API_KEY,
            environment=environment_name,
            code_version="1.0",
        )

    return log_to_rollbar

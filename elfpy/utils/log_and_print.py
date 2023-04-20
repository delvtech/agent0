"""This module contains a function that logs to both the generic logger and to stdout."""
import logging


def log_and_print(string: str, *args, end="\n") -> None:
    """Log to both the generic logger and to stdout."""
    if args:
        string = string.format(*args)
    logging.info(string + end)
    print(string, end=end)

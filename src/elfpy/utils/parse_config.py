"""Utilities for parsing & loading user config TOML files"""
import logging
import tomli

from elfpy.utils.config import Config


def load_and_parse_config_file(config_file: str) -> Config:
    r"""Wrapper function for loading a toml config file and parsing it.

    Parameters
    ----------
    config_file : str
        Absolute path to a toml config file.

    Returns
    -------
    config: Config
        Nested dataclass with member classes MarketConfig, AMMConfig, and SimulatorConfig
    """
    return parse_simulation_config(load_config_file(config_file))


def load_config_file(config_file: str) -> dict:
    r"""Load a config file as a dictionary

    Parameters
    ----------
    config_file : str
        Absolute path to a toml config file.

    Returns
    -------
    config_dict: dictionary
        Nested dictionary containing the market, amm, and simulator config dicts
    """
    with open(config_file, mode="rb") as file:
        config_dict = tomli.load(file)
    return config_dict


def parse_simulation_config(config_dict: dict) -> Config:
    r"""Parse the TOML config file and return a config object

    Parameters
    ----------
    config_dict : dictionary
        Nested dictionary containing the market, amm, and simulator config dicts

    Returns
    -------
    config: Config
        Nested dataclass with member classes MarketConfig, AMMConfig, and SimulatorConfig
    """
    return Config(**config_dict)


def text_to_logging_level(logging_text: str) -> int:
    r"""Converts logging level description to an integer

    Parameters
    ----------
    logging_text : str
        String description of the logging level; must be in ["debug", "info", "warning", "error", "critical"]

    Returns
    -------
    int
        Logging level integer corresponding to the string input
    """
    if logging_text.lower() == "notset":
        level = logging.NOTSET
    elif logging_text.lower() == "debug":
        level = logging.DEBUG
    elif logging_text.lower() == "info":
        level = logging.INFO
    elif logging_text.lower() == "warning":
        level = logging.WARNING
    elif logging_text.lower() == "error":
        level = logging.ERROR
    elif logging_text.lower() == "critical":
        level = logging.CRITICAL
    else:
        raise ValueError(f'{logging_text=} must be in ["debug", "info", "warning", "error", "critical"]')
    return level

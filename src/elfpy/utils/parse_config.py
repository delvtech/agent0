"""
Utilities for parsing & loading user config TOML files
"""

import logging
import tomli

from elfpy.utils.config import AMMConfig, Config, MarketConfig, SimulatorConfig


def load_and_parse_config_file(config_file):
    """
    Wrapper function for loading a toml config file and parsing it.
    Arguments
    ---------
    config_file : str
        Absolute path to a toml config file.

    Returns
    -------
    config: Config
        Nested dataclass with member classes MarketConfig, AMMConfig, and SimulatorConfig
    """
    return parse_simulation_config(load_config_file(config_file))


def load_config_file(config_file):
    """
    Load a config file as a dictionary
    Arguments
    ---------
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


def parse_simulation_config(config_dict):
    """
    Parse the TOML config file and return a config object
    Arguments
    ---------
    config_dict : dictionary
        Nested dictionary containing the market, amm, and simulator config dicts

    Returns
    -------
    config: Config
        Nested dataclass with member classes MarketConfig, AMMConfig, and SimulatorConfig
    """
    simulation_config = Config(
        market=MarketConfig(**config_dict["market"]),
        amm=AMMConfig(**config_dict["amm"]),
        simulator=SimulatorConfig(**config_dict["simulator"]),
    )
    simulation_config.simulator.logging_level = text_to_logging_level(simulation_config.simulator.logging_level)
    return simulation_config


def text_to_logging_level(logging_text: str) -> int:
    """
    Converts logging level description to an integer

    Arguments
    ---------
    logging_text : str
        String description of the logging level; must be in ["debug", "info", "warning", "error", "critical"]

    Returns
    -------
    int
        Logging level integer corresponding to the string input
    """
    match logging_text.lower():
        case "notset":
            level = logging.NOTSET
        case "debug":
            level = logging.DEBUG
        case "info":
            level = logging.INFO
        case "warning":
            level = logging.WARNING
        case "error":
            level = logging.ERROR
        case "critical":
            level = logging.CRITICAL
        case _:
            raise ValueError(f'{logging_text=} must be in ["debug", "info", "warning", "error", "critical"]')
    return level

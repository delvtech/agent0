"""
Utilities for parsing & loading user config TOML files

"""

import tomli
import logging

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
    return apply_config_logging(simulation_config)


def apply_config_logging(raw_config: Config):
    """
    Applies config logging from config settings
    """
    match raw_config.simulator.logging_level.lower():
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
    raw_config.simulator.logging_level = level
    return raw_config

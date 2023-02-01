"""Utilities for parsing & loading user config TOML files"""

import logging
import tomli

from elfpy.utils.config import AMMConfig, Config, MarketConfig, SimulatorConfig


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
    simulation_config = Config(
        market=MarketConfig(**config_dict["market"]),
        amm=AMMConfig(**config_dict["amm"]),
        simulator=SimulatorConfig(**config_dict["simulator"]),
    )
    return simulation_config


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


def override_config_variables(config: Config, override_dict: dict) -> Config:
    r"""Replace existing member & config variables with ones defined in override_dict

    Parameters
    ----------
    config : Config
        config object, as defined in elfpy.utils.config
    override_dict : dict
        dictionary containing keys that correspond to member fields of the RandomSimulationVariables class

    Returns
    -------
    Config
        same dataclass as the config input, but with fields specified by override_dict changed
    """
    # override the config variables, including random variables that were set
    output_config = Config()
    for config_type in ["market", "amm", "simulator"]:
        for config_key in config[config_type].__dict__:
            if config_key in override_dict:
                logging.debug(
                    "Overridding %s from %s to %s.",
                    config_key,
                    str(config[config_type][config_key]),
                    str(override_dict[config_key]),
                )
                output_config[config_type][config_key] = override_dict[config_key]
            else:
                output_config[config_type][config_key] = config[config_type][config_key]
    return output_config

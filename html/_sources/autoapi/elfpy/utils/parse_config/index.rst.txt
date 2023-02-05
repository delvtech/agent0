:py:mod:`elfpy.utils.parse_config`
==================================

.. py:module:: elfpy.utils.parse_config

.. autoapi-nested-parse::

   Utilities for parsing & loading user config TOML files

   ..
       !! processed by numpydoc !!


Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   elfpy.utils.parse_config.load_and_parse_config_file
   elfpy.utils.parse_config.load_config_file
   elfpy.utils.parse_config.parse_simulation_config
   elfpy.utils.parse_config.text_to_logging_level
   elfpy.utils.parse_config.override_config_variables



.. py:function:: load_and_parse_config_file(config_file: str) -> elfpy.utils.config.Config

   
   Wrapper function for loading a toml config file and parsing it.

   :param config_file: Absolute path to a toml config file.
   :type config_file: str

   :returns: **config** -- Nested dataclass with member classes MarketConfig, AMMConfig, and SimulatorConfig
   :rtype: Config















   ..
       !! processed by numpydoc !!

.. py:function:: load_config_file(config_file: str) -> dict

   
   Load a config file as a dictionary

   :param config_file: Absolute path to a toml config file.
   :type config_file: str

   :returns: **config_dict** -- Nested dictionary containing the market, amm, and simulator config dicts
   :rtype: dictionary















   ..
       !! processed by numpydoc !!

.. py:function:: parse_simulation_config(config_dict: dict) -> elfpy.utils.config.Config

   
   Parse the TOML config file and return a config object

   :param config_dict: Nested dictionary containing the market, amm, and simulator config dicts
   :type config_dict: dictionary

   :returns: **config** -- Nested dataclass with member classes MarketConfig, AMMConfig, and SimulatorConfig
   :rtype: Config















   ..
       !! processed by numpydoc !!

.. py:function:: text_to_logging_level(logging_text: str) -> int

   
   Converts logging level description to an integer

   :param logging_text: String description of the logging level; must be in ["debug", "info", "warning", "error", "critical"]
   :type logging_text: str

   :returns: Logging level integer corresponding to the string input
   :rtype: int















   ..
       !! processed by numpydoc !!

.. py:function:: override_config_variables(config: elfpy.utils.config.Config, override_dict: dict) -> elfpy.utils.config.Config

   
   Replace existing member & config variables with ones defined in override_dict

   :param config: config object, as defined in elfpy.utils.config
   :type config: Config
   :param override_dict: dictionary containing keys that correspond to member fields of the RandomSimulationVariables class
   :type override_dict: dict

   :returns: same dataclass as the config input, but with fields specified by override_dict changed
   :rtype: Config















   ..
       !! processed by numpydoc !!


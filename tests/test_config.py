"""Testing for Config class"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest

from elfpy.types import Config


class TestConfig(unittest.TestCase):
    """Test usage of the Config class"""

    def test_config_cant_add_new_attribs(self):
        """
        config object can't add new attributes after it's initialized
        """
        config = Config()
        with self.assertRaises(AttributeError):
            config.new_attrib = 1

    def test_config_cant_change_existing_attribs(self):
        """
        config object can change existing attributes, only if not frozen
        """
        config = Config()
        config.num_blocks_per_day = 2
        config.freeze()  # pylint: disable=no-member # type: ignore
        with self.assertRaises(AttributeError):
            config.num_blocks_per_day = 2

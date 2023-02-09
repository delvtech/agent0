"""Testing for ElfPy types"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest

import elfpy.types as elftypes


class TestStretchedTime(unittest.TestCase):
    """Test freezable wrapper functionality"""

    def test_freezability(self):
        """Test mutability of frozen objects

        Tests that freezable object is mutable when not frozen and
        throws an error when frozen and member attributes are changed
        """
        # make unfrozen variable & change attribute
        freezable = elftypes.StretchedTime(days=365, time_stretch=1, normalizing_constant=365)
        freezable.days = 10  # ok to override unfrozen attrib
        # freeze & try to change
        # NOTE: lint error false positives: This message may report object members that are created dynamically,
        # but exist at the time they are accessed.
        freezable.freeze()  # pylint: disable=no-member # type: ignore
        with self.assertRaises(AttributeError):
            freezable.days = 20

    def test_new_attribute(self):
        """Test adding an attribute to a freezable object

        Tests that freezable object can add new attributes after being frozen, but then they are immutable
        """
        for freezable in [
            elftypes.StretchedTime(days=365, time_stretch=1, normalizing_constant=365),
            elftypes.Config(),
        ]:
            # NOTE: lint error false positives: This message may report object members that are created dynamically,
            # but exist at the time they are accessed.
            freezable.freeze()  # pylint: disable=no-member # type: ignore
            freezable.new_attrib = "This is ok."  # type: ignore
            with self.assertRaises(AttributeError):
                freezable.new_attrib = "This is not ok."  # type: ignore

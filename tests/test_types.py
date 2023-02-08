"""Testing for ElfPy types"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest

import elfpy.types as elftypes


class TestStretchedTime(unittest.TestCase):
    def test_frozen_mutability(self):
        frozen = elftypes.StretchedTime(days=365, time_stretch=1, normalizing_constant=365, frozen=True)
        frozen.new_attribute = "this is ok"
        with self.assertRaises(AttributeError):
            frozen.days = 10

    def test_freezability(self):
        # using freeze method
        unfrozen = elftypes.StretchedTime(days=365, time_stretch=1, normalizing_constant=365, frozen=False)
        unfrozen.days = 10  # ok to override unfrozen attrib
        unfrozen.freeze()
        with self.assertRaises(AttributeError):
            unfrozen.days = 20
        # directly setting attribute
        unfrozen = elftypes.StretchedTime(days=365, time_stretch=1, normalizing_constant=365, frozen=False)
        unfrozen.days = 10
        unfrozen.frozen = True
        with self.assertRaises(AttributeError):
            unfrozen.days = 20

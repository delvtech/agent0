"""Testing for ElfPy types"""
from __future__ import annotations  # types are strings by default in 3.11

import unittest
from dataclasses import dataclass

from elfpy.types import freezable, Config


@dataclass
class ClassWithOneAttribute:
    """Class with one attribute"""

    existing_attrib = 1


@freezable(frozen=False, no_new_attribs=False)
@dataclass
class FreezableClass(ClassWithOneAttribute):
    """Freezable class unfrozen by default"""


@freezable(frozen=True, no_new_attribs=False)
@dataclass
class FreezableClassFrozenByDefault(ClassWithOneAttribute):
    """Freezable class frozen by default"""


@freezable(frozen=False, no_new_attribs=True)
@dataclass
class FreezableClassNoNewAttribsByDefault(ClassWithOneAttribute):
    """Freezable class with no_new_attribs set by default"""


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class FreezableClassFrozenNoNewAttribsByDefault(ClassWithOneAttribute):
    """Freezable class frozen and with no_new_attribs set by default"""


class TestFreezability(unittest.TestCase):
    """Test freezable wrapper functionality
    each test checks for the ability to change or add attributest, in 4 cases:
    1. not frozen
    2. frozen
    3. not frozen, but with "no_new_attribs" set
    4. frozen, and with "no_new_attribs" set
    the last 3 cases are set manually and by default in the decorator, for a total of 7 tests

    NOTE: pylint and pyright throw false positives due to difficulty checking members that are added dynamically
    """

    def test_freezable_when_not_set(self):
        """
        freezable object when frozen is NOT set, and no_new_attribs is NOT set
        desired behavior is: CAN change attributes, and CAN add attributes
        """
        freezable_object = FreezableClass()
        freezable_object.existing_attrib = 2
        freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_frozen_is_set(self):
        """
        freezable object when frozen IS set, but no_new_attribs is NOT set, manually
        desired behavior is: can NOT change attributes, and CAN add attributes
        """
        freezable_object = FreezableClass()
        freezable_object.freeze()  # pylint: disable=no-member # type: ignore
        with self.assertRaises(AttributeError):
            freezable_object.existing_attrib = 2
        freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_frozen_is_set_by_default(self):
        """
        freezable object when frozen IS set, but no_new_attribs is NOT set, by default
        desired behavior is: can NOT change attributes, and CAN add attributes
        """
        freezable_object = FreezableClassFrozenByDefault()
        with self.assertRaises(AttributeError):
            freezable_object.existing_attrib = 2
        freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_no_new_attribs_is_set(self):
        """
        freezable object when frozen is NOT set, but no_new_attribs IS set, manually
        desired behavior is: CAN change attributes, and can NOT add attributes
        """
        freezable_object = FreezableClass()
        freezable_object.disable_new_attribs()  # pylint: disable=no-member # type: ignore
        freezable_object.existing_attrib = 2
        with self.assertRaises(AttributeError):
            freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_no_new_attribs_is_set_by_default(self):
        """
        freezable object when frozen is NOT set, but no_new_attribs IS set, by default
        desired behavior is: CAN change attributes, and can NOT add attributes
        """
        freezable_object = FreezableClassNoNewAttribsByDefault()
        freezable_object.existing_attrib = 2
        with self.assertRaises(AttributeError):
            freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_frozen_is_set_and_no_new_attribs_is_set(self):
        """
        freezable object when frozen IS set, and no_new_attribs IS set, manually
        desired behavior is: can NOT change attributes, and can NOT add attributes
        """
        freezable_object = FreezableClass()
        freezable_object.freeze()  # pylint: disable=no-member # type: ignore
        freezable_object.disable_new_attribs()  # pylint: disable=no-member # type: ignore
        with self.assertRaises(AttributeError):
            freezable_object.existing_attrib = 2
        with self.assertRaises(AttributeError):
            freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_frozen_is_set_and_no_new_attribs_is_set_by_default(self):
        """
        freezable object when frozen IS set, and no_new_attribs IS set, by default
        desired behavior is: can NOT change attributes, and can NOT add attributes
        """
        freezable_object = FreezableClassFrozenNoNewAttribsByDefault()
        with self.assertRaises(AttributeError):
            freezable_object.existing_attrib = 2
        with self.assertRaises(AttributeError):
            freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

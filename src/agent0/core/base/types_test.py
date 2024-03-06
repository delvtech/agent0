"""Testing for agent0 types"""

from __future__ import annotations

import unittest
from dataclasses import dataclass

from .types import freezable

# dynamic member attribution breaks pylint
# pylint: disable=no-member


@dataclass
class ClassWithOneAttribute:
    """Class with one attribute"""

    existing_attrib: int = 1


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
        """Freezable object when frozen is NOT set, and no_new_attribs is NOT set
        desired behavior is: CAN change attributes, and CAN add attributes
        """
        freezable_object = FreezableClass()
        freezable_object.existing_attrib = 2
        freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_frozen_is_set(self):
        """Freezable object when frozen IS set, but no_new_attribs is NOT set, manually
        desired behavior is: can NOT change attributes, and CAN add attributes
        """
        freezable_object = FreezableClass()
        freezable_object.freeze()  # pylint: disable=no-member # type: ignore
        with self.assertRaises(AttributeError):
            freezable_object.existing_attrib = 2
        freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_frozen_is_set_by_default(self):
        """Freezable object when frozen IS set, but no_new_attribs is NOT set, by default
        desired behavior is: can NOT change attributes, and CAN add attributes
        """
        freezable_object = FreezableClassFrozenByDefault()
        with self.assertRaises(AttributeError):
            freezable_object.existing_attrib = 2
        freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_no_new_attribs_is_set(self):
        """Freezable object when frozen is NOT set, but no_new_attribs IS set, manually
        desired behavior is: CAN change attributes, and can NOT add attributes
        """
        freezable_object = FreezableClass()
        freezable_object.disable_new_attribs()  # pylint: disable=no-member # type: ignore
        freezable_object.existing_attrib = 2
        with self.assertRaises(AttributeError):
            freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_no_new_attribs_is_set_by_default(self):
        """Freezable object when frozen is NOT set, but no_new_attribs IS set, by default
        desired behavior is: CAN change attributes, and can NOT add attributes
        """
        freezable_object = FreezableClassNoNewAttribsByDefault()
        freezable_object.existing_attrib = 2
        with self.assertRaises(AttributeError):
            freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_frozen_is_set_and_no_new_attribs_is_set(self):
        """Freezable object when frozen IS set, and no_new_attribs IS set, manually
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
        """Freezable object when frozen IS set, and no_new_attribs IS set, by default
        desired behavior is: can NOT change attributes, and can NOT add attributes
        """
        freezable_object = FreezableClassFrozenNoNewAttribsByDefault()
        with self.assertRaises(AttributeError):
            freezable_object.existing_attrib = 2
        with self.assertRaises(AttributeError):
            freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_dtypes(self):
        """Test dtype casting & checking capability of classes that have the freezable decorator"""
        freezable_object = FreezableClass(existing_attrib=4)
        # cast to int, check that it is an int
        assert isinstance(
            freezable_object.astype(int).existing_attrib,  # type: ignore
            int,
        )
        # cast to float, check that it is a float
        assert isinstance(
            freezable_object.astype(float).existing_attrib,  #  type: ignore
            float,
        )
        # cast to str, check that it is a str
        assert isinstance(
            freezable_object.astype(str).existing_attrib,  #  type: ignore
            str,
        )
        # cast to str, make sure value is correct
        assert freezable_object.astype(str).existing_attrib == "4"  # type: ignore
        # get dtypes, confirm the key exists & that it is an int
        assert "existing_attrib" in freezable_object.dtypes.keys()  #  type: ignore
        assert freezable_object.dtypes["existing_attrib"] == int  #  type: ignore
        # cast to float, make sure dtypes updates
        assert freezable_object.astype(float).dtypes["existing_attrib"] == float  #  type: ignore
        # cast to float, make sure value is correct
        assert freezable_object.astype(float).existing_attrib == 4.0  #  type: ignore
        # check that attrib gets updated with new type
        assert freezable_object.astype(float).__annotations__["existing_attrib"] == float  #  type: ignore
        # ERROR case: changing type to something that is not compatible
        freezable_object = FreezableClass(existing_attrib="bleh")  #  type: ignore
        with self.assertRaises(TypeError):
            freezable_object.astype(int)  #  type: ignore

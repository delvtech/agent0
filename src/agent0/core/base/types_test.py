"""Testing for agent0 types."""

from __future__ import annotations

import unittest
from dataclasses import dataclass

from .types import Freezable

# missing docstring
# ruff: noqa: D105
# magic value used in comparison
# ruff: noqa: PLR2004


@dataclass
class ClassWithOneAttribute:
    """Class with one attribute."""

    existing_attrib: int = 1


@dataclass
class FreezableClass(ClassWithOneAttribute, Freezable):
    """Freezable class unfrozen by default."""


@dataclass
class FreezableClassFrozenByDefault(ClassWithOneAttribute, Freezable):
    """Freezable class frozen by default."""

    def __post_init__(self):
        self.freeze()


@dataclass
class FreezableClassNoNewAttribsByDefault(ClassWithOneAttribute, Freezable):
    """Freezable class with no_new_attribs set by default."""

    def __post_init__(self):
        self.disable_new_attribs()


@dataclass
class FreezableClassFrozenNoNewAttribsByDefault(ClassWithOneAttribute, Freezable):
    """Freezable class frozen and with no_new_attribs set by default."""

    def __post_init__(self):
        self.freeze()
        self.disable_new_attribs()


class TestFreezability(unittest.TestCase):
    """Test freezable wrapper functionality.

    each test checks for the ability to change or add attributest, in 4 cases:
    1. not frozen
    2. frozen
    3. not frozen, but with "no_new_attribs" set
    4. frozen, and with "no_new_attribs" set
    the last 3 cases are set manually and by default in the decorator, for a total of 7 tests
    """

    def test_freezable_when_not_set(self):
        """Freezable object when frozen is NOT set, and no_new_attribs is NOT set.

        Desired behavior is: CAN change attributes, and CAN add attributes
        """
        freezable_object = FreezableClass()
        freezable_object.existing_attrib = 2
        freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_frozen_is_set(self):
        """Freezable object when frozen IS set, but no_new_attribs is NOT set, manually.

        Desired behavior is: can NOT change attributes, and CAN add attributes
        """
        freezable_object = FreezableClass()
        freezable_object.freeze()
        with self.assertRaises(AttributeError):
            freezable_object.existing_attrib = 2
        freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_frozen_is_set_by_default(self):
        """Freezable object when frozen IS set, but no_new_attribs is NOT set, by default.

        Desired behavior is: can NOT change attributes, and CAN add attributes
        """
        freezable_object = FreezableClassFrozenByDefault()
        with self.assertRaises(AttributeError):
            freezable_object.existing_attrib = 2
        freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_no_new_attribs_is_set(self):
        """Freezable object when frozen is NOT set, but no_new_attribs IS set, manually.

        Desired behavior is: CAN change attributes, and can NOT add attributes
        """
        freezable_object = FreezableClass()
        freezable_object.disable_new_attribs()
        freezable_object.existing_attrib = 2
        with self.assertRaises(AttributeError):
            freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_no_new_attribs_is_set_by_default(self):
        """Freezable object when frozen is NOT set, but no_new_attribs IS set, by default.

        Desired behavior is: CAN change attributes, and can NOT add attributes
        """
        freezable_object = FreezableClassNoNewAttribsByDefault()
        freezable_object.existing_attrib = 2
        with self.assertRaises(AttributeError):
            freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_frozen_is_set_and_no_new_attribs_is_set(self):
        """Freezable object when frozen IS set, and no_new_attribs IS set, manually.

        Desired behavior is: can NOT change attributes, and can NOT add attributes
        """
        freezable_object = FreezableClass()
        freezable_object.freeze()
        freezable_object.disable_new_attribs()
        with self.assertRaises(AttributeError):
            freezable_object.existing_attrib = 2
        with self.assertRaises(AttributeError):
            freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_freezable_when_frozen_is_set_and_no_new_attribs_is_set_by_default(self):
        """Freezable object when frozen IS set, and no_new_attribs IS set, by default.

        Desired behavior is: can NOT change attributes, and can NOT add attributes
        """
        freezable_object = FreezableClassFrozenNoNewAttribsByDefault()
        with self.assertRaises(AttributeError):
            freezable_object.existing_attrib = 2
        with self.assertRaises(AttributeError):
            freezable_object.new_attrib = 1  # pylint: disable=attribute-defined-outside-init # type: ignore

    def test_dtypes(self):
        """Test dtype casting & checking capability of classes that have the freezable decorator."""
        freezable_object = FreezableClass(existing_attrib=4)
        # cast to int, check that it is an int
        assert isinstance(
            freezable_object.astype(int).existing_attrib,
            int,
        )
        # cast to float, check that it is a float
        assert isinstance(
            freezable_object.astype(float).existing_attrib,
            float,
        )
        # cast to str, check that it is a str
        assert isinstance(
            freezable_object.astype(str).existing_attrib,
            str,
        )
        # cast to str, make sure value is correct
        assert freezable_object.astype(str).existing_attrib == "4"
        # get dtypes, confirm the key exists & that it is an int
        assert "existing_attrib" in freezable_object.dtypes.keys()
        assert freezable_object.dtypes["existing_attrib"] == int
        # cast to float, make sure dtypes updates
        assert freezable_object.astype(float).dtypes["existing_attrib"] == float
        # cast to float, make sure value is correct
        assert freezable_object.astype(float).existing_attrib == 4.0
        # check that attrib gets updated with new type
        assert freezable_object.astype(float).__annotations__["existing_attrib"] == float  # pylint: disable=no-member
        # ERROR case: changing type to something that is not compatible
        freezable_object = FreezableClass(existing_attrib="bleh")  # type: ignore
        with self.assertRaises(TypeError):
            freezable_object.astype(int)

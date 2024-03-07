"""Various agent0 utility functions."""

from typing import NoReturn


def assert_never(arg: NoReturn) -> NoReturn:
    """Helper function for exhaustive matching on ENUMS.

    .. note::
        This ensures that all ENUM values are checked, via an exhaustive match:
        https://github.com/microsoft/pyright/issues/2569

    Arguments
    ---------
    arg: NoReturn
        The enum value.
    """
    assert False, f"Unhandled type: {type(arg).__name__}"

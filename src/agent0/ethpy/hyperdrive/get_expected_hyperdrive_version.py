"""Function to read `min-hyperdrive.version`."""

import pathlib

from packaging.version import Version


def get_minimum_hyperdrive_version() -> str:
    """Get the minimum hyperdrive version from the `min-hyperdrive.version` file.

    Returns
    -------
    str
        The minimum hyperdrive version.
    """
    # Use relative path wrt this file
    version_path = (pathlib.Path(__file__).parent.parent.parent / "min-hyperdrive.version").resolve()
    with open(version_path, "r", encoding="UTF-8") as f:
        expected_versions = f.readlines()
    # Strip newlines
    expected_versions = [v.strip() for v in expected_versions]
    if len(expected_versions) != 1:
        raise ValueError(f"Expected exactly 1 minimum version in {version_path}, got {len(expected_versions)}")

    return expected_versions[0]


def check_hyperdrive_version(in_version: str) -> bool:
    """Checks that the version meets the minimum hyperdrive version.

    Arguments
    ---------
    in_version: str
        The version string to check.

    Returns
    -------
    bool
        True if the version meets the minimum hyperdrive version.
    """

    return Version(in_version) >= Version(get_minimum_hyperdrive_version())

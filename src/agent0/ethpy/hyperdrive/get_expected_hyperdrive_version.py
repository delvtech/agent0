"""Function to read `hyperdrive.version`."""

import pathlib


def get_expected_hyperdrive_version() -> str:
    """Get the hyperdrive version from the `hyperdrive.version` file.

    Returns
    -------
    str
        The expected hyperdrive version read from the `hyperdrive.version` file.
    """
    # Use relative path wrt this file
    version_path = (pathlib.Path(__file__).parent.parent.parent.parent.parent / "hyperdrive.version").resolve()
    with open(version_path, "r", encoding="UTF-8") as f:
        version = f.readline()

    return version


if __name__ == "__main__":
    print(get_expected_hyperdrive_version())

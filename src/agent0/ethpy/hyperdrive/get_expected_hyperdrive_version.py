"""Function to read `hyperdrive.version`."""

import pathlib


def get_expected_hyperdrive_version() -> list[str]:
    """Get the hyperdrive version from the `hyperdrive.version` file.

    Returns
    -------
    list[str]
        The expected hyperdrive versions read from the `hyperdrive.version` file.
    """
    # Use relative path wrt this file
    version_path = (pathlib.Path(__file__).parent.parent.parent / "hyperdrive.version").resolve()
    with open(version_path, "r", encoding="UTF-8") as f:
        versions = f.readlines()
    # Strip newlines
    versions = [v.strip() for v in versions]

    return versions


if __name__ == "__main__":
    print(get_expected_hyperdrive_version())

from enum import Enum


class HyperdriveKind(Enum):
    """Hyperdrive contract kind."""

    ERC4626 = "ERC4626"
    STETH = "STETH"
    MORPHOBLUE = "MORPHOBLUE"

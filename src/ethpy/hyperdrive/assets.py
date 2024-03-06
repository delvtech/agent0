"""Hyperdrive AssetId classes and methods"""

from enum import IntEnum

# TODO get this value from the deployed pool, putting this here now for reference
# across everything
BASE_TOKEN_SYMBOL = "WETH"


class AssetIdPrefix(IntEnum):
    r"""The asset ID is used to encode the trade type in a transaction receipt"""

    LP = 0
    LONG = 1
    SHORT = 2
    WITHDRAWAL_SHARE = 3


def encode_asset_id(prefix: int, timestamp: int) -> int:
    r"""Encodes a prefix and a timestamp into an asset ID.

    Asset IDs are used so that LP, long, and short tokens can all be represented
    in a single MultiToken instance. The zero asset ID indicates the LP token.

    Encode the asset ID by left-shifting the prefix by 248 bits,
    then bitwise-or-ing the result with the timestamp.

    Arguments
    ---------
    prefix: int
        A one byte prefix that specifies the asset type.
    timestamp: int
        A timestamp associated with the asset.

    Returns
    -------
    int
        The asset ID.
    """
    timestamp_mask = (1 << 248) - 1
    if timestamp > timestamp_mask:
        raise ValueError("Invalid timestamp")
    return (prefix << 248) | timestamp


def decode_asset_id(asset_id: int) -> tuple[int, int]:
    r"""Decodes a transaction asset ID into its constituent parts of an identifier, data, and a timestamp.

    First calculate the prefix mask by left-shifting 1 by 248 bits and subtracting 1 from the result.
    This gives us a bit-mask with 248 bits set to 1 and the rest set to 0.
    Then apply this mask to the input ID using the bitwise-and operator `&` to extract
    the lower 248 bits as the timestamp.

    Arguments
    ---------
    asset_id: int
        Encoded ID from a transaction. It is a concatenation, [identifier: 8 bits][timestamp: 248 bits]

    Returns
    -------
    tuple[int, int]
        identifier, timestamp
    """
    prefix_mask = (1 << 248) - 1
    prefix = asset_id >> 248  # shr 248 bits
    timestamp = asset_id & prefix_mask  # apply the prefix mask
    return prefix, timestamp

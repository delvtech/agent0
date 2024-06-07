"""Make a private key using web3 eth utils"""

import os

from eth_utils.conversions import to_bytes
from eth_utils.crypto import keccak
from eth_utils.curried import text_if_str
from hexbytes import HexBytes


def make_private_key(extra_entropy: str = "SOME STRING") -> str:
    """Make a private key.

    Arguments
    ---------
    extra_entropy: str, optional
        Any string used to add entropy to the keccak hash.
        Defaults to "SOME STRING".

    Returns
    -------
    str
        The private key.
    """
    extra_key_bytes = text_if_str(to_bytes, extra_entropy)
    key_bytes = keccak(os.urandom(32) + extra_key_bytes)
    return HexBytes(key_bytes).hex()

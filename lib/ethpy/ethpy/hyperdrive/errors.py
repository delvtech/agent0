"""Error handling for the hyperdrive ecosystem"""

from typing import NamedTuple


# TODO: get error names from the ABI, encode to get the selector, match selector with name.  For now
# this is hard coded list of errors in all the contracts we use.
def lookup_hyperdrive_error_selector(error_selector: str) -> str:
    """Get the error name for a given error selector.

    Arguments
    ---------
    error_selector: str
        A 3 byte hex string obtained from a keccak256 has of the error signature, i.e.
        'InvalidToken()' would yield '0xc1ab6dc1'.

    Returns
    -------
    str
       The name of the error.
    """
    return getattr(_hyperdrive_errors, error_selector)


class HyperdriveErrors(NamedTuple):
    """A collection of error selectors by the name."""

    # TODO Ideally use pypechain generated errors
    # Gathered from IHyperdrive.json abi

    BatchInputLengthMismatch: str = "0xba430d38"
    BelowMinimumContribution: str = "0xabed41c4"
    ExpInvalidExponent: str = "0x73a2d6b1"
    ExpiredDeadline: str = "0xf87d9271"
    InsufficientLiquidity: str = "0x780daf16"
    InvalidApr: str = "0x76c22a22"
    InvalidBaseToken: str = "0x0e442a4a"
    InvalidCheckpointDuration: str = "0x5428734d"
    InvalidCheckpointTime: str = "0xecd29e81"
    InvalidERC20Bridge: str = "0x2aab8bd3"
    InvalidFeeAmounts: str = "0x45ee5986"
    InvalidFeeDestination: str = "0x2b44eccc"
    InvalidInitialVaultSharePrice: str = "0x094b19ad"
    InvalidMinimumShareReserves: str = "0x49db44f5"
    InvalidPositionDuration: str = "0x4a7fff9e"
    InvalidShareReserves: str = "0xb0bfcdbe"
    InvalidSignature: str = "0x8baa579f"
    InvalidTimestamp: str = "0xb7d09497"
    LnInvalidInput: str = "0xe61b4975"
    MinimumSharePrice: str = "0x42af972b"
    MinimumTransactionAmount: str = "0x423bbb46"
    NegativePresentValue: str = "0xaeeb825d"
    NotPayable: str = "0x1574f9f3"
    OutputLimit: str = "0xc9726517"
    PoolAlreadyInitialized: str = "0x7983c051"
    PoolIsPaused: str = "0x21081abf"
    RestrictedZeroAddress: str = "0xf0dd15fd"
    ReturnData: str = "0xdcc81126"
    SweepFailed: str = "0x9eec2ff8"
    TransferFailed: str = "0x90b8ec18"
    Unauthorized: str = "0x82b42900"
    UnexpectedSuccess: str = "0x8bb0a34b"
    UnsafeCastToUint112: str = "0x10d62a2e"
    UnsafeCastToUint128: str = "0x1e15f2a2"
    UnsafeCastToInt128: str = "0xa5353be5"
    UnsupportedToken: str = "0x6a172882"


_hyperdrive_errors = HyperdriveErrors()

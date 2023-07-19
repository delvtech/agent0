"""Error handling for the hyperdrive ecosystem"""
from typing import NamedTuple


# TODO: get error names from the ABI, encode to get the selector, match selector with name.  For now
# this is hard coded list of errors in all the contracts we use.
def decode_hyperdrive_errors(error_selector: str) -> str:
    """Get the error name for a given error selector."""
    return getattr(_hyperdrive_errors, error_selector)


class HyperdriveErrors(NamedTuple):
    """A collection of error selectors by the name."""

    ##################
    ### Hyperdrive ###
    ##################
    BaseBufferExceedsShareReserves: str = "0x18846de9"
    InvalidApr: str = "0x76c22a22"
    InvalidBaseToken: str = "0x0e442a4a"
    InvalidCheckpointTime: str = "0xecd29e81"
    InvalidInitialSharePrice: str = "0x55f2a42f"
    InvalidMaturityTime: str = "0x987dadd3"
    InvalidPositionDuration: str = "0x4a7fff9e"
    InvalidFeeAmounts: str = "0x45ee5986"
    NegativeInterest: str = "0x512095c7"
    OutputLimit: str = "0xc9726517"
    Paused: str = "0x9e87fac8"
    PoolAlreadyInitialized: str = "0x7983c051"
    TransferFailed: str = "0x90b8ec18"
    UnexpectedAssetId: str = "0xe9bf5433"
    UnsupportedToken: str = "0x6a172882"
    ZeroAmount: str = "0x1f2a2005"
    ZeroLpTotalSupply: str = "0x252c3a3e"
    ZeroLpTotalSupply: str = "0x252c3a3e"

    ############
    ### TWAP ###
    ############
    QueryOutOfRange: str = "0xa89817b0"

    ####################
    ### DataProvider ###
    ####################
    UnexpectedSuccess: str = "0x8bb0a34b"

    ###############
    ### Factory ###
    ###############
    Unauthorized: str = "0x82b42900"
    InvalidContribution: str = "0x652122d9"
    InvalidToken: str = "0xc1ab6dc1"

    ######################
    ### ERC20Forwarder ###
    ######################
    BatchInputLengthMismatch: str = "0xba430d38"
    ExpiredDeadline: str = "0xf87d9271"
    InvalidSignature: str = "0x8baa579f"
    InvalidERC20Bridge: str = "0x2aab8bd3"
    RestrictedZeroAddress: str = "0xf0dd15fd"

    ###################
    ### BondWrapper ###
    ###################
    AlreadyClosed: str = "0x9acb7e52"
    BondMatured: str = "0x3f8e46bc"
    BondNotMatured: str = "0x915eceb1"
    InsufficientPrice: str = "0xd5481703"

    ###############
    ### AssetId ###
    ###############
    InvalidTimestamp: str = "0xb7d09497"

    ######################
    ### FixedPointMath ###
    ######################
    FixedPointMath_AddOverflow: str = "0x2d59cfbd"
    FixedPointMath_SubOverflow: str = "0x35ba1440"
    FixedPointMath_InvalidExponent: str = "0xdf92cc9d"
    FixedPointMath_NegativeOrZeroInput: str = "0xac5f1b8e"
    FixedPointMath_NegativeInput: str = "0x2c7949f5"


_hyperdrive_errors = HyperdriveErrors()

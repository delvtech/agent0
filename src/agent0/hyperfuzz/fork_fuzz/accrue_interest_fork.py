"""Function to accrue interest in underlying yields when fork fuzzing."""

from fixedpointmath import FixedPoint

from agent0.ethpy.hyperdrive import HyperdriveReadWriteInterface

from .accrue_interest_ezeth import accrue_interest_ezeth


def accrue_interest_fork(interface: HyperdriveReadWriteInterface, variable_rate: FixedPoint):
    # Switch case for pool types for interest accrual
    # TODO do we need to switch chain?
    hyperdrive_kind = interface.hyperdrive_kind
    match hyperdrive_kind:
        case interface.HyperdriveKind.EZETH:
            accrue_interest_ezeth(interface, variable_rate)

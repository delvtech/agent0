"""Tests of economic intuition."""

import pytest
from fixedpointmath import FixedPoint

from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive

YEAR_IN_SECONDS = 31_536_000


@pytest.mark.anvil
def test_symmetry(fast_chain_fixture: LocalChain):
    """Does in equal out?

    One may be under the impression swaps between x and y have the same result, irrespective of direction.
    We set the number of bonds in and out to 100k and see if the resulting shares_in and shares_out differ."""
    interactive_config = LocalHyperdrive.Config(
        position_duration=YEAR_IN_SECONDS,  # 1 year term
        governance_lp_fee=FixedPoint(0.1),
        curve_fee=FixedPoint(0.01),
        flat_fee=FixedPoint(0),
    )
    interactive_hyperdrive = LocalHyperdrive(fast_chain_fixture, interactive_config)
    interface = interactive_hyperdrive.interface
    shares_out = interface.calc_shares_out_given_bonds_in_down(FixedPoint(100_000))
    shares_in = interface.calc_shares_in_given_bonds_out_down(FixedPoint(100_000))
    print(shares_out)
    print(shares_in)
    assert shares_out != shares_in

"""Calculate the high and low thresholds for maximally profitable trading.

1. Do the trade without fees.
    - calculate effective price
2. Do the trade with fees.
    - calculate effective price
3. Find the trade amount that matches the no-fee price?
"""

# %%
from fixedpointmath import FixedPoint

from agent0 import ILocalChain, ILocalHyperdrive

# %%
chain = ILocalChain()
interactive_hyperdrive = ILocalHyperdrive(
    chain,
    ILocalHyperdrive.Config(
        initial_fixed_apr=FixedPoint("0.05"),
        initial_variable_rate=FixedPoint("0.01"),
        curve_fee=FixedPoint("0.01"),
        flat_fee=FixedPoint("0.0005"),
        governance_lp_fee=FixedPoint("0.15"),
        governance_zombie_fee=FixedPoint("0.03"),
    ),
)

# %%
agent0 = interactive_hyperdrive.init_agent(base=FixedPoint(1_000_000), eth=FixedPoint(1_000))

pool_state = interactive_hyperdrive.interface.current_pool_state
bonds_purchased = interactive_hyperdrive.interface.calc_open_long(base_amount=FixedPoint(100), pool_state=pool_state)
# effective_price =


def calc_deadzone_threshold(interface: HyperdriveReadInterface, pool_state: PoolState, target_rate: FixedPoint):
    """Calculate the high and low thresholds for maximally profitable trading.

    1. Do the trade without fees.
      - calculate effective price
    2. Do the trade with fees.
      - calculate effective price
    3. Find the trade amount that matches the no-fee price?
    """
    annualized_position_duration = interface.calc_position_duration_in_years(pool_state)
    spot_price_at_rate = FixedPoint(1) / (target_rate * annualized_position_duration + FixedPoint(1))

# %%
from fixedpointmath import FixedPoint, FixedPointMath

from agent0.hyperdrive.interactive import ILocalChain, ILocalHyperdrive
from agent0.hyperdrive.interactive.event_types import AddLiquidity
from agent0.hyperdrive.policies import PolicyZoo

# %%
chain = ILocalChain()

# Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
# We explicitly set initial liquidity here to ensure we have withdrawal shares when trading
initial_pool_config = ILocalHyperdrive.Config(
    initial_liquidity=FixedPoint(10_000),
    initial_fixed_apr=FixedPoint("0.05"),
    position_duration=60 * 60 * 24 * 30,  # 1 month
    checkpoint_duration=60 * 60 * 24,  # 1 day
)
interactive_hyperdrive = ILocalHyperdrive(chain, initial_pool_config)
pnl_target = FixedPoint("0.5")
lp_agent = interactive_hyperdrive.init_agent(
    base=FixedPoint(1_111_111),
    eth=FixedPoint(111),
    name="Lisa",
    policy=PolicyZoo.simple_lp,
    policy_config=PolicyZoo.simple_lp.Config(
        lookback_length=FixedPoint("5"),
        pnl_target=pnl_target,
        delta_liquidity=FixedPoint("1_000"),
    ),
)

# %%

# execute first policy action
trade_event_list = lp_agent.execute_policy_action()

# only one trade per action execution
assert len(trade_event_list) == 1
# always should be add liquidity
assert isinstance(trade_event_list[0], AddLiquidity)
# always should be 1_000
assert FixedPointMath.isclose(trade_event_list[0].lp_amount, FixedPoint("1_000"), abs_tol=FixedPoint("0.001"))
# no other trades, so agent PNL should stay 0
assert lp_agent.agent.policy.sub_policy.pnl_history[0][1] == FixedPoint("0")

# do a dumb trade
hyperdrive_agent0 = interactive_hyperdrive.init_agent(base=FixedPoint(1_111_111), eth=FixedPoint(111), name="Bob")
open_event = hyperdrive_agent0.open_short(FixedPoint("100"))
chain.advance_time(60 * 60 * 24 * 7, create_checkpoints=False)
hyperdrive_agent0.close_short(open_event.maturity_time, open_event.bond_amount)

# %%
# big loss from agent0, so LP should get profit and add liquidity again
trade_event_list = lp_agent.execute_policy_action()
assert len(trade_event_list) == 1  # only one trade per action execution
assert isinstance(trade_event_list[0], AddLiquidity)  # always should be add liquidity
assert trade_event_list[0].lp_amount == FixedPoint("1_000")  # always should be 1_000
assert lp_agent.agent.policy.sub_policy.pnl_history[0][1] == FixedPoint("0")

# %%

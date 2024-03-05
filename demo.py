import datetime

from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import ILocalChain, ILocalHyperdrive

chain = ILocalChain(ILocalChain.Config())
interactive_hyperdrive = ILocalHyperdrive(chain, ILocalHyperdrive.Config())

agent0 = interactive_hyperdrive.init_agent(base=FixedPoint(100000), eth=FixedPoint(100), name="alice")

open_event = agent0.open_long(base=FixedPoint(100))
chain.advance_time(datetime.timedelta(weeks=52), create_checkpoints=False)
close_event = agent0.close_long(open_event.maturity_time, open_event.bond_amount)


pool_state = interactive_hyperdrive.get_pool_state(coerce_float=True)

pool_state.plot(x="block_number", y="longs_outstanding", kind="line")

interactive_hyperdrive.dashboard_subprocess

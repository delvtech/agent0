"""Example script showing example dashboard hyperdrive."""

# pylint: disable=pointless-statement
import time

from fixedpointmath import FixedPoint

from agent0 import LocalChain, LocalHyperdrive, PolicyZoo

local_chain_config = LocalChain.Config()
chain = LocalChain(local_chain_config)

initial_pool_config = LocalHyperdrive.Config()
hyperdrive0 = LocalHyperdrive(chain, initial_pool_config)

agent0 = hyperdrive0.init_agent(
    base=FixedPoint(100000),
    eth=FixedPoint(100),
    name="random_bot",
    # The underlying policy to attach to this agent
    policy=PolicyZoo.random,
    # The configuration for the underlying policy
    policy_config=PolicyZoo.random.Config(rng_seed=123),
)

initial_pool_config = LocalHyperdrive.Config()
hyperdrive1 = LocalHyperdrive(chain, initial_pool_config)

agent1 = hyperdrive1.init_agent(
    base=FixedPoint(100000),
    eth=FixedPoint(100),
    name="random_bot",
    # The underlying policy to attach to this agent
    policy=PolicyZoo.random,
    # The configuration for the underlying policy
    policy_config=PolicyZoo.random.Config(rng_seed=345),
)

chain.run_dashboard(blocking=False)

for i in range(100):
    # NOTE Since a policy can execute multiple trades per action, the output events is a list
    trade_events: list = agent0.execute_policy_action()
    # NOTE Since a policy can execute multiple trades per action, the output events is a list
    trade_events: list = agent1.execute_policy_action()
    # Slow down execution to see dashboard better
    time.sleep(1)

chain.cleanup()

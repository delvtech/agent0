import numpy as np
from fixedpointmath import FixedPoint

from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive
from agent0.core.hyperdrive.interactive.local_hyperdrive_agent import LocalHyperdriveAgent
from agent0.ethpy.hyperdrive.interface.read_write_interface import HyperdriveReadWriteInterface

TIME_STRETCH_APR = 0.1
STARTING_RATE = 0.1
DELTA = 1e18
YEAR_IN_SECONDS = 31_536_000
START_LIQ = FixedPoint(100_000)


def calc_price_and_rate(interface:HyperdriveReadWriteInterface):
    price = interface.calc_spot_price()
    rate = interface.calc_spot_rate()
    return price, rate

def trade(interface:HyperdriveReadWriteInterface, agent:LocalHyperdriveAgent, trade_portion, max_long, max_short):
    relevant_max = max_long if trade_portion > 0 else max_short
    trade_size = float(relevant_max) * trade_portion
    trade_result = trade_long(interface, agent, trade_size) if trade_size > 0 else trade_short(interface, agent, abs(trade_size))
    return *trade_result, trade_size

def trade_long(interface:HyperdriveReadWriteInterface, agent:LocalHyperdriveAgent, trade_size):
    try:
        trade_result = agent.open_long(base=FixedPoint(trade_size))
        base_traded = trade_result.amount
        bonds_traded = trade_result.bond_amount
        return *calc_price_and_rate(interface), base_traded, bonds_traded
    except:
        pass
    return None, None, None, None

def trade_short(interface:HyperdriveReadWriteInterface, agent:LocalHyperdriveAgent, trade_size):
    try:
        trade_result = agent.open_short(bonds=FixedPoint(trade_size))
        base_traded = -trade_result.amount
        bonds_traded = -trade_result.bond_amount
        return *calc_price_and_rate(interface), base_traded, bonds_traded
    except:
        pass
    return None, None, None, None

def calc_shorts(chain:LocalChain, interface:HyperdriveReadWriteInterface):
    # pseudo calc_targeted_short
    chain.save_snapshot()
    price, rate, base_traded, bonds_traded_short, trade_size = trade(interface, agent1, 1, interface.calc_max_long(budget=FixedPoint(1e18)), interface.calc_max_short(budget=FixedPoint(1e18)))
    print(f"max long  rate = {float(rate):,.5%}")
    chain.load_snapshot()
    price, rate, base_traded, bonds_traded_short, trade_size = trade(interface, agent1, -1, interface.calc_max_long(budget=FixedPoint(1e18)), interface.calc_max_short(budget=FixedPoint(1e18)))
    print(f"max short rate = {float(rate):,.5%}")
    max_delta = np.floor((float(rate)-TIME_STRETCH_APR)*100)/100
    short_target = STARTING_RATE + min(DELTA, max_delta)
    pool_info = interface.current_pool_state.pool_info
    print("=== POOL INFO ===")
    for d in dir(pool_info):
        if not d.startswith("_"):
            print(f" {d} = {getattr(pool_info, d)}")
    print(f"trying to calculate targeted long, target={short_target:,.5%}, current rate={float(interface.calc_spot_rate()):,.5%}")
    trade_size = interface.calc_targeted_long(budget=FixedPoint(1e18), target_rate=FixedPoint(short_target))
    bonds_traded_long = 0
    if trade_size > minimum_transaction_amount:
        price, rate, base_traded, bonds_traded_long = trade_long(interface, agent1, trade_size)
    chain.load_snapshot()
    return bonds_traded_short, bonds_traded_long, short_target

print(f"=== {TIME_STRETCH_APR=} {DELTA=} ===")
chain = LocalChain(LocalChain.Config(chain_port=10_000, db_port=10_001))
interactive_config = LocalHyperdrive.Config(
    position_duration=YEAR_IN_SECONDS,  # 1 year term
    governance_lp_fee=FixedPoint(0),
    curve_fee=FixedPoint(0),
    flat_fee=FixedPoint(0),
    initial_liquidity=START_LIQ,
    initial_fixed_apr=FixedPoint(TIME_STRETCH_APR),
    initial_time_stretch_apr=FixedPoint(TIME_STRETCH_APR),
    factory_min_fixed_apr=FixedPoint(0.001),
    factory_max_fixed_apr=FixedPoint(1000),
    factory_min_time_stretch_apr=FixedPoint(0.001),
    factory_max_time_stretch_apr=FixedPoint(1000),
    minimum_share_reserves=FixedPoint(0.001),
    factory_max_circuit_breaker_delta=FixedPoint(1000),
    circuit_breaker_delta=FixedPoint(1e3),
    initial_variable_rate=FixedPoint(STARTING_RATE),
)
hyperdrive:LocalHyperdrive = LocalHyperdrive(chain, interactive_config)
interface:HyperdriveReadWriteInterface = hyperdrive.interface
minimum_transaction_amount = interface.pool_config.minimum_transaction_amount
agent1 = chain.init_agent(base=FixedPoint(1e18), eth=FixedPoint(1e18), pool=hyperdrive)
calc_shorts(chain=chain, interface=interface)
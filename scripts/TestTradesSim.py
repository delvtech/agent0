import numpy as np
import json
#from genson import SchemaBuilder
from PricingModels import *

runs={}
np.random.seed(1)

t_max=0.25
t_min=.00025
step_size=.00025
num_steps=int(t_max/step_size)
times = np.arange(t_min, t_max+step_size, step_size) 
np.random.shuffle(times)
max_apy = 200
max_x_reserves=1000000.0

g=.1



x_orders=0
x_volume=0
y_orders=0
y_volume=0
trades = []
init = {
    "percent_fee": float("{:.18f}".format(g)),
    "t_max": float("{:.18f}".format(t_max)),
    "t_min": float("{:.18f}".format(t_min)),
    "num_tests": float("{:.18f}".format(len(times))),
    "max_apy": float("{:.18f}".format(max_apy)),
    "max_x_reserves": float("{:.18f}".format(max_x_reserves)),
}
for t in times:
    # determine APY
    apy = np.random.uniform(0,max_apy)
    # determine base reserves
    x_reserves = np.random.uniform(0,max_x_reserves)
    # use apy and x_reserves to calculate y_reserves and total_supply
    #    apy = (y_reserves+total_supply)/x_reserves - 1
    #    y_reserves+total_supply = (apy/100 + 1)*x_reserves
    
    y_reserves_plus_total_supply=(apy/100+1)*(x_reserves+y_reserves)
    y_weight = np.random.uniform(0,1)
    y_reserves = y_reserves_plus_total_supply * y_weight
    total_supply = y_reserves_plus_total_supply - y_reserves
    
    # determine order size (bounded)
    amount = np.random.uniform(0,min(min(x_reserves,y_reserves),total_supply)/50)
    m = Market(x_reserves,y_reserves,g,t,total_supply,Element_Pricing_Model)
    #print("time = " + str(t) + " apy = " + str(apy) + " x = " + str(x_reserves) + " y = " + str(y_reserves) + " amount = " + str(amount))
    #print("price = " + str(1/pow((2*y_reserves+x_reserves)/x_reserves,t)))
    #print("apy = " + str((2*y_reserves+x_reserves)/x_reserves -1 ))
    # buy fyt or base
    if np.random.uniform(0,1) < 0.5:
        token_in = "base"
        token_out = "fyt"
    else:
        token_in = "fyt"
        token_out = "base"
        
    if np.random.uniform(0,1) < 0.5:
        direction="in"
    else:
        direction="out"
        
    trade_input = {
        "time": float("{:.18f}".format(m.t)),
        "x_reserves": float("{:.18f}".format(m.x)),
        "y_reserves": float("{:.18f}".format(m.y)),
        "total_supply": float("{:.18f}".format(m.total_supply)),
        "token_in": token_in,
        "amount_in": float("{:.18f}".format(amount)),
        "token_out": token_out,
        "direction": direction
    }
    (without_fee_or_slippage,with_fee,without_fee,fee) = m.swap(amount,direction,token_in,token_out)
    trade_output = {
        "x_reserves": float("{:.18f}".format(m.x)),
        "y_reserves": float("{:.18f}".format(m.y)),
        "amount_out": float("{:.18f}".format(with_fee)),
        "fee": float("{:.18f}".format(fee)),
    }
    trades.append({
        "input": trade_input,
        "output": trade_output
    });


run={
    "init":init,
    "trades":trades
}


with open('testTrades.json', 'w') as fp:
    json.dump(run, fp, indent=1)
    
#builder = SchemaBuilder()
#builder.add_object(run)
#run_schema=builder.to_schema()

#with open('test_vectors_schema.json', 'w') as fp:
#    json.dump(run_schema, fp, indent=1)

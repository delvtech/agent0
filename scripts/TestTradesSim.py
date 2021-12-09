import numpy as np
import json
import math
#from genson import SchemaBuilder
from PricingModels import *


def truncate(number, digits):
    stepper = 10.0 ** digits
    return math.trunc(stepper * number) / stepper

runs={}
np.random.seed(1)

step_size=.001
t_max=1
t_min=0+step_size
num_steps=int(t_max/step_size)
times = np.arange(t_min, t_max+step_size, step_size) 
np.random.shuffle(times)
min_target_liquidity = 100000
max_target_liquidity = 10000000
base_asset_price = 55000
max_apy = 50
min_apy = .5
BASE_DECIMALS = 8
BOND_DECIMALS = 18
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
    "base_decimals": float("{:.18f}".format(BASE_DECIMALS)),
    "max_apy": float("{:.18f}".format(max_apy)),
}
for t in times:
    # determine APY
    apy = np.random.uniform(min_apy,max_apy)
    # determine target liquidity
    target_liquidity = np.random.uniform(min_target_liquidity,max_target_liquidity)
    # determine t_stretch
    t_stretch = Element_Pricing_Model.calc_time_stretch(apy)
    # calculate days_until_maturity from t
    days_until_maturity = t * 365
    # calculate liquidity
    (x_reserves, y_reserves, liquidity) = Element_Pricing_Model.calc_liquidity2(target_liquidity,base_asset_price,apy,days_until_maturity,t_stretch)
    total_supply = x_reserves+y_reserves
    spot_price = Element_Pricing_Model.calc_spot_price(x_reserves,y_reserves,total_supply,t/t_stretch)
    resulting_apy = Element_Pricing_Model.apy(spot_price,days_until_maturity)
    # determine order size (bounded)
    amount = np.random.uniform(0,(liquidity/base_asset_price)/5)


    token_in = "base"
    token_out = "fyt"
    direction="out"
        
    
    m = Market(x_reserves,y_reserves,g,t/t_stretch,total_supply,Element_Pricing_Model)
    print("time = " + str(m.t) + " t_stretch = " + str(t_stretch) +  " apy = " + str(resulting_apy) + " x = " + str(x_reserves) + " y = " + str(y_reserves) + " amount = " + str(amount))
        
    display_x = truncate(m.x,BASE_DECIMALS)
    display_y =  truncate(m.y,BOND_DECIMALS)
    display_amount = 0
    display_with_fee = 0
    if token_in == "base":
        display_amount = truncate(amount,BASE_DECIMALS)
    else:
        display_amount = truncate(amount,BOND_DECIMALS)
        
    trade_input = {
        "time": float("{:.18f}".format(m.t)),
        "x_reserves": float("{:.18f}".format(display_x)),
        "y_reserves": float("{:.18f}".format(display_y)),
        "total_supply": float("{:.18f}".format(m.total_supply)),
        "token_in": token_in,
        "amount_in": float("{:.18f}".format(display_amount)),
        "token_out": token_out,
        "direction": direction
    }
    (without_fee_or_slippage,with_fee,without_fee,fee) = m.swap(amount,direction,token_in,token_out)
    display_x = truncate(m.x,BASE_DECIMALS)
    display_y =  truncate(m.y,BOND_DECIMALS)
    if token_in == "base":
        display_with_fee = truncate(with_fee,BOND_DECIMALS)
    else:
        display_with_fee = truncate(with_fee,BASE_DECIMALS)
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

import numpy as np
import json
import math
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
DECIMALS = 8
min_g = 0
max_g = 0.5
min_vault_age = 0
max_vault_age = 2
min_vault_apy = 0
max_vault_apy = 10
min_pool_age = 0
max_pool_age = 0.5

pricingModel = YieldsSpacev2_Pricing_model # pick from [Element_Pricing_Model,YieldsSpacev2_Pricing_model]

x_orders=0
x_volume=0
y_orders=0
y_volume=0
trades = []
init = {
    "min_fee": float("{:.18f}".format(min_g)),
    "max_fee": float("{:.18f}".format(max_g)),
    "t_max": float("{:.18f}".format(t_max)),
    "t_min": float("{:.18f}".format(t_min)),
    "num_tests": float("{:.18f}".format(len(times))),
    "decimals": float("{:.18f}".format(DECIMALS)),
    "max_apy": float("{:.18f}".format(max_apy)),
    "min_vault_age": float("{:.18f}".format(min_vault_age)),
    "max_vault_age": float("{:.18f}".format(max_vault_age)),
    "min_vault_apy": float("{:.18f}".format(min_vault_apy)),
    "max_vault_apy": float("{:.18f}".format(max_vault_apy)),
    "min_pool_age": float("{:.18f}".format(min_pool_age)),
    "max_pool_age": float("{:.18f}".format(max_pool_age)),
}
for t in times:
    # determine APY
    apy = np.random.uniform(min_apy,max_apy)
    # determine fee percent
    g = np.random.uniform(min_g,max_g)
    # determine real-world parameters for estimating u and c (vault and pool details)
    vault_age = np.random.uniform(min_vault_age,max_vault_age) # in years
    vault_apy = np.random.uniform(min_vault_apy,max_vault_apy) # in %
    pool_age = np.random.uniform(min(vault_age,min_pool_age),max_pool_age) # in years
    # determine u and c
    c = (1 + vault_apy/100)**vault_age
    c = truncate(c,DECIMALS)
    u = (1 + vault_apy/100)**pool_age
    u = truncate(u,DECIMALS)
    # determine target liquidity
    target_liquidity = np.random.uniform(min_target_liquidity,max_target_liquidity)
    # determine t_stretch
    t_stretch = pricingModel.calc_time_stretch(apy)
    # calculate days_until_maturity from t
    days_until_maturity = t * 365
    # calculate liquidity
    (x_reserves, y_reserves, liquidity) = pricingModel.calc_liquidity(target_liquidity,base_asset_price,apy,days_until_maturity,t_stretch,c,u)
    total_supply = x_reserves+y_reserves
    spot_price = pricingModel.calc_spot_price(x_reserves,y_reserves,total_supply,t/t_stretch,c,u)
    resulting_apy = pricingModel.apy(spot_price,days_until_maturity)
    # determine order size (bounded)
    amount = np.random.uniform(0,(liquidity/base_asset_price)/5)


    token_in = "base"
    token_out = "fyt"
    direction="out"
        
    
    m = Market(x_reserves,y_reserves,g,t/t_stretch,total_supply,pricingModel,c,u)
    print("time = " + str(m.t) + " t_stretch = " + str(t_stretch) +  " apy = " + str(resulting_apy)\
         + " x = " + str(x_reserves) + " y = " + str(y_reserves) + " amount = " + str(amount)\
         + " g = " + str(g) + " c = " + str(c) + " u = " + str(u) + " c/u = " + str(c/u) + " decimals = " + str(DECIMALS))
        
    display_x = truncate(m.x,DECIMALS)
    display_y =  truncate(m.y,DECIMALS)
    display_amount = 0
    display_with_fee = 0

    display_amount = truncate(amount,DECIMALS)
        
    trade_input = {
        "time": float("{:.18f}".format(m.t)),
        "x_reserves": float("{:.18f}".format(display_x)),
        "y_reserves": float("{:.18f}".format(display_y)),
        "total_supply": float("{:.18f}".format(m.total_supply)),
        "token_in": token_in,
        "amount_in": float("{:.18f}".format(display_amount)),
        "token_out": token_out,
        "direction": direction,
        "g": g,
        "c": c,
        "u": u
    }
    (without_fee_or_slippage,with_fee,without_fee,fee) = m.swap(amount,direction,token_in,token_out)
    display_x = truncate(m.x,DECIMALS)
    display_y =  truncate(m.y,DECIMALS)
    display_without_fee = truncate(without_fee,DECIMALS)
    trade_output = {
        "x_reserves": float("{:.18f}".format(m.x)),
        "y_reserves": float("{:.18f}".format(m.y)),
        "amount_out": float("{:.18f}".format(display_without_fee)),
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

with open('testTradesV2.json', 'w') as fp:
    json.dump(run, fp, indent=1)

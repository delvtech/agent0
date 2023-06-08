# %%
%load_ext autoreload
%autoreload 2

# %% [markdown]
# 

# %%
from __future__ import annotations  # types are strings by default in 3.11

from dataclasses import dataclass

import numpy as np
import pandas as pd

# %%

def calc_bond_reserves(apr,share_reserves,days_until_maturity,time_stretch):
    t=days_until_maturity/(365*time_stretch)
    T=days_until_maturity/365
    return share_reserves * (T*apr/100 + 1)**(1/t)

def calc_spot_price_from_reserves(share_reserves,bond_reserves,days_until_maturity,time_stretch):
    t=days_until_maturity/(365*time_stretch)
    return (bond_reserves/share_reserves)**(-t)

def calc_apr_from_reserves(share_reserves,bond_reserves,days_until_maturity,time_stretch):
    T=days_until_maturity/365
    p=calc_spot_price_from_reserves(share_reserves,bond_reserves,days_until_maturity,time_stretch)
    return 100*T*(1-p)/p

# %%
apr_list = []
time_stretch_apr_list = []
share_reserves_list = []
bond_reserves_list = []
calculated_apr_list = []
time_stretch_list = []

for apr in np.arange(1, 51, 1):
    for time_stretch in np.arange(1, 120, .1):
        apr_list.append(apr)
        # Set up the market
        time_stretch_list.append(time_stretch)
        share_reserves = 1
        share_reserves_list.append(share_reserves)
        # this method needs to implement the calc_bond_reserves method from SC
        bond_reserves = calc_bond_reserves(apr, share_reserves, 365,time_stretch)
        calculated_apr = calc_apr_from_reserves(share_reserves, bond_reserves, 365, time_stretch)
        bond_reserves_list.append(bond_reserves)
        calculated_apr_list.append(calculated_apr)
        


df = pd.DataFrame(list(zip(apr_list, time_stretch_list, share_reserves_list, 
                           bond_reserves_list, calculated_apr_list)),
               columns =['apr','time_stretch','share_reserves','bond_reserves','calculated_apr'])

# %%
df['reserve_ratio']=df['share_reserves']/df['bond_reserves']

## This is the magic filter. We are essentially only looking for time stretches that result in 
## the bond reserves being between ~ 3x larger than base reserves.  Using this as a schelling point
## for the ratio bc this is very similar to when we used y + total supply where total supply = x+y
reserve_ratio_filter=(df['reserve_ratio'].astype(float)>=.30)&(df['reserve_ratio'].astype(float)<=.36)
df_filtered = df[reserve_ratio_filter].reset_index()

apr_t_stretches=[]
for APR in np.arange(1, 51, 1):
    min_ts=df_filtered[df_filtered['apr'].astype(float)==APR]['time_stretch'].min()
    max_ts=df_filtered[df_filtered['apr'].astype(float)==APR]['time_stretch'].max()
    apr_t_stretches.append((APR,min_ts,max_ts))

#pd.set_option("display.max_rows", None)
df_filtered


# %%
import pandas as pd
import matplotlib.pyplot as plt

#pd.reset_option('display.max_rows')
plt.subplots(figsize=(12,12))
aprs = [apr for apr,min_ts,max_ts in apr_t_stretches]
mean_tss= [(min_ts+max_ts)/2 for apr,min_ts,max_ts in apr_t_stretches]
err_tss= [max_ts-(min_ts+max_ts)/2 for apr,min_ts,max_ts in apr_t_stretches]
plt.yticks(np.arange(0,120, 1))
plt.xticks(np.arange(0,51, 1))
plt.errorbar(aprs, mean_tss, yerr=err_tss, fmt='o', color='black',
             ecolor='red', elinewidth=3, capsize=0);
plt.scatter(aprs,mean_tss,color='black')
plt.grid(True)
plt.title('Suggested Time Stretch vs Market Rate', fontsize=14)
plt.xlabel('Market Rate', fontsize=14)
plt.ylabel('Time Stretch', fontsize=14)
# %%

from scipy.optimize import curve_fit

def objective(x,a,b):
    return a/(b*x)

x = aprs
y = mean_tss
# curve fit
popt, _ = curve_fit(objective, x, y)
# summarize the parameter values
a, b = popt
print('y = %.5f /( %.5f * x)' % (a, b))
# %%

import pandas as pd
import matplotlib.pyplot as plt

plt.subplots(figsize=(12,12))
plt.yticks(np.arange(0,120, 1))
plt.xticks(np.arange(0,51, 1))
plt.scatter(aprs,mean_tss,color='black')
plt.grid(True)
plt.title('Suggested Time Stretch vs Market Rate', fontsize=14)
plt.xlabel('Market Rate', fontsize=14)
plt.ylabel('Time Stretch', fontsize=14)

x = np.arange(1,51,1)
y = 5.24592 /( 0.04665 * x)
plt.plot(x, y, '--', color="green")
# %%
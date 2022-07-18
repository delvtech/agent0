# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.8
#   kernelspec:
#     display_name: Python 3.10.2 64-bit
#     language: python
#     name: python3
# ---

# %%
import numpy as np
import time, os, numbers
import pandas as pd
import matplotlib.pyplot as plt
import sys  
sys.path.insert(0, './scripts')
from PricingModels import Element_Pricing_Model, Market, YieldsSpacev2_Pricing_model


trades = []
run_matrix=[]
run_data=[]

ybas = [
    {
        "vault" : "ySTETH",
        "apy" : 10,
        "market_price" : 2500,
        "days_until_maturity": 90,
        "vault_age": 1,
        "vault_apr_mean": -2,
        "vault_apr_stdev": 0.25,
    },
]

run_id=0
startTime = time.time() # time function
for target_daily_volume in [5000000,10000000]:
# for target_daily_volume in [5000000]:
    for target_liquidity in [10000000]:
        for g in [.2]:
                for yba in ybas:
                    run_id=run_id+1
                    #choose your fighter
                    PricingModel = Element_Pricing_Model
                    PricingModel = YieldsSpacev2_Pricing_model
                    PricingModelList = [Element_Pricing_Model,YieldsSpacev2_Pricing_model]
                    # PricingModelList = [YieldsSpacev2_Pricing_model,Element_Pricing_Model]

                    for PricingModel in PricingModelList:
                        np.random.seed(2) #guarantees randomness behaves deterministically from here on out
                        
                        model_name = PricingModel.model_name()
                        APY=yba["apy"]
                        days_until_maturity = yba["days_until_maturity"]
                        market_price = yba["market_price"]
                        time_stretch = PricingModel.calc_time_stretch(APY)
                        run_matrix.append((model_name,yba,g,target_liquidity,target_daily_volume))

                        y_start = target_liquidity/market_price
                        max_order_price=12500
                        max_order_size=max_order_price/market_price
                        sigma=max_order_size/10
                        liquidity = 0

                        vault_age = yba["vault_age"]
                        vault_apr = yba["vault_apr_mean"]
                        u = (1 + vault_apr/100)**(vault_age)
                        c = u
                        
                        (x_start, y_start, liquidity) = PricingModel.calc_liquidity(target_liquidity, market_price, APY, days_until_maturity, time_stretch, c, u)
                        
                        total_supply = x_start+y_start
                        t = days_until_maturity/(365*time_stretch)
                    
                        step_size=t/days_until_maturity
                        epsilon=step_size/2
                        m = Market(x_start,y_start,g,t,total_supply,PricingModel,c,u)
                        run_cols = ['Run_ID',"Model Name","Days Until Maturity","Time Stretch","Fee (%)","Max order size"\
                            ,"Starting APY","Starting Spot Price","Starting Liquidity","Starting Base Reserves"
                            ,"Starting Share Reserves (z)", "Starting PT Reserves"]
                        this_run = [run_id,model_name,days_until_maturity,time_stretch,g*100,max_order_size,m.apy(days_until_maturity)\
                            ,m.spot_price(),liquidity,m.x,m.x/m.c,m.y]
                        [x_orders,x_volume,x_orders,y_volume,total_fees,todays_volume,todays_fees,todays_num_trades,day]=[0,0,0,0,0,0,0,0,0]
                        while m.t > epsilon:
                            day += 1
                            todays_volume = 0
                            todays_fees = 0
                            todays_num_trades = 0

                            vault_age = yba["vault_age"]+day/365
                            vault_apr = vault_apr + np.random.normal(0,yba['vault_apr_stdev'])
                            m.c = m.c*(1 + vault_apr/100/365)

                            maturity_ratio = day/days_until_maturity
                            ub=target_daily_volume#*math.log10(1/maturity_ratio) # log(1/maturity ratio) is used to simulate waning demand over the lifetime of the fyt
                            # todays_target_volume = np.random.uniform(ub/2,ub)
                            todays_target_volume = np.random.normal(ub/2,ub/10)
                            while todays_target_volume > todays_volume:
                                fee = -1
                                trade = []
                                while fee < 0:
                                    # determine order size
                                    amount = np.random.normal(max_order_size/2,sigma)
                                    # if model_name=="YieldsSpacev2":
                                    #     amount = amount + np.random.normal(1,0) # HACK TO ADD NOISE TO YIELDSPACEV2
                                    lb_amount = max(0.00001,amount)
                                    amount = min(max_order_size,lb_amount)

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

                                    [start_x_volume,start_y_volume,num_orders] = [m.x_volume,m.y_volume,m.x_orders + m.y_orders]
                                    (without_fee_or_slippage,with_fee,without_fee,fee) = m.swap(amount,direction,token_in,token_out)
                                    
                                    cols = ['Run_ID',"model_name","init.apy","init.percent_fee","init.days_until_maturity","init.max_order_size","init.time_stretch"\
                                        ,"init.market_price","init.target_liquidity","init.target_daily_volume","input.day","input.time"\
                                        ,"init.vault_age","init.vault_apr_mean","init.vault_apr_stdev"\
                                        ,"input.base_market_price","input.unit_fyt_price","input.apy","input.base_reserves","input.fyt_reserves","input.trade_number"\
                                        ,"input.token_in","input.amount_specified","input.token_out","input.direction"\
                                        ,"input.vault_age","input.vault_apr","input.c","input.u"\
                                        ,"output.trade_volume","output.fee","output.slippage"]
                                    trade = [run_id,model_name,APY,g,days_until_maturity,max_order_size,time_stretch\
                                        ,market_price,target_liquidity,target_daily_volume,day,m.t\
                                        ,yba["vault_age"],yba["vault_apr_mean"],yba["vault_apr_stdev"]\
                                        ,market_price,m.spot_price(),m.apy(days_until_maturity),m.x,m.y,m.x_orders+m.y_orders\
                                        ,token_in,amount,token_out,direction\
                                        ,vault_age,vault_apr,m.c,m.u\
                                        ,with_fee*market_price,fee*market_price,(without_fee_or_slippage-without_fee)*market_price]
                                    
                                trades.append(trade)
                                todays_volume += (m.x_volume - start_x_volume)*market_price + (m.y_volume - start_y_volume)*market_price
                                todays_fees += fee*market_price
                                todays_num_trades += 1
                            # print("\tDay: " + str(day) + " PT Price: " + str(m.spot_price()) + " Implied APY: " + str(m.apy(days_until_maturity-day+1)) + " Target Volume Factor: {:,.4f}".format(math.log10(1/maturity_ratio)) \
                            #     + " Volume: ${:,.2f}".format(todays_volume) + " Num Trades: " + str(todays_num_trades) + " Fees: ${:,.2f}".format(todays_fees)\
                            #     + " x_reserves: {:,.2f}".format(m.x) + " y_reserves: {:,.2f}".format(m.y)\
                            #     )
                            total_fees += todays_fees
                            m.tick(step_size)

                        run_cols = run_cols + ['Ending Liquidity','Total volume','Total fees'\
                            ,'Fees / Volume (bps)','Ending Base Reserves','Delta Base Reserves','Ending Bond Reserves','Delta Bond Reserves'\
                            ,'Num base orders','Cum base volume','Num PT orders','Cum PT volume','Cum slippage Base'\
                            ,'Cum slippage PT','Cum fees Base','Cum fees PT','Ending PT Price','Ending Time']
                        this_run = this_run + [m.x*market_price+m.y*market_price*m.spot_price(),m.x_volume*market_price+m.y_volume*market_price\
                            ,total_fees,total_fees/(m.x_volume*market_price+m.y_volume*market_price)*1e4,m.x,abs(x_start-m.x),m.y,abs(y_start-m.y)\
                            ,m.x_orders,m.x_volume,m.y_orders,m.y_volume,m.cum_x_slippage,m.cum_y_slippage\
                            ,m.cum_x_fees,m.cum_y_fees,m.spot_price(),m.t]
                        run_data.append(this_run)
endTime = time.time()
print('finished {} runs in {} seconds'.format(len(run_data),endTime-startTime))

#df = pd.DataFrame.from_dict(json_normalize(trades), orient='columns')
df = pd.DataFrame(trades,columns=cols)
df_runs = pd.DataFrame(run_data,columns=run_cols).set_index('Run_ID',drop=True)
display(df_runs.T)

# %%
dfs=[]
oldIndex = []
df['total_liquidity']=df.loc[:,'input.base_reserves']*df.loc[:,'input.base_market_price']+df.loc[:,'input.fyt_reserves']*df.loc[:,'input.base_market_price']*df.loc[:,'input.unit_fyt_price']
for (model_name,yba,g,target_liquidity,target_daily_volume) in run_matrix:
  newIndex = (df['init.market_price']==yba["market_price"]) & (df['init.apy']==yba["apy"]) & (df['init.percent_fee']==g) & (df['init.days_until_maturity']==yba["days_until_maturity"]) & (df['init.target_liquidity']==target_liquidity) & (df['init.target_daily_volume']==target_daily_volume)
  if len(oldIndex)==0 or not all(newIndex==oldIndex):
    dfs.append(df[ newIndex ].reset_index(drop=True))
    oldIndex = newIndex

numPlots = 5
for idx,_df in enumerate(dfs):
  fig, ax = plt.subplots(ncols=1, nrows=numPlots,gridspec_kw = {'wspace':0, 'hspace':0, 'height_ratios':np.ones(numPlots)})
  fig.patch.set_facecolor('white')   # set fig background color to white
  df_fees_volume = _df.groupby(['input.day','model_name']).agg({'output.trade_volume':['sum']\
                                  ,'output.fee':['mean','std','min','max','sum']\
                                })
  df_fees_by_trade_type = _df.groupby(['model_name','input.direction','input.token_in']).agg({'output.trade_volume':['sum']\
                                  ,'output.slippage':['mean','std','min','max','sum']\
                                  ,'output.fee':['mean','std','min','max','sum']\
                                })
  display(df_fees_by_trade_type)
                            
  df_fees_volume.columns = ['_'.join(col).strip() for col in df_fees_volume.columns.values]
  df_fees_volume = df_fees_volume.reset_index()

  for model in df_fees_volume.model_name.unique():
    ax[0] = df_fees_volume.loc[df_fees_volume.model_name==model,:].plot(x="input.day", y="output.fee_sum",figsize=(24,18),ax=ax[0],label=model)
  ax[0].set_xlabel("")
  ax[0].set_ylabel("Fees (US Dollars)",fontsize=18)
  ax[0].tick_params(axis = "both", labelsize=18)
  ax[0].grid(visible=True,linestyle='--', linewidth='1', color='grey',which='both',axis='y')
  ax[0].xaxis.set_ticklabels([])
  title = "Fees Collected Per Day Until Maturity\nAPY: {:.2f}%, Time Stretch: {:.2f}, Maturity: {:} days\n\
          Target Liquidity: {:.2f}, Target Daily Volume: {:.2f}, Percent Fees: {:.2f}%"\
    .format(_df['init.apy'][0],_df['init.time_stretch'][0],_df['init.days_until_maturity'][0]\
      ,_df["init.target_daily_volume"][0],_df["init.target_liquidity"][0],_df["init.percent_fee"][0])
  ax[0].set_title(title,fontsize=20)
  ax[0].legend(fontsize=18)

  currentPlot = 1
  df_to_display = pd.DataFrame()
  for model in df_fees_volume.model_name.unique():
    ax[currentPlot] = _df.loc[_df.model_name==model,:]\
      .plot(x="input.trade_number",y="input.apy",figsize=(24,18),ax=ax[currentPlot],label=model)
    df_to_display = pd.concat([df_to_display,_df.loc[_df.model_name==model,:].head(1)])
  df_to_display=df_to_display.set_index('model_name',drop=True)
  df_to_display.loc['diff']=[df_to_display.iloc[1,i]-df_to_display.iloc[0,i] if isinstance(df_to_display.iloc[0,i],numbers.Number) else df_to_display.iloc[0,i] for i in range(0,df_to_display.shape[1])]
  df_to_display.loc['ratio']=[df_to_display.iloc[1,i]/df_to_display.iloc[0,i] if isinstance(df_to_display.iloc[0,i],numbers.Number) else df_to_display.iloc[0,i] for i in range(0,df_to_display.shape[1])]
  display(df_to_display.loc[:,(df_to_display.iloc[0,:].values!=df_to_display.iloc[1,:].values) | (df_to_display.columns.isin(['input.c','input.u']))].T)

  ax[currentPlot] = _df.loc[_df.model_name==model,:].plot(x="input.trade_number",y="input.vault_apr",figsize=(24,18),ax=ax[currentPlot],label='vault_apr')
  ax[currentPlot].set_xlabel("")
  ax[currentPlot].set_ylabel("APY",fontsize=18)
  ax[currentPlot].tick_params(axis = "both", labelsize=18)
  ax[currentPlot].grid(visible=True,linestyle='--', linewidth='1', color='grey',which='both',axis='y')
  ax[currentPlot].xaxis.set_ticklabels([])
  ax[currentPlot].legend(fontsize=18)

  currentPlot = 2
  ax[currentPlot] = _df.loc[_df.model_name==model,:].plot(x="input.trade_number",y="input.c",figsize=(24,18),ax=ax[currentPlot],label='c')
  ax[currentPlot] = _df.loc[_df.model_name==model,:].plot(x="input.trade_number",y="input.u",figsize=(24,18),ax=ax[currentPlot],label='u')
  ax[currentPlot].set_ylabel("Price Per Share",fontsize=18)
  ax[currentPlot].tick_params(axis = "both", labelsize=18)
  ax[currentPlot].grid(visible=True,linestyle='--', linewidth='1', color='grey',which='both',axis='y')
  ax[currentPlot].xaxis.set_ticklabels([])

  currentPlot = 3
  for model in df_fees_volume.model_name.unique():
    ax[currentPlot] = df_fees_volume.loc[df_fees_volume.model_name==model,:]\
      .plot(kind='line',x="input.day", y="output.trade_volume_sum",ax=ax[currentPlot],label=model)
  ax[currentPlot].set_xlabel("Day",fontsize=18)
  ax[currentPlot].set_ylabel("Volume (US Dollars)",fontsize=18)
  ax[currentPlot].tick_params(axis = "both", labelsize=12)
  ax[currentPlot].grid(visible=True,linestyle='--', linewidth='1', color='grey',which='both',axis='y')
  ax[currentPlot].legend(fontsize=18)
  ax[currentPlot].ticklabel_format(style='plain',axis='y')
  fig.subplots_adjust(wspace=None, hspace=None)

  currentPlot = 4
  for model in df_fees_volume.model_name.unique():
    ax[currentPlot] = _df.loc[_df.model_name==model,:]\
      .plot(kind='line',x="input.day", y=["input.base_reserves","input.fyt_reserves"],ax=ax[currentPlot],label=[model+'x',model+'y']) # .plot(kind='line',x="input.day", y="total_liquidity",ax=ax[currentPlot],label=model)
  # ax[currentPlot-2].plot(ax[currentPlot-2].lines[0].get_xdata()\
  #   ,ax[currentPlot].lines[0].get_ydata()/ax[currentPlot].lines[1].get_ydata()*ax[currentPlot-2].lines[0].get_ydata()[0]\
  #     ,label='liquidityDiff')
  ax[currentPlot-2].legend(fontsize=18)
  ax[currentPlot].set_xlabel("Day",fontsize=18)
  ax[currentPlot].set_ylabel("Liquidity (US Dollars)",fontsize=18)
  ax[currentPlot].tick_params(axis = "both", labelsize=12)
  ax[currentPlot].grid(visible=True,linestyle='--', linewidth='1', color='grey',which='both',axis='y')
  ax[currentPlot].legend(fontsize=18)
  ax[currentPlot].ticklabel_format(style='plain',axis='y')
  fig.subplots_adjust(wspace=None, hspace=None)

  plt.show()
  os.makedirs("figures", exist_ok=True)
  fig.savefig("figures/chart{}.png".format(idx+1),bbox_inches='tight')

# %%
hist=df['output.trade_volume'].plot.hist(bins=50,title="Order Size Distribution",figsize=(10,10),edgecolor='black').set_xlabel("Typical Order Amount (in USD)")

# %%
df_fees_volume

# %%
pd.options.display.float_format = '{:,.8f}'.format
df_fees_agg = df.groupby(['Run_ID','model_name','init.apy','init.percent_fee','init.time_stretch','init.market_price','init.target_liquidity','init.days_until_maturity','init.target_daily_volume'])\
    ['init.apy','init.percent_fee','init.time_stretch','init.market_price','init.target_liquidity','init.days_until_maturity','init.target_daily_volume','input.amount_specified','output.fee','output.slippage','output.trade_volume']\
        .agg({'output.fee':['count','sum'],'output.trade_volume':['sum'],'output.slippage':['mean'],'input.amount_specified':['mean']})
df_fees_agg.columns = ['_'.join(col).strip() for col in df_fees_agg.columns.values]
df_fees_agg = df_fees_agg.reset_index()
df_fees_agg['init.percent_fee'] = df_fees_agg['init.percent_fee'].round(2)
df_fees_agg['output.mean_daily_volume'] = df_fees_agg['output.trade_volume_sum']/df_fees_agg['init.days_until_maturity']
df_fees_agg['output.apr'] = (df_fees_agg['output.fee_sum']/df_fees_agg['init.target_liquidity']) * (365/df_fees_agg['init.days_until_maturity'])*100
df_fees_agg = df_fees_agg.set_index('Run_ID',drop=True)
display(df_fees_agg.T)

# %%
#df_fees_agg.to_csv("fees.csv")
#print(df_fees_agg[['init.target_liquidity','init.target_daily_volume','output.fee_sum','output.trade_volume_sum','output.mean_daily_volume','output.apr']].to_markdown(index=False))

print(df_fees_agg[['model_name','init.target_liquidity','output.trade_volume_sum','output.mean_daily_volume','output.apr']].to_markdown(index=True,floatfmt=(",.0f", ",.0f",",.0f",",.2f")))

# %%
ax = plt.figure(figsize=(10, 8))
data_to_plot=pd.DataFrame()
for (model_name,yba,g,target_liquidity,target_daily_volume) in run_matrix:
  condition =   (df_fees_agg['init.target_liquidity']==target_liquidity) & (df_fees_agg['init.target_daily_volume']==target_daily_volume) & (df_fees_agg['model_name']==model_name)
  data_to_plot = pd.concat([data_to_plot,df_fees_agg[condition][['model_name','init.apy','output.fee_sum','init.time_stretch']]])
display(data_to_plot)
barWidth = 0.4
for idx,model in enumerate(data_to_plot.model_name.unique()):
  bars=plt.bar(data_to_plot.index[(data_to_plot.model_name==model)]-barWidth/2+barWidth*idx,data_to_plot.loc[(data_to_plot.model_name==model),'output.fee_sum'],label=model,width=barWidth,edgecolor='black')
  plt.gca().bar_label(bars,fmt='%s',labels=['{:,.0f}'.format(i) for i in data_to_plot.loc[(data_to_plot.model_name==model),'output.fee_sum']])
plt.ticklabel_format(style='plain',axis='y')
plt.ylabel("Fees in US Dollars", size=14)
plt.legend(fontsize=18)
plt.xticks(range(0,max(data_to_plot.index)+1),size=14)
plt.xlabel("Run", size=14)
plt.title('Total Fees')
plt.show()


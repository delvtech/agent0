
class Element_Pricing_Model:
    @staticmethod
    def model_name():
        return "Element_Pricing_Model"

    @staticmethod
    def calc_max_trade(in_reserves,out_reserves,t):
        k=pow(in_reserves,1-t) + pow(out_reserves,1-t)
        return k**(1/(1-t))-in_reserves
    
    @staticmethod
    def calc_x_reserves(APY,y_reserves,days_until_maturity,time_stretch):
        t=days_until_maturity/(365*time_stretch)
        T=days_until_maturity/365
        return y_reserves*(-(2/((1-T*APY/100)**(1/t)-1))-2)
    
    @staticmethod    
    def calc_liquidity(target_liquidity, market_price, apy, days_until_maturity, time_stretch,c=1,u=1):
      spot_price=Element_Pricing_Model.calc_spot_price_from_apy(apy,days_until_maturity)
      t=days_until_maturity/(365*time_stretch)
      y_reserves = target_liquidity/market_price/2/(1-apy/100*t)
      x_reserves = Element_Pricing_Model.calc_x_reserves(apy,y_reserves,days_until_maturity,time_stretch)
      scaleUpFactor = target_liquidity/(x_reserves*market_price+y_reserves*market_price*spot_price)
      y_reserves = y_reserves * scaleUpFactor
      x_reserves = x_reserves * scaleUpFactor
      liquidity = x_reserves*market_price+y_reserves*market_price*spot_price
      return (x_reserves,y_reserves,liquidity)
    
    @staticmethod
    def calc_time_stretch(apy):
        return 3.09396 /( 0.02789 * apy)

    @staticmethod
    def calc_apy_from_reserves(x_reserves,y_reserves,total_supply,t,t_stretch):
      spot_price = Element_Pricing_Model.calc_spot_price(x_reserves,y_reserves,total_supply,t)
      days_until_maturity = t * 365 * t_stretch
      return Element_Pricing_Model.apy(spot_price,days_until_maturity)
    
    @staticmethod
    def apy(price,days_until_maturity):
      T=days_until_maturity/365
      return (1-price)/T * 100
    
    @staticmethod
    def calc_spot_price_from_apy(apy,days_until_maturity):
      T=days_until_maturity/365
      return 1- apy*T/100
    
    @staticmethod
    def calc_spot_price(x_reserves,y_reserves,total_supply,t,c=1,u=1):
        return 1/pow((y_reserves+total_supply)/x_reserves,t)
    
    @staticmethod
    def calc_in_given_out(out,in_reserves,out_reserves,token_in,g,t,c,u):
        k=pow(in_reserves,1-t) + pow(out_reserves,1-t)
        without_fee = pow(k-pow(out_reserves-out,1-t),1/(1-t)) - in_reserves
        if token_in == "base":
            fee =  (out-without_fee)*g
            with_fee = without_fee+fee
        elif token_in == "fyt":
            fee =  (without_fee-out)*g
            with_fee = without_fee+fee
        without_fee_or_slippage = pow(in_reserves/out_reserves,t)*out
        return (without_fee_or_slippage,with_fee,without_fee,fee)
    
    @staticmethod
    def calc_out_given_in(in_,in_reserves,out_reserves,token_out,g,t,c,u):
        k=pow(in_reserves,1-t) + pow(out_reserves,1-t)
        without_fee = out_reserves - pow(k-pow(in_reserves+in_,1-t),1/(1-t))
        if token_out == "base":
            fee =  (in_-without_fee)*g
            with_fee = without_fee-fee
        elif token_out == "fyt":
            fee =  (without_fee-in_)*g
            with_fee = without_fee-fee
        without_fee_or_slippage = 1/pow(in_reserves/out_reserves,t)*in_
        return (without_fee_or_slippage,with_fee,without_fee,fee)
    
    @staticmethod
    def calc_tokens_in_given_lp_out(lp_out, x_reserves, y_reserves, total_supply):
        # Check if the pool is initialized
        if total_supply == 0:
            x_needed = lp_out
            y_needed = 0
        else:
            # solve for y_needed: lp_out = ((x_reserves / y_reserves) * y_needed * total_supply)/x_reserves
            y_needed = (lp_out * x_reserves)/((x_reserves / y_reserves) * total_supply)
            # solve for x_needed: x_reserves/y_reserves = x_needed/y_needed
            x_needed = (x_reserves/y_reserves)*y_needed
        return (x_needed, y_needed)

    @staticmethod
    def calc_lp_out_given_tokens_in(x_in, y_in, x_reserves, y_reserves, total_supply):
        # Check if the pool is initialized
        if total_supply == 0:
            # When uninitialized we mint exactly the underlying input in LP tokens
            lp_out = x_in
            x_needed = x_in
            y_needed = 0
        else:
            # calc the number of x needed for the y_in provided
            x_needed = (x_reserves / y_reserves) * y_in
            # if there isn't enough x_in provided
            if x_needed > x_in:
                lp_out = (x_in * total_supply)/x_reserves
                # use all the x_in
                x_needed = x_in
                # solve for: x_reserves/y_reserves = x_needed/y_needed
                y_needed = x_needed/(x_reserves/y_reserves)
            else:
                # We calculate the percent increase in the reserves from contributing all of the bond
                lp_out = (x_needed * total_supply)/x_reserves
                y_needed = y_in
        return (x_needed, y_needed, lp_out)
   
    @staticmethod
    def calc_lp_in_given_tokens_out(min_x_out, min_y_out, x_reserves, y_reserves, total_supply):
        # calc the number of x needed for the y_out provided
        x_needed = (x_reserves / y_reserves) * min_y_out
        # if there isn't enough x_out provided
        if min_x_out > x_needed:
            lp_in = (min_x_out * total_supply)/x_reserves
            # use all the x_out
            x_needed = min_x_out
            # solve for: x_reserves/y_reserves = x_needed/y_needed
            y_needed = x_needed/(x_reserves/y_reserves)
        else:
            y_needed = min_y_out
            lp_in = (y_needed * total_supply)/y_reserves
        return (x_needed,y_needed,lp_in)

    @staticmethod
    def calc_tokens_out_for_lp_in(lp_in, x_reserves, y_reserves, total_supply):
        # solve for y_needed: lp_out = ((x_reserves / y_reserves) * y_needed * total_supply)/x_reserves
        y_needed = (lp_in * x_reserves)/((x_reserves / y_reserves) * total_supply)
        # solve for x_needed: x_reserves/y_reserves = x_needed/y_needed
        x_needed = (x_reserves/y_reserves)*y_needed
        return (x_needed, y_needed)


class Market: 
    def __init__(self,x,y,g,t,total_supply,pricing_model,c=1,u=1): 
        self.x=x
        self.y=y
        self.total_supply = total_supply
        self.g=g
        self.t=t
        self.c=c
        self.u=u
        self.pricing_model=pricing_model
        self.x_orders = 0
        self.y_orders = 0
        self.x_volume = 0
        self.y_volume = 0
        self.cum_y_slippage=0
        self.cum_x_slippage=0
        self.cum_y_fees=0
        self.cum_x_fees=0
        self.starting_fyt_price=self.spot_price()
    
    def apy(self,days_until_maturity):
        price = self.pricing_model.calc_spot_price(self.x,self.y,self.total_supply,self.t,self.c,self.u)
        return self.pricing_model.apy(price,days_until_maturity)
    
    def spot_price(self):
        return self.pricing_model.calc_spot_price(self.x,self.y,self.total_supply,self.t,self.c,self.u)
    
    def tick(self,step_size):
        self.t -= step_size
        
    def swap(self, amount, direction, token_in, token_out):
        if direction == "in":
            if token_in == "fyt" and token_out == "base":
                (without_fee_or_slippage,output_with_fee,output_without_fee,fee) = self.pricing_model.calc_in_given_out(amount,self.y+self.total_supply,self.x,token_in,self.g,self.t,self.c,self.u)
                if fee > 0:
                    self.x -= output_with_fee
                    self.y += amount
                    self.cum_x_slippage += abs(without_fee_or_slippage-output_without_fee)
                    self.cum_y_fees += fee
                    self.x_orders+=1
                    self.x_volume+=output_with_fee
            elif token_in == "base" and token_out == "fyt":
                (without_fee_or_slippage,output_with_fee,output_without_fee,fee) = self.pricing_model.calc_in_given_out(amount,self.x,self.y+self.total_supply,token_in,self.g,self.t,self.c,self.u)
                if fee > 0:
                    self.x += amount
                    self.y -= output_with_fee
                    self.cum_y_slippage += abs(without_fee_or_slippage-output_without_fee)
                    self.cum_x_fees += fee
                    self.y_orders+=1
                    self.y_volume+=output_with_fee
        elif direction == "out":
            if token_in == "fyt" and token_out == "base":
                (without_fee_or_slippage,output_with_fee,output_without_fee,fee) = \
                    self.pricing_model.calc_out_given_in(amount,self.y+self.total_supply,self.x,token_out,self.g,self.t,self.c,self.u)
                if fee > 0:
                    self.x -= output_with_fee
                    self.y += amount
                    self.cum_x_slippage += abs(without_fee_or_slippage-output_without_fee)
                    self.cum_x_fees += fee
                    self.x_orders+=1
                    self.x_volume+=output_with_fee
            elif token_in == "base" and token_out == "fyt":
                (without_fee_or_slippage,output_with_fee,output_without_fee,fee) = \
                    self.pricing_model.calc_out_given_in(amount,self.x,self.y+self.total_supply,token_out,self.g,self.t,self.c,self.u)
                if fee > 0:
                    self.x += amount
                    self.y -= output_with_fee
                    self.cum_y_slippage += abs(without_fee_or_slippage-output_without_fee)
                    self.cum_y_fees += fee
                    self.y_orders+=1
                    self.y_volume+=output_with_fee   
        return (without_fee_or_slippage,output_with_fee,output_without_fee,fee)

class YieldsSpacev2_Pricing_model(Element_Pricing_Model):
    @staticmethod
    def model_name():
        return "YieldsSpacev2"

    @staticmethod
    def calc_in_given_out(out,in_reserves,out_reserves,token_in,g,t,c,u):
        if token_in == "base": # calc shares in for fyt out
            #without_fee = YieldsSpacev2_Pricing_model.sharesInForFYTokenOut(dy=out,z=in_reserves,y=out_reserves,t=t,c=c,u=u)
            scale = c/u
            dy=out
            z=in_reserves/c # convert from x to z (x=cz)
            y=out_reserves
            k = scale*(u*z)**(1-t)+y**(1-t)
            without_fee_old = 1/u*pow(pow(u*z,1-t)+u/c*pow(y,1-t)-u/c*pow(y-dy,1-t),1/(1-t))-z
            without_fee = 1/u*((k-(y-dy)**(1-t))/scale)**(1/(1-t))-z
            without_fee = without_fee*c # convert from z to x
            # if without_fee_old!=without_fee:
            #     print('disagremeent calc shares in for fyt out (case 1): old: {}, new: {}'.format(without_fee_old,without_fee))
            fee = (out-without_fee)*g
            with_fee = without_fee+fee
            without_fee_or_slippage = pow((in_reserves)/(c/u*out_reserves),t)*out
        elif token_in == "fyt": # calc fyt in for shares out
            #without_fee = YieldsSpacev2_Pricing_model.fyTokenInForSharesOut(dz=out,z=out_reserves,y=in_reserves,t=t,c=c,u=u)
            scale = c/u
            dz=out/c
            z=out_reserves/c # convert from x to z (x=cz)
            y=in_reserves
            k = scale*(u*z)**(1-t)+y**(1-t)
            without_fee_old = pow(c/u*pow(u*z,1-t)+pow(y,1-t)-c/u*pow(u*z-u*dz,1-t),1/(1-t))-y
            without_fee = (k-scale*(u*z-u*dz)**(1-t))**(1/(1-t))-y
            # without_fee = without_fee*c # convert from z to x (x=cz)
            # if without_fee_old!=without_fee:
            #     print('disagremeent calc fyt in for shares out (case 2): old: {}, new: {}'.format(without_fee_old,without_fee))
            fee =  (without_fee-out)*g
            with_fee = without_fee+fee
            without_fee_or_slippage = pow(c/u*in_reserves/(out_reserves),t)*out
        return (without_fee_or_slippage,with_fee,without_fee,fee)
    
    @staticmethod
    def calc_out_given_in(in_,in_reserves,out_reserves,token_out,g,t,c,u):
        if token_out == "base": # calc shares out for fyt in
            #without_fee = YieldsSpacev2_Pricing_model.fyTokenOutForSharesIn(dz=in_,z=in_reserves,y=out_reserves,t=t,c=c,u=u)
            scale = c/u
            dy=in_
            z=out_reserves/c # convert from x to z (x=cz)
            y=in_reserves
            k = scale*(u*z)**(1-t)+y**(1-t)
            without_fee_old = z-1/u*pow(pow(u*z,1-t)+u/c*pow(y,1-t)-u/c*pow(y+dy,1-t),1/(1-t))
            without_fee = z-1/u*((k-(y+dy)**(1-t))/scale)**(1/(1-t))
            without_fee = without_fee*c # convert from z to x (x=cz)
            # if without_fee_old!=without_fee:
            #     print('disagremeent calc shares out for fyt in (case 3): old: {}, new: {}'.format(without_fee_old,without_fee))
            fee =  (in_-without_fee)*g
            with_fee = without_fee-fee
            without_fee_or_slippage = 1/pow((c/u*in_reserves)/out_reserves,t)*in_
        elif token_out == "fyt": # calc fyt out for shares in
            #without_fee = YieldsSpacev2_Pricing_model.sharesOutForFYTokenIn(dy=in_,z=out_reserves,y=in_reserves,t=t,c=c,u=u)
            scale = c/u
            dz=in_/c # convert from x to z (x=cz)
            z=in_reserves/c # convert from x to z (x=cz)
            y=out_reserves
            k = scale*(u*z)**(1-t)+y**(1-t)
            without_fee_old = y-pow(c/u*pow(u*z,1-t)+pow(y,1-t)-c/u*pow(u*z+u*dz,1-t),1/(1-t))
            without_fee = y-(k-scale*(u*z+u*dz)**(1-t))**(1/(1-t))
            # without_fee = without_fee*c # convert from z to x (x=cz)
            # if without_fee_old!=without_fee:
            #     print('disagremeent calc fyt out for shares inn (case 4): old: {}, new: {}'.format(without_fee_old,without_fee))
            fee =  (without_fee-in_)*g
            with_fee = without_fee-fee
            without_fee_or_slippage = 1/pow(in_reserves/(c/u*out_reserves),t)*in_
        return (without_fee_or_slippage,with_fee,without_fee,fee)

    @staticmethod
    def calc_x_reserves(APY,y_reserves,days_until_maturity,time_stretch,c,u):
        t=days_until_maturity/(365*time_stretch)
        T=days_until_maturity/365
        # result = y_reserves*(-(2/((1-T*APY/100)**(1/t)-1))-2)
        # result = 2*c*y_reserves/(-c + u*(-1/(APY*T - 1))**(1/t))
        # result = 2*c*y_reserves/(u*(-1/(APY/100*T - 1))**(1/t) - 1)
        # result = c*y_reserves/(u*(-1/(APY/100*T - 1))**(1/t) - 1)
        # result = c*y_reserves/u/(APY/100*T)
        # result = 2*c*y_reserves/(u*(-1/(APY/100*T - 1))**(1/t) - 1)
        # result = 2*c*y_reserves/(-c**2 + u*(-1/(APY/100*T - 1))**(1/t))
        # result = 2*c*y_reserves/(-c + u*(-1/(APY/100*T - 1))**(1/t))
        # display('c: {}, u: {}'.format(c,u))
        r = APY/100
        y = y_reserves
        # result = ((-APY/100*T + 1)/(c*y_reserves))**(1/t)/u
        # result = (((-r*T + 1)/(c*y))**(1/t))/u
        result = 2*c*y/(-c + u*(-1/(r*T - 1))**(1/t))
        # display('result: {}'.format(result))
        return result

    @staticmethod
    def calc_time_stretch(apy):
        return 3.09396 /( 0.02789 * apy)

    @staticmethod    
    def calc_liquidity(target_liquidity, market_price, apy, days_until_maturity, time_stretch,c,u):
      spot_price=YieldsSpacev2_Pricing_model.calc_spot_price_from_apy(apy,days_until_maturity)
    #   display('spot price: {}'.format(spot_price))
      t=days_until_maturity/(365*time_stretch)
      y_reserves = target_liquidity/market_price/2/(1-apy/100*t)
      x_reserves = YieldsSpacev2_Pricing_model.calc_x_reserves(apy,y_reserves,days_until_maturity,time_stretch,c,u)
      scaleUpFactor = target_liquidity/(x_reserves*market_price+y_reserves*market_price*spot_price)
      y_reserves = y_reserves * scaleUpFactor
      x_reserves = x_reserves * scaleUpFactor
      liquidity = x_reserves*market_price+y_reserves*market_price*spot_price
      actual_apy = YieldsSpacev2_Pricing_model.calc_apy_from_reserves(x_reserves,y_reserves,x_reserves+y_reserves,t,time_stretch,c,u)
      return (x_reserves,y_reserves,liquidity)

    @staticmethod
    def calc_apy_from_reserves(x_reserves,y_reserves,total_supply,t,t_stretch,c,u):
      spot_price = YieldsSpacev2_Pricing_model.calc_spot_price(x_reserves,y_reserves,total_supply,t,c,u)
      days_until_maturity = t * 365 * t_stretch
      return YieldsSpacev2_Pricing_model.apy(spot_price,days_until_maturity)

    @staticmethod
    def apy(price,days_until_maturity):
      T=days_until_maturity/365
      return (1-price)/T * 100
    
    @staticmethod
    def calc_spot_price_from_apy(apy,days_until_maturity):
      T=days_until_maturity/365
    #   display(T)
    #   display(1-apy*T/100)
      return 1- apy*T/100
    
    @staticmethod
    def calc_spot_price(x_reserves,y_reserves,total_supply,t,c,u):
        # display('c: {}, u: {}'.format(c,u))
        # display('denom: {}'.format((u*x_reserves)))
        # display('x reserves: {}'.format(x_reserves))
        return 1/pow(c*(y_reserves+total_supply)/(u*x_reserves),t)

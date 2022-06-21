class YieldsSpacev2_Pricing_model:
    @staticmethod
    def calc_in_given_out(out,in_reserves,out_reserves,token_in,g,t,c,u):
        k=c/u*pow(u*in_reserves,1-t) + pow(out_reserves,1-t)
        without_fee = pow(k-c/u*pow(u*out_reserves-u*out,1-t),1/(1-t)) - in_reserves
        if token_in == "base":
            fee =  (out-without_fee)*g
            with_fee = without_fee+fee
        elif token_in == "fyt":
            fee =  (without_fee-out)*g
            with_fee = without_fee+fee
        without_fee_or_slippage = pow(in_reserves/out_reserves,t)*out
        return (without_fee_or_slippage,with_fee,without_fee,fee)
    
    @staticmethod
    def calc_out_given_in(in_,in_reserves,out_reserves,token_out,g,t):
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

class Element_Pricing_Model:
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
    def calc_liquidity(target_liquidity, market_price, apy, days_until_maturity, time_stretch):
      spot_price=Element_Pricing_Model.calc_spot_price_from_apy(apy,days_until_maturity)
      y_reserves = target_liquidity/market_price/2/spot_price
      x_reserves = y_reserves
      t=days_until_maturity/(365*time_stretch)
      liquidity = 0
      actual_apy = 0
      while abs(actual_apy-apy) > 1e-9:
          x_reserves = Element_Pricing_Model.calc_x_reserves(apy,y_reserves,days_until_maturity,time_stretch)
          total_supply=x_reserves + y_reserves
          # calculate y_reserves need to hit target liquidity
          y_reserves_ub = (target_liquidity - x_reserves*market_price)/(market_price*spot_price)
          y_reserves_lb = Element_Pricing_Model.calc_x_reserves(apy,x_reserves,days_until_maturity,time_stretch)
          y_reserves = y_reserves_ub/2 + y_reserves_lb/2
          # calculate resulting liquidity
          liquidity=x_reserves*market_price+y_reserves*market_price*spot_price
          total_supply=x_reserves + y_reserves
          actual_apy = Element_Pricing_Model.calc_apy_from_reserves(x_reserves,y_reserves,total_supply,t,time_stretch)
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
    def calc_spot_price(x_reserves,y_reserves,total_supply,t):
        return 1/pow((y_reserves+total_supply)/x_reserves,t)
    
    @staticmethod
    def calc_in_given_out(out,in_reserves,out_reserves,token_in,g,t):
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
    def calc_out_given_in(in_,in_reserves,out_reserves,token_out,g,t):
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
    def __init__(self,x,y,g,t,total_supply,pricing_model): 
        self.x=x
        self.y=y
        self.total_supply = total_supply
        self.g=g
        self.t=t
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
        price = self.pricing_model.calc_spot_price(self.x,self.y,self.total_supply,self.t)
        return self.pricing_model.apy(price,days_until_maturity)
    
    def spot_price(self):
        return self.pricing_model.calc_spot_price(self.x,self.y,self.total_supply,self.t)
    
    def tick(self,step_size):
        self.t -= step_size
        
    def swap(self, amount, direction, token_in, token_out):
        if direction == "in":
            if token_in == "fyt" and token_out == "base":
                (without_fee_or_slippage,output_with_fee,output_without_fee,fee) = self.pricing_model.calc_in_given_out(amount,self.y+self.total_supply,self.x,token_in,self.g,self.t)
                if fee > 0:
                    self.x -= output_with_fee
                    self.y += amount
                    self.cum_x_slippage += abs(without_fee_or_slippage-output_without_fee)
                    self.cum_y_fees += fee
                    self.x_orders+=1
                    self.x_volume+=output_with_fee
            elif token_in == "base" and token_out == "fyt":
                (without_fee_or_slippage,output_with_fee,output_without_fee,fee) = self.pricing_model.calc_in_given_out(amount,self.x,self.y+self.total_supply,token_in,self.g,self.t)
                if fee > 0:
                    self.x += amount
                    self.y -= output_with_fee
                    self.cum_y_slippage += abs(without_fee_or_slippage-output_without_fee)
                    self.cum_x_fees += fee
                    self.y_orders+=1
                    self.y_volume+=output_with_fee
        elif direction == "out":
            if token_in == "fyt" and token_out == "base":
                (without_fee_or_slippage,output_with_fee,output_without_fee,fee) = self.pricing_model.calc_out_given_in(amount,self.y+self.total_supply,self.x,token_out,self.g,self.t)
                if fee > 0:
                    self.x -= output_with_fee
                    self.y += amount
                    self.cum_x_slippage += abs(without_fee_or_slippage-output_without_fee)
                    self.cum_x_fees += fee
                    self.x_orders+=1
                    self.x_volume+=output_with_fee
            elif token_in == "base" and token_out == "fyt":
                (without_fee_or_slippage,output_with_fee,output_without_fee,fee) = self.pricing_model.calc_out_given_in(amount,self.x,self.y+self.total_supply,token_out,self.g,self.t)
                if fee > 0:
                    self.x += amount
                    self.y -= output_with_fee
                    self.cum_y_slippage += abs(without_fee_or_slippage-output_without_fee)
                    self.cum_y_fees += fee
                    self.y_orders+=1
                    self.y_volume+=output_with_fee   
        return (without_fee_or_slippage,output_with_fee,output_without_fee,fee)

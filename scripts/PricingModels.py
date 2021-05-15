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
    def apy(price,days_until_maturity):
      T=days_until_maturity/365
      return (1-price)/T * 100
    
    @staticmethod
    def fyt_price(x_reserves,y_reserves,total_supply,t):
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
        self.starting_fyt_price=self.fyt_price()
    
    def apy(self,days_until_maturity):
        price = self.pricing_model.fyt_price(self.x,self.y,self.total_supply,self.t)
        return self.pricing_model.apy(price,days_until_maturity)
    
    def fyt_price(self):
        return self.pricing_model.fyt_price(self.x,self.y,self.total_supply,self.t)
    
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

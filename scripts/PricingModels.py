class Element_Pricing_Model:
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
            without_fee_or_slippage = pow(in_reserves/out_reserves,t)*out
        elif token_in == "fyt":
            fee =  (without_fee-out)*g
            with_fee = without_fee+fee
            without_fee_or_slippage = 1/pow(out_reserves/in_reserves,t)*out
        return (without_fee_or_slippage,with_fee,without_fee,fee)
    
    @staticmethod
    def calc_out_given_in(in_,in_reserves,out_reserves,token_out,g,t):
        k=pow(in_reserves,1-t) + pow(out_reserves,1-t)
        without_fee = out_reserves - pow(k-pow(in_reserves+in_,1-t),1/(1-t))
        if token_out == "base":
            fee =  (in_-without_fee)*g
            with_fee = without_fee-fee
            without_fee_or_slippage = pow(in_reserves/out_reserves,t)*in_
        elif token_out == "fyt":
            fee =  (without_fee-in_)*g
            with_fee = without_fee-fee
            without_fee_or_slippage = 1/pow(out_reserves/in_reserves,t)*in_
        return (without_fee_or_slippage,with_fee,without_fee,fee)

class Yield_Pricing_Model:
    @staticmethod
    def apy(x_reserves,y_reserves,total_supply):
        return ((y_reserves+total_supply)/x_reserves - 1) * 100
    
    @staticmethod
    def fyt_price(x_reserves,y_reserves,total_supply,t):
        return 1/pow((y_reserves+total_supply)/x_reserves,t)
    
    # input: number of base tokens to buy/sell
    # output: number of fy tokens bought/sold with fee, number of fy tokens bought/sold without fee, fy token fee
    @staticmethod
    def calc_in_given_out(out,in_reserves,out_reserves,token_in,g,t):
        k=pow(in_reserves,1-t/g) + pow(out_reserves,1-t/g)
        # calculate the number of fyts the specified amount of base tokens will cost with fees
        output_with_fee = pow(k-pow(out_reserves-out,1-t/g),1/(1-t/g)) - in_reserves
        k=pow(in_reserves,1-t) + pow(out_reserves,1-t)
        # calculate the number of fyts the specified amount of base tokens will cost without fees
        output_without_fee = pow(k-pow(out_reserves-out,1-t),1/(1-t)) - in_reserves
        # output_with_fee is greater than output_without_fee bc the fee adds additional cost
        fee =  abs(output_with_fee - output_without_fee)
        if token_in == "base":
            without_fee_or_slippage = pow(in_reserves/out_reserves,t)*out
        elif token_in == "fyt":
            without_fee_or_slippage = 1/pow(out_reserves/in_reserves,t)*out
        return (without_fee_or_slippage,output_with_fee,output_without_fee,fee)

    # input: number of fy tokens to buy/sell
    # output: number of base tokens bought/sold with fee, number of base tokens bought/sold without fee, base token fee    
    @staticmethod
    def calc_out_given_in(in_,in_reserves,out_reserves,token_out,g,t):
        k=pow(in_reserves,1-t*g) + pow(out_reserves,1-t*g)
        # calculate the number of base tokens the specified amount of fy tokens will cost with fees
        output_with_fee = out_reserves - pow(k-pow(in_reserves+in_,1-t*g),1/(1-t*g))
        k=pow(in_reserves,1-t) + pow(out_reserves,1-t)
        # calculate the number of base tokens the specified amount of fy tokens will cost without fees
        output_without_fee = out_reserves - pow(k-pow(in_reserves+in_,1-t),1/(1-t))
        # output_with_fee is greater than output_without_fee bc the fee adds additional cost
        fee =  abs(output_with_fee - output_without_fee)
        if token_out == "base":
            without_fee_or_slippage = pow(in_reserves/out_reserves,t)*in_
        elif token_out == "fyt":
            without_fee_or_slippage = 1/pow(out_reserves/in_reserves,t)*in_
        return (without_fee_or_slippage,output_with_fee,output_without_fee,fee)

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

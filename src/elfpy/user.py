"""
Implements abstract classes that control user behavior

TODO: rewrite all functions to have typed inputs
"""
from elfpy.utils.basic_dataclass import *
from elfpy.utils.fmt import *   # float→str formatter, also imports numpy as np
import elfpy.utils.time as time_utils
from elfpy.utils.bcolors import bcolors


@dataclass
class AgentWallet(BasicDataclass):
    """stores what's in the agent's wallet"""

    # fungible
    base_in_wallet: float = 0
    lp_in_wallet: float = 0  # they're fungible!
    fees_paid: float = 0
    # non-fungible (identified by mint_time, stored as dict)
    token_in_wallet: dict = field(default_factory=dict)
    base_in_protocol: dict = field(default_factory=dict)
    token_in_protocol: dict = field(default_factory=dict)


class User:
    """
    Implements abstract classes that control user behavior
    user has a budget that is a dict, keyed with a date
    value is an inte with how many tokens they have for that date
    """

    def __init__(self, market, rng, wallet_address, budget=0, verbose=False):
        """
        Set up initial conditions
        """
        self.market = market
        self.budget = budget
        assert self.budget >= 0, f"ERROR: budget should be initialized (>=0), but is {self.budget}"
        self.wallet = AgentWallet(base_in_wallet=self.budget)
        self.rng = rng
        self.wallet_address = wallet_address
        self.verbose = verbose
        self.last_update_spend = 0
        self.product_of_time_and_base = 0
        self.weighted_average_spend = 0
        self.position_list = []
        self.status_update()

    @dataclass
    class UserAction:
        """user action specification"""

        action_type: str
        trade_amount: float
        wallet_address: int
        agent: object
        mint_time: float = None
        fee_percent: float = field(init=False)
        init_share_price: float = field(init=False)
        share_price: float = field(init=False)  
        share_reserves: float = field(init=False)
        bond_reserves: float = field(init=False)
        share_buffer: float = field(init=False)
        bond_buffer: float = field(init=False)
        liquidity_pool: float = field(init=False)
        rate: float = field(init=False)
        time_remaining: float = field(init=False)
        stretched_time_remaining: float = field(init=False)

        def print_description_string(self):
            output_string = f"🤖 {bcolors.FAIL}{self.wallet_address}{bcolors.ENDC}"
            # for key, value in self.__dataclass_fields__.items():
            for key, value in self.__dict__.items():
                if key == "action_type":
                    output_string += f" execute {bcolors.FAIL}{value}(){bcolors.ENDC}"
                elif key not in ["wallet_address","agent"]:
                    output_string += f" {key}: "
                    if value<2:
                        output_string += f"{value:.5f}"
                    elif value<100:
                        output_string += f"{value:.2f}"
                    else:
                        output_string += f"{value:,.0f}"
            print(output_string)

        def update_market_variables(self, market, wallet_address=None):
            if self.mint_time is None:
                self.mint_time = market.time
            self.fee_percent = market.fee_percent
            self.init_share_price = market.init_share_price
            self.share_price = market.share_price
            self.share_reserves = market.share_reserves
            self.bond_reserves = market.bond_reserves
            self.share_buffer = market.share_buffer
            self.bond_buffer = market.bond_buffer
            self.liquidity_pool = market.liquidity_pool
            self.rate = market.rate
            if wallet_address is not None:
                self.wallet_address = wallet_address
            self.time_remaining = time_utils.get_yearfrac_remaining(
                market.time, self.mint_time, market.token_duration
            )
            self.stretched_time_remaining = time_utils.stretch_time(
                self.time_remaining, market.time_stretch_constant
            )

    # user functions defined below
    def create_user_action(self, action_type, trade_amount, mint_time=None):
        user_action = self.UserAction(
            action_type=action_type,
            trade_amount=trade_amount,
            wallet_address=self.wallet_address,
            agent=self,
            mint_time=mint_time
        )
        user_action.update_market_variables(self.market)
        return user_action

    def action(self):
        """Specify action from the policy"""
        raise NotImplementedError

    def get_max_long(self):
        """Returns the amount of base that the user can spend."""
        return np.minimum(self.wallet.base_in_wallet, self.market.bond_reserves)

    def get_max_pt_short(self, mint_time, eps=1.0):
        """
        Returns an approximation of maximum amount of base that the user can short given current market conditions

        TODO: This currently is a first-order approximation.
        An alternative is to do this iteratively and find a max trade, but that is probably too slow.
        Maybe we could add an optional flag to iteratively solve it, like num_iters.
        """
        if self.market.share_reserves == 0:
            return 0
        # time_remaining = time_utils.get_yearfrac_remaining(self.market.time, mint_time, self.market.token_duration)
        # stretched_time_remaining = time_utils.stretch_time(time_remaining, self.market.time_stretch_constant)
        # output_with_fee = self.market.pricing_model.calc_out_given_in(
        #     self.wallet.base_in_wallet,
        #     self.market.share_reserves,
        #     self.market.bond_reserves,
        #     "base",
        #     self.market.fee_percent,
        #     stretched_time_remaining,
        #     self.market.init_share_price,
        #     self.market.share_price,
        # )[1]
        # max_short = self.wallet.base_in_wallet + output_with_fee - eps
        # save lower bound on max short, calculated as the most amount of base you can hope to extract from the market
        max_pt_short = self.market.share_reserves * self.market.share_price / self.market.spot_price
        return max_pt_short

    def get_trade(self):
        """
        Helper function for computing a user trade
        direction is chosen based on this logic:
        when entering a trade (open long or short),
        we use calcOutGivenIn because we know how much we want to spend,
        and care less about how much we get for it.
        when exiting a trade (close long or short),
        we use calcInGivenOut because we know how much we want to get,
        and care less about how much we have to spend.
        we spend what we have to spend, and get what we get.
        """
        self.status_update()
        action_list = self.action()  # get the action list from the policy
        for action in action_list:  # edit each action in place
            if action.mint_time is None:
                action.mint_time = self.market.time
            if action.action_type == "close_short":
                action.token_in_protocol = self.wallet.token_in_protocol[action.mint_time]
                action.base_in_protocol = self.wallet.base_in_protocol[action.mint_time]
            if action.action_type == "close_short":
                action.token_in_protocol = self.wallet.token_in_protocol[action.mint_time]
                action.base_in_protocol = self.wallet.base_in_protocol[action.mint_time]
        # TODO: Add safety checks
        # e.g. if trade amount > 0, whether there is enough money in the account
        # if len(trade_action) > 0: # there is a trade
        #    token_in, token_out, trade_amount_usd = trade_action
        #    assert trade_amount_usd >= 0, (
        #        f"user.py: ERROR: Trade amount should not be negative, but is {trade_amount_usd}"
        #        f" token_in={token_in} token_out={token_out}"
        #    )
        return action_list

    def update_spend(self):
        # TODO: add back in with high level of logging, category = "spending"
        # if self.verbose:
            # print(f"  time={self.market.time} last_update_spend={self.last_update_spend} budget={self.budget} base_in_wallet={self.wallet['base_in_wallet']}") if self.verbose else None
        new_spend = (self.market.time - self.last_update_spend) * (self.budget - self.wallet["base_in_wallet"])
        self.product_of_time_and_base += new_spend
        self.weighted_average_spend = self.product_of_time_and_base / self.market.time if self.market.time > 0 else 0
        # TODO: add back in with high level of logging, category = "spending"
        # if self.verbose:
            # print(f"  weighted_average_spend={self.weighted_average_spend} added {new_spend} deltaT={self.market.time - self.last_update_spend} delta₡={self.budget - self.wallet['base_in_wallet']}") if self.verbose else None
        self.last_update_spend = self.market.time
        return self.weighted_average_spend

    def update_wallet(self, agent_deltas):
        """Update the user's wallet"""
        self.update_spend()
        for wallet_key, wallet in agent_deltas.items():
            if wallet is None:
                pass
            elif wallet_key in ["base_in_wallet", "lp_in_wallet", "fees_paid"]:
                if self.verbose and wallet != 0 or self.wallet[wallet_key] !=0:
                    print(f"   pre-trade {wallet_key:17s} = {self.wallet[wallet_key]:,.0f}")
                self.wallet[wallet_key] += wallet
                if self.verbose and wallet != 0 or self.wallet[wallet_key] !=0:
                    print(f"  post-trade {wallet_key:17s} = {self.wallet[wallet_key]:,.0f}")
                    print(f"                              Δ = {wallet:+,.0f}")
            # these wallets have mint_time attached, stored as dicts
            elif wallet_key in ["base_in_protocol", "token_in_wallet", "token_in_protocol"]:
                for mint_time, account in wallet.items():
                    # print(f"  updating wallet {wallet_key} mint_time={mint_time} account={account}")
                    if self.verbose:
                        print(f"   pre-trade {wallet_key:17s} = {{{' '.join([f'{k}: {v:,.0f}' for k, v in self.wallet[wallet_key].items()])}}}")
                    if mint_time in self.wallet[wallet_key]: #  entry already exists for this mint_time, so add to it
                        # print(f"updating index {self.wallet[wallet_key]} at mint_time={mint_time} adding={account}")
                        self.wallet[wallet_key][mint_time] += account
                    else:
                        # print(f"updating dict {wallet_key} mint_time={mint_time} account={account}")
                        # print(f"taking {self.wallet[wallet_key]}")
                        # print(f"and updating {{mint_time: account}}")
                        self.wallet[wallet_key].update({mint_time: account})
                    if self.verbose:
                        print(f"  post-trade {wallet_key:17s} = {{{' '.join([f'{k}: {v:,.0f}' for k, v in self.wallet[wallet_key].items()])}}}")
            elif wallet_key == "fees_paid":
                pass
            else:
                raise ValueError(f"wallet_key={wallet_key} is not allowed.")

    def liquidate(self):
        """close up shop"""
        self.status_update()
        is_LP = True if hasattr(self, "can_LP") else False
        is_shorter = True if hasattr(self, "can_open_short") else False
        action_list = []
        if is_shorter:
            if self.has_opened_short:
                for mint_time, position in self.wallet.token_in_protocol.items():
                    if self.verbose:
                        print(f"  liquidate() evaluating closing short: mint_time={mint_time} position={position}")
                    if position < 0:
                        action_list.append(self.create_user_action(
                                action_type="close_short",
                                trade_amount= -position,
                                mint_time=mint_time,
                        ))
        # if self.verbose:
            # action_list_string = '\n action = '.join([f' {x}' for x in action_list])
            # print(f"liquidate: short action_list:\n action:{action_list_string}")
        if is_LP:
            if self.has_LPd:
                action_list.append(self.create_user_action(
                        action_type="remove_liquidity",
                        trade_amount=self.wallet.lp_in_wallet
                ))
        return action_list

    def status_update(self):
        self.is_LP = True if hasattr(self, "amount_to_LP") else False
        self.is_shorter = True if hasattr(self, "pt_to_short") else False
        if self.is_LP:
            self.has_LPd = self.wallet.lp_in_wallet > 0
            self.can_LP = self.wallet.base_in_wallet >= self.amount_to_LP
        self.position_list = list(self.wallet.token_in_protocol.values())
        self.mint_times = list(self.wallet.token_in_protocol.keys())
        if self.is_shorter:
            self.has_opened_short = True if any([x < -1 for x in self.position_list]) else False
            self.can_open_short = self.get_max_pt_short(self.market.time) >= self.pt_to_short

    def status_report(self):
        self.status_update()
        output_string = f"🤖 {bcolors.FAIL}{self.wallet_address}{bcolors.ENDC} "
        string_list = []
        if self.is_LP:         # this agent can LP! he has the logic circuits to do so
            string_list.append(f"has_LPd: {self.has_LPd}, can_LP: {self.can_LP}")
        if self.is_shorter:  # this agent can short! he has the logic circuits to do so
            string_list.append(f"has_opened_short: {self.has_opened_short}")
            string_list.append(f"can_open_short: {self.can_open_short}")
            string_list.append(f"max_short: {self.get_max_pt_short(self.market.time):,.0f}")
        string_list.append(f"base_in_wallet: {bcolors.OKBLUE}{self.wallet.base_in_wallet:,.0f}{bcolors.ENDC}")
        string_list.append(f"position_list: {self.position_list} sum(positions)={sum(self.position_list)}") if self.position_list else None
        string_list.append(f"LP_position: {bcolors.OKCYAN}{self.wallet.lp_in_wallet:,.0f}{bcolors.ENDC}") if self.is_LP else None
        string_list.append(f"fees_paid: {bcolors.OKCYAN}{self.wallet.fees_paid:,.0f}{bcolors.ENDC}") if self.wallet.fees_paid > 0 else None
        output_string += ", ".join(string_list)
        return output_string

    def final_report(self):
        self.status_update()
        price = self.market.spot_price
        base = self.wallet['base_in_wallet']
        tokens = sum(self.position_list)
        worth = base + tokens * price
        PnL = worth - self.budget
        spend = self.weighted_average_spend
        holding_period_rate = PnL / spend if spend != 0 else 0
        annual_percentage_rate = holding_period_rate / self.market.time
        output_string = f" 🤖 {bcolors.FAIL}{self.wallet_address}{bcolors.ENDC}"
        if PnL < 0:
            output_string += f" lost {bcolors.FAIL}"
        else:
            output_string += f" made {bcolors.OKGREEN}"
        output_string += f"{fmt(PnL)}{bcolors.ENDC}"
        output_string += f" on ₡{bcolors.OKCYAN}{fmt(spend)}{bcolors.ENDC} spent, APR = "
        output_string += f"{bcolors.OKGREEN}" if annual_percentage_rate > 0 else f"{bcolors.FAIL}"
        output_string += f"{annual_percentage_rate:,.2%}{bcolors.ENDC}"
        output_string += f" ({holding_period_rate:,.2%} in {fmt(self.market.time,precision=2)} years)"
        output_string += f", net worth = ₡{bcolors.FAIL}{fmt(worth)}{bcolors.ENDC}"
        output_string += f" from {fmt(base)} base and {fmt(tokens)} tokens at p={price}\n"
        print(output_string)

"""
Implements abstract classes that control user behavior

TODO: rewrite all functions to have typed inputs
"""

from dataclasses import dataclass
from dataclasses import field
from typing import Optional

import numpy as np

from elfpy.utils.float_to_string import float_to_string
from elfpy.utils.bcolors import bcolors


@dataclass(frozen=False)
class AgentWallet:
    """stores what's in the agent's wallet"""

    # fungible
    base_in_wallet: float
    lp_in_wallet: float = 0  # they're fungible!
    fees_paid: float = 0
    # non-fungible (identified by mint_time, stored as dict)
    token_in_wallet: dict = field(default_factory=dict)
    base_in_protocol: dict = field(default_factory=dict)
    token_in_protocol: dict = field(default_factory=dict)
    effective_price: float = field(init=False)  # calculated after init, only for transactions

    def __post_init__(self):
        """post initialization function"""
        # check if this represents a trade (one side will be negative)
        total_tokens = sum(list(self.token_in_wallet.values()))
        if self.base_in_wallet < 0 or total_tokens < 0:
            self.effective_price = total_tokens / self.base_in_wallet

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __str__(self):
        output_string = ""
        for key, value in vars(self).items():
            if value:  #  check if object exists
                if value != 0:
                    output_string += f" {key}: "
                    if isinstance(value, float):
                        output_string += f"{float_to_string(value)}"
                    elif isinstance(value, list):
                        output_string += "[" + ", ".join([float_to_string(x) for x in value]) + "]"
                    elif isinstance(value, dict):
                        output_string += "{" + ", ".join([f"{k}: {float_to_string(v)}" for k, v in value.items()]) + "}"
                    else:
                        output_string += f"{value}"
        return output_string


class User:
    """
    Implements abstract classes that control user behavior
    user has a budget that is a dict, keyed with a date
    value is an inte with how many tokens they have for that date
    """

    def __init__(self, market, rng, wallet_address, budget, verbose):
        """
        Set up initial conditions
        """
        self.market = market
        self.rng = rng
        self.wallet_address = wallet_address
        self.budget = budget
        self.verbose = False if verbose is None else verbose
        self.last_update_spend = 0
        self.product_of_time_and_base = 0
        self.weighted_average_spend = 0
        self.position_list = []
        self.wallet = AgentWallet(base_in_wallet=budget)
        self.status_update()

    @dataclass
    class AgentAction:
        """user action specification"""

        # these two variables are required to be set by the strategy
        action_type: str
        trade_amount: float
        # wallet_address is always set automatically by the basic user class
        wallet_address: int
        # mint time is set only for trades that act on existing positions (close long or close short)
        mint_time: Optional[float] = None

        def print_description_string(self):
            output_string = f"{bcolors.FAIL}{self.wallet_address}{bcolors.ENDC}"
            for key, value in self.__dict__.items():
                if key == "action_type":
                    output_string += f" execute {bcolors.FAIL}{value}(){bcolors.ENDC}"
                elif key in ["trade_amount", "mint_time"]:
                    output_string += f" {key}: {float_to_string(value)}"
                elif key not in ["wallet_address", "agent"]:
                    output_string += f" {key}: {float_to_string(value)}"
            print(output_string)

    # user functions defined below
    def create_agent_action(self, action_type, trade_amount, mint_time=None):
        agent_action = self.AgentAction(
            # these two variables are required to be set by the strategy
            action_type=action_type,
            trade_amount=trade_amount,
            # next two variables are set automatically by the basic user class
            wallet_address=self.wallet_address,
            mint_time=mint_time,
        )
        return agent_action

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
        max_pt_short = self.market.share_reserves * self.market.share_price / self.market.spot_price
        return max_pt_short

    def get_trade_list(self):
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
        """Track over time the user's weighted average spend, for return calculation"""
        new_spend = (self.market.time - self.last_update_spend) * (self.budget - self.wallet["base_in_wallet"])
        self.product_of_time_and_base += new_spend
        self.weighted_average_spend = self.product_of_time_and_base / self.market.time if self.market.time > 0 else 0
        self.last_update_spend = self.market.time
        return self.weighted_average_spend

    def update_wallet(self, agent_deltas):
        """Update the user's wallet"""
        self.update_spend()
        for wallet_key, wallet in agent_deltas.__dict__.items():
            if wallet is None:
                pass
            elif wallet_key in ["base_in_wallet", "lp_in_wallet", "fees_paid"]:
                # TODO: add back in with high level of logging, category = "trade"
                # if self.verbose and wallet != 0 or self.wallet[wallet_key] !=0:
                #    print(f"   pre-trade {wallet_key:17s} = {self.wallet[wallet_key]:,.0f}")
                self.wallet[wallet_key] += wallet
                # TODO: add back in with high level of logging, category = "trade"
                # if self.verbose and wallet != 0 or self.wallet[wallet_key] !=0:
                #    print(f"  post-trade {wallet_key:17s} = {self.wallet[wallet_key]:,.0f}")
                #    print(f"                              Δ = {wallet:+,.0f}")
            # these wallets have mint_time attached, stored as dicts
            elif wallet_key in ["base_in_protocol", "token_in_wallet", "token_in_protocol"]:
                for mint_time, account in wallet.items():
                    # TODO: add back in with high level of logging, category = "trade"
                    # if self.verbose:
                    #    print(f"   pre-trade {wallet_key:17s} = \
                    #       {{{' '.join([f'{k}: {v:,.0f}' for k, v in self.wallet[wallet_key].items()])}}}")
                    if mint_time in self.wallet[wallet_key]:  #  entry already exists for this mint_time, so add to it
                        self.wallet[wallet_key][mint_time] += account
                    else:
                        self.wallet[wallet_key].update({mint_time: account})
                    # TODO: add back in with high level of logging, category = "trade"
                    # if self.verbose:
                    #    print(f"  post-trade {wallet_key:17s} = \
                    #       {{{' '.join([f'{k}: {v:,.0f}' for k, v in self.wallet[wallet_key].items()])}}}")
            elif wallet_key in ["fees_paid", "effective_price"]:
                pass
            else:
                raise ValueError(f"wallet_key={wallet_key} is not allowed.")

    def get_liquidation_trades(self):
        """close up shop"""
        self.status_update()
        action_list = []
        if self.is_shorter:
            if self.has_opened_short:
                for mint_time, position in self.wallet.token_in_protocol.items():
                    if self.verbose:
                        print(
                            "  get_liquidation_trades() evaluating closing short:"
                            f" mint_time={mint_time} position={position}"
                        )
                    if position < 0:
                        action_list.append(
                            self.create_agent_action(
                                action_type="close_short",
                                trade_amount=-position,
                                mint_time=mint_time,
                            )
                        )
        if self.is_LP:
            if self.has_LPd:
                action_list.append(
                    self.create_agent_action(action_type="remove_liquidity", trade_amount=self.wallet.lp_in_wallet)
                )
        return action_list

    def status_update(self):
        if self.is_LP:
            self.has_LPd = self.wallet.lp_in_wallet > 0
            self.can_LP = self.wallet.base_in_wallet >= getattr(self, "amount_to_LP", np.inf)
        self.position_list = list(self.wallet.token_in_protocol.values())
        self.mint_times = list(self.wallet.token_in_protocol.keys())
        if self.is_shorter:
            self.has_opened_short = bool(any([x < -1 for x in self.position_list]))
            self.can_open_short = self.get_max_pt_short(self.market.time) >= getattr(self, "pt_to_short", np.inf)

    def status_report(self):
        self.status_update()
        output_string = f"{bcolors.FAIL}{self.wallet_address}{bcolors.ENDC} "
        string_list = []
        if self.is_LP:  # this agent can LP! he has the logic circuits to do so
            string_list.append(f"has_LPd: {self.has_LPd}, can_LP: {self.can_LP}")
        if self.is_shorter:  # this agent can short! he has the logic circuits to do so
            string_list.append(f"has_opened_short: {self.has_opened_short}")
            string_list.append(f"can_open_short: {self.can_open_short}")
            string_list.append(f"max_short: {self.get_max_pt_short(self.market.time):,.0f}")
        string_list.append(f"base_in_wallet: {bcolors.OKBLUE}{self.wallet.base_in_wallet:,.0f}{bcolors.ENDC}")
        string_list.append(
            f"position_list: {self.position_list} sum(positions)={sum(self.position_list)}"
        ) if self.position_list else None
        string_list.append(
            f"LP_position: {bcolors.OKCYAN}{self.wallet.lp_in_wallet:,.0f}{bcolors.ENDC}"
        ) if self.is_LP else None
        string_list.append(
            f"fees_paid: {bcolors.OKCYAN}{self.wallet.fees_paid:,.0f}{bcolors.ENDC}"
        ) if self.wallet.fees_paid > 0 else None
        output_string += ", ".join(string_list)
        return output_string

    def final_report(self):
        self.status_update()
        price = self.market.spot_price
        base = self.wallet.base_in_wallet
        tokens = sum(self.position_list) if len(self.position_list) > 0 else 0
        worth = base + tokens * price
        PnL = worth - self.budget
        spend = self.weighted_average_spend
        holding_period_rate = PnL / spend if spend != 0 else 0
        annual_percentage_rate = holding_period_rate / self.market.time
        output_string = f" {bcolors.FAIL}{self.wallet_address}{bcolors.ENDC}"
        if PnL < 0:
            output_string += f" lost {bcolors.FAIL}"
        else:
            output_string += f" made {bcolors.OKGREEN}"
        output_string += f"{float_to_string(PnL)}{bcolors.ENDC}"
        output_string += f" on ₡{bcolors.OKCYAN}{float_to_string(spend)}{bcolors.ENDC} spent, APR = "
        output_string += f"{bcolors.OKGREEN}" if annual_percentage_rate > 0 else f"{bcolors.FAIL}"
        output_string += f"{annual_percentage_rate:,.2%}{bcolors.ENDC}"
        output_string += f" ({holding_period_rate:,.2%} in {float_to_string(self.market.time,precision=2)} years)"
        output_string += f", net worth = ₡{bcolors.FAIL}{float_to_string(worth)}{bcolors.ENDC}"
        output_string += f" from {float_to_string(base)} base and {float_to_string(tokens)} tokens at p={price}\n"
        print(output_string)

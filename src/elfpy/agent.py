"""
Implements abstract classes that control agent behavior
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.random._generator import Generator
from elfpy.markets import Market

from elfpy.utils.outputs import float_to_string
from elfpy.utils.bcolors import Bcolors as bcolors
from elfpy.wallet import Wallet


AgentActionType = Literal["close_short", "close_long", "open_short", "open_long", "add_liquidity", "remove_liquidity"]
TradeDirection = Literal["out", "in"]

# TODO: The agent class has too many instance attributes (8/7)
#     we should move some, like budget and wallet_address, into the agent wallet and out of User
class Agent:
    """
    Implements abstract classes that control agent behavior
    agent has a budget that is a dict, keyed with a date
    value is an inte with how many tokens they have for that date
    """

    # TODO: variables assigned by child classes are referenced by User -- need to fix up agent inheritance
    # pylint: disable=no-member
    # pylint: disable=too-many-arguments

    def __init__(self, market: Market, rng: Generator, wallet_address: int, budget: float, verbose: bool):
        """
        Set up initial conditions
        """
        self.market: Market = market
        self.rng: Generator = rng
        # TODO: remove this, wallet_address is a property of wallet, not the agent
        self.wallet_address: int = wallet_address
        self.budget: float = budget
        self.verbose: bool = verbose
        self.last_update_spend: float = 0  # timestamp
        self.product_of_time_and_base: float = 0
        self.wallet: Wallet = Wallet(address=wallet_address, base_in_wallet=budget)

    # TODO: this is really a MarketAction.  should refactor this to live under the Market.
    # Agent's don't need to know about markets, remove this coupling!
    @dataclass
    class AgentAction:
        """agent action specification"""

        # these two variables are required to be set by the strategy
        action_type: AgentActionType
        trade_amount: float
        # wallet_address is always set automatically by the basic agent class
        wallet_address: int

        # mint time is set only for trades that act on existing positions (close long or close short)
        mint_time: float = 0

        def print_description_string(self) -> None:
            """Print a description of the Action"""
            output_string = f"{bcolors.FAIL}{self.wallet_address}{bcolors.ENDC}"
            for key, value in self.__dict__.items():
                if key == "action_type":
                    output_string += f" execute {bcolors.FAIL}{value}(){bcolors.ENDC}"
                elif key in ["trade_amount", "mint_time"]:
                    output_string += f" {key}: {float_to_string(value)}"
                elif key not in ["wallet_address", "agent"]:
                    output_string += f" {key}: {float_to_string(value)}"
            print(output_string)

    def create_agent_action(self, action_type: AgentActionType, trade_amount: float, mint_time: float=0) -> AgentAction:
        """Instantiate a agent action"""
        agent_action = self.AgentAction(
            # these two variables are required to be set by the strategy
            action_type=action_type,
            trade_amount=trade_amount,
            # next two variables are set automatically by the basic agent class
            wallet_address=self.wallet_address,
            mint_time=mint_time,
        )
        return agent_action

    def action(self) -> list[AgentAction]:
        """Specify action from the policy"""
        raise NotImplementedError

    def get_max_long(self) -> float:
        """Returns the amount of base that the agent can spend."""
        return np.minimum(self.wallet.base_in_wallet, self.market.bond_reserves)

    # TODO: Fix up this function
    def get_max_pt_short(self) -> float:
        """
        Returns an approximation of maximum amount of base that the agent can short given current market conditions

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
        Helper function for computing a agent trade
        direction is chosen based on this logic:
        when entering a trade (open long or short),
        we use calcOutGivenIn because we know how much we want to spend,
        and care less about how much we get for it.
        when exiting a trade (close long or short),
        we use calcInGivenOut because we know how much we want to get,
        and care less about how much we have to spend.
        we spend what we have to spend, and get what we get.
        """
        action_list = self.action()  # get the action list from the policy
        for action in action_list:  # edit each action in place
            if action.mint_time is None:
                action.mint_time = self.market.time
        # TODO: Add safety checks
        # e.g. if trade amount > 0, whether there is enough money in the account
        # if len(trade_action) > 0: # there is a trade
        #    token_in, token_out, trade_amount_usd = trade_action
        #    assert trade_amount_usd >= 0, (
        #        f"agent.py: ERROR: Trade amount should not be negative, but is {trade_amount_usd}"
        #        f" token_in={token_in} token_out={token_out}"
        #    )
        return action_list

    def update_spend(self) -> None:
        """Track over time the agent's weighted average spend, for return calculation"""
        new_spend = (self.market.time - self.last_update_spend) * (self.budget - self.wallet["base_in_wallet"])
        self.product_of_time_and_base += new_spend
        self.last_update_spend = self.market.time

    def update_wallet(self, wallet_deltas: Wallet) -> None:
        """Update the agent's wallet"""
        self.update_spend()
        for key, value_or_dict in wallet_deltas.__dict__.items():
            if value_or_dict is None:
                pass

            # handle update value case
            if key in ["base_in_wallet", "lp_in_wallet", "fees_paid"]:
                # TODO: add back in with high level of logging, category = "trade"
                # if self.verbose and wallet != 0 or self.wallet[wallet_key] !=0:
                #    print(f"   pre-trade {wallet_key:17s} = {self.wallet[wallet_key]:,.0f}")
                self.wallet[key] += value_or_dict
                # TODO: add back in with high level of logging, category = "trade"
                # if self.verbose and wallet != 0 or self.wallet[wallet_key] !=0:
                #    print(f"  post-trade {wallet_key:17s} = {self.wallet[wallet_key]:,.0f}")
                #    print(f"                              Δ = {wallet:+,.0f}")

            # handle updating a dict
            # these values have mint_time attached, stored as dicts
            elif key in ["base_in_protocol", "token_in_wallet", "token_in_protocol"]:
                for mint_time, amount in value_or_dict.items():
                    # TODO: add back in with high level of logging, category = "trade"
                    # if self.verbose:
                    #    print(f"   pre-trade {wallet_key:17s} = \
                    #       {{{' '.join([f'{k}: {v:,.0f}' for k, v in self.wallet[wallet_key].items()])}}}")
                    if mint_time in self.wallet[key]:  #  entry already exists for this mint_time, so add to it
                        self.wallet[key][mint_time] += amount
                    else:
                        self.wallet[key].update({mint_time: amount})
                    # TODO: add back in with high level of logging, category = "trade"
                    # if self.verbose:
                    #    print(f"  post-trade {wallet_key:17s} = \
                    #       {{{' '.join([f'{k}: {v:,.0f}' for k, v in self.wallet[wallet_key].items()])}}}")
            elif key in ["fees_paid", "effective_price"]:
                pass
            else:
                raise ValueError(f"wallet_key={key} is not allowed.")

    def get_liquidation_trades(self) -> list[AgentAction]:
        """Get final trades for liquidating positions"""
        action_list: list[Agent.AgentAction] = []
        for mint_time, position in self.wallet.token_in_protocol.items():
            if self.verbose:
                print(
                    "  get_liquidation_trades() evaluating closing short:" f" mint_time={mint_time} position={position}"
                )
            if position < 0:
                action_list.append(
                    self.create_agent_action(
                        action_type="close_short",
                        trade_amount=-position,
                        mint_time=mint_time,
                    )
                )
        if self.wallet.lp_in_wallet > 0:
            action_list.append(
                self.create_agent_action(
                    action_type="remove_liquidity", trade_amount=self.wallet.lp_in_wallet, mint_time=self.market.time
                )
            )
        return action_list

    # TODO: should be called get_status_report
    def status_report(self) -> str:
        """Returns a status report for the agent"""
        output_string = f"{bcolors.FAIL}{self.wallet_address}{bcolors.ENDC} "
        string_list = []
        string_list.append(f"base_in_wallet: {bcolors.OKBLUE}{self.wallet.base_in_wallet:,.0f}{bcolors.ENDC}")
        if self.wallet.fees_paid:
            string_list.append(f"fees_paid: {bcolors.OKCYAN}{self.wallet.fees_paid:,.0f}{bcolors.ENDC}")
        output_string += ", ".join(string_list)
        return output_string

    # TODO: should be called print_final_report.  better yet, make get_final_report that returns a
    # string, caller can print
    def final_report(self) -> None:
        """Prints a report of the agent's state"""
        price = self.market.spot_price
        base = self.wallet.base_in_wallet
        block_position_list = list(self.wallet.token_in_protocol.values())
        tokens = sum(block_position_list) if len(block_position_list) > 0 else 0
        worth = base + tokens * price
        profit_and_loss = worth - self.budget
        weighted_average_spend = self.product_of_time_and_base / self.market.time if self.market.time > 0 else 0
        spend = weighted_average_spend
        holding_period_rate = profit_and_loss / spend if spend != 0 else 0
        annual_percentage_rate = holding_period_rate / self.market.time
        output_string = f" {bcolors.FAIL}{self.wallet_address}{bcolors.ENDC}"
        if profit_and_loss < 0:
            output_string += f" lost {bcolors.FAIL}"
        else:
            output_string += f" made {bcolors.OKGREEN}"
        output_string += f"{float_to_string(profit_and_loss)}{bcolors.ENDC}"
        output_string += f" on ₡{bcolors.OKCYAN}{float_to_string(spend)}{bcolors.ENDC} spent, APR = "
        output_string += f"{bcolors.OKGREEN}" if annual_percentage_rate > 0 else f"{bcolors.FAIL}"
        output_string += f"{annual_percentage_rate:,.2%}{bcolors.ENDC}"
        output_string += f" ({holding_period_rate:,.2%} in {float_to_string(self.market.time,precision=2)} years)"
        output_string += f", net worth = ₡{bcolors.FAIL}{float_to_string(worth)}{bcolors.ENDC}"
        output_string += f" from {float_to_string(base)} base and {float_to_string(tokens)} tokens at p={price}\n"
        print(output_string)

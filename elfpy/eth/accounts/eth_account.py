"""Empty accounts for engaging with smart contracts"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Any, Generic, Iterable, TypeVar

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from web3 import Web3

from elfpy import check_non_zero
from elfpy.agents.agent import Agent
from elfpy.agents.policies import BasePolicy, NoActionPolicy
from elfpy.markets.hyperdrive import HyperdriveMarket, HyperdriveMarketAction, MarketActionType
from elfpy.types import MarketType, Quantity, TokenType, Trade
from elfpy.wallet.wallet import Long, Short
from elfpy.wallet.wallet_deltas import WalletDeltas


@dataclass()
class EthWallet:
    r"""Stateful variable for storing what is in the agent's wallet

    Arguments
    ----------
    address : HexBytes
        The trader's address.
    balance : Quantity
        The base assets that held by the trader.
    lp_tokens : FixedPoint
        The LP tokens held by the trader.
    longs : Dict[FixedPoint, Long]
        The long positions held by the trader.
    shorts : Dict[FixedPoint, Short]
        The short positions held by the trader.
    borrows : Dict[FixedPoint, Borrow]
        The borrow positions held by the trader.
    """

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes

    # agent identifier
    address: HexBytes

    # fungible
    balance: Quantity = field(default_factory=lambda: Quantity(amount=FixedPoint(0), unit=TokenType.BASE))
    # TODO: Support multiple typed balances:
    #     balance: Dict[TokenType, Quantity] = field(default_factory=dict)
    lp_tokens: FixedPoint = FixedPoint(0)

    # non-fungible (identified by key=mint_time, stored as dict)
    longs: dict[FixedPoint, Long] = field(default_factory=dict)
    shorts: dict[FixedPoint, Short] = field(default_factory=dict)
    withdraw_shares: FixedPoint = FixedPoint(0)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def _update_longs(self, longs: Iterable[tuple[FixedPoint, Long]]) -> None:
        """Helper internal function that updates the data about Longs contained in the Agent's Wallet object

        Arguments
        ----------
        shorts : Iterable[tuple[FixedPoint, Short]]
            A list (or other Iterable type) of tuples that contain a Long object
            and its market-relative mint time
        """
        for mint_time, long in longs:
            if long.balance != FixedPoint(0):
                logging.debug(
                    "agent #%g trade longs, mint_time = %g\npre-trade amount = %s\ntrade delta = %s",
                    self.address,
                    mint_time,
                    self.longs,
                    long,
                )
                if mint_time in self.longs:  #  entry already exists for this mint_time, so add to it
                    self.longs[mint_time].balance += long.balance
                else:
                    self.longs.update({mint_time: long})
            if self.longs[mint_time].balance == FixedPoint(0):
                # Removing the empty borrows allows us to check existance
                # of open longs using `if wallet.longs`
                del self.longs[mint_time]
            if mint_time in self.longs and self.longs[mint_time].balance < FixedPoint(0):
                raise AssertionError(f"ERROR: Wallet balance should be >= 0, not {self.longs[mint_time]}.")

    def _update_shorts(self, shorts: Iterable[tuple[FixedPoint, Short]]) -> None:
        """Helper internal function that updates the data about Shortscontained in the Agent's Wallet object

        Arguments
        ----------
        shorts : Iterable[tuple[FixedPoint, Short]]
            A list (or other Iterable type) of tuples that contain a Short object
            and its market-relative mint time
        """
        for mint_time, short in shorts:
            if short.balance != FixedPoint(0):
                logging.debug(
                    "agent #%g trade shorts, mint_time = %s\npre-trade amount = %s\ntrade delta = %s",
                    self.address,
                    mint_time,
                    self.shorts,
                    short,
                )
                if mint_time in self.shorts:  #  entry already exists for this mint_time, so add to it
                    self.shorts[mint_time].balance += short.balance
                    old_balance = self.shorts[mint_time].balance

                    # if the balance is positive, we are opening a short, therefore do a weighted
                    # mean for the open share price.  this covers an edge case where two shorts are
                    # opened for the same account in the same block.  if the balance is negative, we
                    # don't want to update the open_short_price
                    if short.balance > FixedPoint(0):
                        old_share_price = self.shorts[mint_time].open_share_price
                        self.shorts[mint_time].open_share_price = (
                            short.open_share_price * short.balance + old_share_price * old_balance
                        ) / (short.balance + old_balance)
                else:
                    self.shorts.update({mint_time: short})
            if self.shorts[mint_time].balance == FixedPoint(0):
                # Removing the empty borrows allows us to check existance
                # of open shorts using `if wallet.shorts`
                del self.shorts[mint_time]
            if mint_time in self.shorts and self.shorts[mint_time].balance < FixedPoint(0):
                raise AssertionError(f"ERROR: Wallet balance should be >= 0, not {self.shorts[mint_time]}.")

    def check_valid_wallet_state(self, dictionary: dict | None = None) -> None:
        """Test that all wallet state variables are greater than zero"""
        if dictionary is None:
            dictionary = self.__dict__
        check_non_zero(dictionary)

    def copy(self) -> EthWallet:
        """Returns a new copy of self"""
        return EthWallet(**copy.deepcopy(self.__dict__))

    def update(self, wallet_deltas: WalletDeltas) -> None:
        """Update the agent's wallet in-place

        Arguments
        ----------
        wallet_deltas : AgentDeltas
            The agent's wallet that tracks the amount of assets this agent holds
        """
        # track over time the agent's weighted average spend, for return calculation
        for key, value_or_dict in wallet_deltas.copy().__dict__.items():
            if value_or_dict is None:
                continue
            match key:
                case ["frozen", "no_new_attribs"]:
                    continue
                case ["lp_tokens", "withdraw_shares"]:
                    logging.debug(
                        "agent #%g %s pre-trade = %.0g\npost-trade = %1g\ndelta = %1g",
                        self.address,
                        key,
                        getattr(self, key),
                        getattr(self, key) + value_or_dict,
                        value_or_dict,
                    )
                    self[key] += value_or_dict
                # handle updating a Quantity
                case "balance":
                    logging.debug(
                        "agent #%g %s pre-trade = %.0g\npost-trade = %1g\ndelta = %1g",
                        self.address,
                        key,
                        float(getattr(self, key).amount),
                        float(getattr(self, key).amount + value_or_dict.amount),
                        float(value_or_dict.amount),
                    )
                    getattr(self, key).amount += value_or_dict.amount
                # handle updating a dict, which have mint_time attached
                case "longs":
                    self._update_longs(value_or_dict.items())
                case "shorts":
                    self._update_shorts(value_or_dict.items())
                case _:
                    raise ValueError(f"wallet_{key=} is not allowed.")
            self.check_valid_wallet_state(self.__dict__)


Policy = TypeVar("Policy", bound=BasePolicy)
Market = TypeVar(
    "Market", bound=HyperdriveMarket
)  # TODO: I don't know how to impose that this is a HyperdriveMarket at times, but BaseMarket in general
MarketAction = TypeVar(
    "MarketAction", bound=HyperdriveMarketAction
)  # TODO: should be able to infer this from the market


class EthAgent(LocalAccount, Generic[Policy, Market, MarketAction]):
    r"""Enacts policies on smart contracts and tracks wallet state

    Arguments
    ----------
    policy : Policy
        Elfpy policy for producing agent actions
    private_key : str | None, optional
        Private key for constructing the agent's blockchain wallet.
        If None, then a random private key is created
    """

    def __init__(self, policy: Policy | None = None, private_key: str | None = None):
        """Initialize an agent and wallet account"""
        if policy is None:
            self.policy = NoActionPolicy()
        else:
            self.policy = policy
        if private_key is None:
            account: LocalAccount = Account().create()
            private_key = account._key_obj  # pylint: disable=protected-access
        else:
            account: LocalAccount = Account().from_key(private_key)
        super().__init__(private_key, account)
        self.wallet: EthWallet = EthWallet(
            address=HexBytes(self.address), balance=Quantity(amount=self.policy.budget, unit=TokenType.BASE)
        )

    @property
    def checksum_address(self) -> ChecksumAddress:
        """Return the checksum address of the account"""
        return Web3.to_checksum_address(self.address)

    @property
    def _private_key(self) -> str:
        logging.warning("accessing agent private key")
        return str(self._key_obj)  # pylint: disable=protected-access

    @property
    def liquidation_trades(self) -> list[Trade[MarketAction]]:
        """List of trades that liquidate all open positions

        Returns
        -------
        list[Trade]
            List of trades to execute in order to liquidate positions where applicable
        """
        action_list = []
        for maturity_time, long in self.wallet.longs.items():
            logging.debug("closing long: maturity_time=%g, balance=%s", maturity_time, long)
            if long.balance > 0:
                # TODO: Deprecate the old wallet in favor of this new one
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=MarketActionType.CLOSE_LONG,
                            trade_amount=long.balance,
                            wallet=self.wallet,  # type: ignore
                            maturity_time=maturity_time,
                        ),
                    )
                )
        for maturity_time, short in self.wallet.shorts.items():
            logging.debug("closing short: maturity_time=%g, balance=%s", maturity_time, short.balance)
            if short.balance > 0:
                # TODO: Deprecate the old wallet in favor of this new one
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=MarketActionType.CLOSE_SHORT,
                            trade_amount=short.balance,
                            wallet=self.wallet,  # type: ignore
                            maturity_time=maturity_time,
                        ),
                    )
                )
        if self.wallet.lp_tokens > 0:
            logging.debug("closing lp: lp_tokens=%s", self.wallet.lp_tokens)
            # TODO: Deprecate the old wallet in favor of this new one
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=MarketActionType.REMOVE_LIQUIDITY,
                        trade_amount=self.wallet.lp_tokens,
                        wallet=self.wallet,  # type: ignore
                    ),
                )
            )
        return action_list

    def get_trades(self, market: Market) -> list[Trade[MarketAction]]:
        """Helper function for computing a agent trade

        Arguments
        ----------
        market : Market
            The market on which this agent will be executing trades (MarketActions)

        Returns
        -------
        list[Trade]
            List of Trade type objects that represent the trades to be made by this agent
        """
        # get the action list from the policy
        # TODO: Deprecate the old wallet in favor of this new one
        actions: list[Trade[MarketAction]] = self.policy.action(market, self.wallet)  # type: ignore
        # edit each action in place
        for action in actions:
            if action.market_type == MarketType.HYPERDRIVE and action.market_action.maturity_time is None:
                action.market_action.maturity_time = market.latest_checkpoint_time + market.position_duration.seconds
                if action.market_action.trade_amount <= 0:
                    raise ValueError("Trade amount cannot be zero or negative.")
        return actions


class EthAccount:
    """Web3 account that has helper functions & associated funding source"""

    # TODO: We should be adding more methods to this class.
    # If not, we can delete it at the end of the refactor.
    # pylint: disable=too-few-public-methods

    def __init__(self, agent: Agent | None = None, private_key: str | None = None, extra_entropy: str = "TEST ACCOUNT"):
        """Initialize an account"""
        if private_key is None:
            self.account: LocalAccount = Account().create(extra_entropy=extra_entropy)
        else:
            self.account: LocalAccount = Account().from_key(private_key)
        self._agent = agent

    @property
    def agent(self) -> Agent:
        """Return the elfpy agent object if it exists, otherwise throw an error"""
        if self._agent is None:
            raise AttributeError(f"EthAccount with address {self.account.address} has no Agent member")
        return self._agent

    @property
    def checksum_address(self) -> ChecksumAddress:
        """Return the checksum address of the account"""
        return Web3.to_checksum_address(self.account.address)

    @property
    def _private_key(self) -> str:
        logging.warning("accessing agent private key")
        return str(self.account._private_key)  # pylint: disable=protected-access

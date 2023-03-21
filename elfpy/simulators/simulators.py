"""Simulator class wraps the pricing models and markets for experiment tracking and execution"""
from __future__ import annotations  # types will be strings by default in 3.11

import json
import logging
from dataclasses import dataclass, field, make_dataclass
from typing import TYPE_CHECKING, Optional

import numpy as np
import pandas as pd
from numpy.random._generator import Generator as NumpyGenerator

import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions
import elfpy.agents.wallet as wallet
import elfpy.time as time
import elfpy.types as types
import elfpy.utils.outputs as output_utils

if TYPE_CHECKING:
    from elfpy.agents.agent import Agent
    import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market


@dataclass
class SimulationState:
    r"""Simulator state, updated after each trade

    MarketState, Agent, and Config attributes are added dynamically in Simulator.update_simulation_state()

    .. todo:: change attribute type hints to indicate what list contents should be
    """

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes
    # the name of the pricing model that is used in simulation"
    model_name: list[str] = field(default_factory=list)
    # simulation index
    run_number: list[int] = field(default_factory=list)
    # day index in a given simulation
    day: list[int] = field(default_factory=list)
    # block index in a given simulation
    block_number: list[int] = field(default_factory=list)
    # block index in a given day
    daily_block_number: list[int] = field(default_factory=list)
    # current block time in years
    current_time: list[float] = field(default_factory=list)
    # trade number in a given simulation
    trade_number: list[int] = field(default_factory=list)
    # minimum time discretization for a time step
    time_step_size: list[float] = field(default_factory=list)
    # time lapse between token mint and expiry in years
    position_duration: list[time.StretchedTime] = field(default_factory=list)
    # variable apr on a given day
    current_variable_apr: list[float] = field(default_factory=list)
    # apr of the AMM pool
    fixed_apr: list[float] = field(default_factory=list)
    # price of shares
    spot_price: list[float] = field(default_factory=list)

    def add_dict_entries(self, dictionary: dict) -> None:
        r"""Adds keys & values of input ditionary to the simulation state

        The simulation state is an ever-growing list,
        so each item in this dict is appended to the attribute with a corresponding key.
        If no attribute exists for that key, a new list containing the value is assigned to the attribute

        Parameters
        ----------
        dictionary : dict
            items to be added
        """
        for key, val in dictionary.items():
            if key in ["frozen", "no_new_attribs"]:
                continue
            if hasattr(self, key):
                attribute_state = getattr(self, key)
                attribute_state.append(val)
                setattr(self, key, attribute_state)
            else:
                setattr(self, key, [val])

    def __getitem__(self, key):
        r"""Get object attribute referenced by `key`"""
        return getattr(self, key)

    def __setitem__(self, key, value):
        r"""Set object attribute referenced by `key` to `value`"""
        setattr(self, key, value)


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class Config:
    """Data object for storing user simulation config parameters

    .. todo:: Rename the {trade/redemption}_fee_percent variables so that they doesn't use "percent"
    """

    # lots of configs!
    # pylint: disable=too-many-instance-attributes

    # Temporary
    do_dataframe_states: bool = False

    # Market
    # total size of the market pool (shares)
    target_liquidity: float = field(default=1e6)
    # fraction of pool liquidity
    target_volume: float = field(default=0.01)
    # years since the vault was opened
    init_vault_age: float = field(default=0)

    # TODO: Move this out of config, it should be computed in simulator init based on config values
    # the underlying variable (e.g. from a vault) APR at each time step; the default is overridden in __post_init__
    variable_apr: list[float] = field(default_factory=lambda: [-1])

    # TODO: Move this out of config, it should be computed in simulator init based on config values
    # initial market share price for the vault asset; default is overridden in __post_init__
    init_share_price: float = field(default=-1)

    # AMM
    # Must be "Hyperdrive", or "YieldSpace"
    pricing_model_name: str = field(default="Hyperdrive")
    # LP fee factor (decimal) to charge for trades
    trade_fee_percent: float = field(default=0.05)
    # LP fee factor (decimal) to charge for redemption
    redemption_fee_percent: float = field(default=0.05)
    # desired fixed apr for as a decimal
    target_fixed_apr: float = field(default=0.1)
    # minimum fee percentage (bps)
    floor_fee: float = field(default=0)

    # Simulation
    # durations
    # Text description of the simulation
    title: str = field(default="elfpy simulation")
    # in days; should be <= pool_duration
    num_trading_days: int = field(default=3)
    # agents execute trades each block
    num_blocks_per_day: int = field(default=3)
    # time lapse between token mint and expiry as days
    num_position_days: int = field(default=90)

    # users
    # shuffle order of action (as if random gas paid)
    shuffle_users: bool = field(default=True)
    # list of strings naming user policies
    agent_policies: list = field(default_factory=list)
    # if True, use an initial LP agent to seed pool
    init_lp: bool = field(default=True)

    # vault
    # whether or not to use compounding revenue for the underlying yield source
    compound_variable_apr: bool = field(default=True)

    # logging
    # logging level, as defined by stdlib logging
    log_level: int = field(default=logging.INFO)
    # filename for output logs
    log_filename: str = field(default="simulation")

    # numerical
    # precision of calculations; max is 64
    precision: int = field(default=64)

    # random
    # int to be used for the random seed
    random_seed: int = field(default=1)
    # random number generator used in the simulation
    rng: NumpyGenerator = field(init=False, compare=False)

    def __post_init__(self) -> None:
        r"""init_share_price & rng are a function of other random variables"""
        self.rng = np.random.default_rng(self.random_seed)
        if self.variable_apr == [-1]:  # defaults to [-1] so this should happen right after init
            self.variable_apr = [0.05] * self.num_trading_days
        if self.init_share_price < 0:  # defaults to -1 so this should happen right after init
            self.init_share_price = (1 + self.variable_apr[0]) ** self.init_vault_age
        self.disable_new_attribs()  # disallow new attributes # pylint: disable=no-member # type: ignore

    def __getitem__(self, key) -> None:
        return getattr(self, key)

    def __setattr__(self, attrib, value) -> None:
        #  variable_apr gets set to [-1] on init, then an appropriate value
        #  on post_init. So we need to check after it has been set, and only if
        #  it is not the first time being set.
        if not hasattr(self, attrib) or attrib != "variable_apr":
            super().__setattr__(attrib, value)
        else:  # only check variable apr if it is being reassigned
            super().__setattr__(attrib, value)
            self.check_variable_apr()  # check it after it has been assigned

    def __str__(self) -> str:
        # cls arg tells json how to handle numpy objects and nested dataclasses
        return json.dumps(self.__dict__, sort_keys=True, indent=2, cls=output_utils.CustomEncoder)

    def copy(self) -> Config:
        """Returns a new copy of self"""
        if hasattr(self, "__dataclass_fields__"):
            # TODO: Not sure why lint is claiming that self has no "__dataclass_fields__" member
            # when we're in the conditional
            # pylint: disable=no-member
            return Config(**{key: self[key] for key, value in self.__dataclass_fields__.items() if value.init})
        raise AttributeError("Config was not instantiated & cannot be copied")

    def check_variable_apr(self) -> None:
        r"""Verify that the variable_apr is the right length"""
        if not isinstance(self.variable_apr, list):
            raise TypeError(
                f"ERROR: variable_apr must be of type list, not {type(self.variable_apr)}."
                f"\nhint: it must be set after Config is initialized."
            )
        if len(self.variable_apr) != self.num_trading_days:
            raise ValueError(
                "ERROR: variable_apr must have len equal to num_trading_days = "
                + f"{self.num_trading_days},"
                + f" not {len(self.variable_apr)}"
            )


@dataclass
class RunSimVariables:
    """Simulation state variables that change by run"""

    # incremented each time run_simulation is called
    run_number: int
    # the simulation config
    config: Config
    # initial wallets for the agents
    agent_init: list[wallet.Wallet]
    # initial market state for this simulation run
    market_init: hyperdrive_market.MarketState
    # minimum time discretization for time step in years
    time_step: float
    # time lapse between token mint and expiry in years
    position_duration: time.StretchedTime


@dataclass
class DaySimVariables:
    """Simulation state variables that change by day"""

    # incremented each time run_simulation is called
    run_number: int
    # day index in a given simulation
    day: int
    # variable apr on a given day
    variable_apr: float
    # share price for the underlying vault
    share_price: float


@dataclass
class BlockSimVariables:
    """Simulation state variables that change by block"""

    # incremented each time run_simulation is called
    run_number: int
    # day index in a given simulation
    day: int
    # integer, block index in a given simulation
    block_number: int
    # float, current time in years
    time: float


@dataclass
class TradeSimVariables:
    """Simulation state variables that change by trade"""

    # pylint: disable=too-many-instance-attributes

    # incremented each time run_simulation is called
    run_number: int
    # day index in a given simulation
    day: int
    # block index in a given simulation
    block_number: int
    # trade number in a given simulation
    trade_number: int
    # apr of the AMM pool
    fixed_apr: float
    # price of shares
    spot_price: float
    # trade being executed
    trade_action: types.Trade
    # deltas used to update the market state
    market_deltas: hyperdrive_actions.MarketDeltas
    # address of the agent that is executing the trade
    agent_address: int
    # deltas used to update the market state
    agent_deltas: wallet.Wallet


def simulation_state_aggreagator(constructor):
    """Returns a dataclass that aggregates simulation state attributes"""
    # Wrap the type from the constructor in a list, but keep the name
    attribs = [
        (key, "list[" + val + "]", field(default_factory=list)) for key, val in constructor.__annotations__.items()
    ]

    # Make a new dataclass that has helper functions for appending to the list
    def update(obj, dictionary):
        for key, value in dictionary.items():
            obj.update_item(key, value)

    # The lambda is used because of the self variable -- TODO: can possibly remove?
    # pylint: disable=unnecessary-lambda
    aggregator = make_dataclass(
        constructor.__name__ + "Aggregator",
        attribs,
        namespace={
            "update_item": lambda self, key, value: getattr(self, key).append(value),
            "update": lambda self, dict_like: update(self, dict_like),
        },
    )()
    return aggregator


@dataclass
class NewSimulationState:
    r"""Simulator state that stores Market, Agent, and Config attributes
    The SimulationState has the following external attributes:
        run_updates: pd.DataFrame composed of RunSimVariables
        day_updates: pd.DataFrame composed of DaySimVariables
        block_updates: pd.DataFrame composed of BlockSimVariables
        trade_updates: pd.DataFrame composed of TradeSimVariables
    """

    def __post_init__(self) -> None:
        r"""Construct empty dataclasses with appropriate attributes for each state variable type"""
        self._run_updates = simulation_state_aggreagator(RunSimVariables)
        self._day_updates = simulation_state_aggreagator(DaySimVariables)
        self._block_updates = simulation_state_aggreagator(BlockSimVariables)
        self._trade_updates = simulation_state_aggreagator(TradeSimVariables)

    def update(
        self,
        run_vars: Optional[RunSimVariables] = None,
        day_vars: Optional[DaySimVariables] = None,
        block_vars: Optional[BlockSimVariables] = None,
        trade_vars: Optional[TradeSimVariables] = None,
    ) -> None:
        r"""Add a row to the state dataframes that contains the latest variables"""
        if run_vars is not None:
            self._run_updates.update(run_vars.__dict__)
        if day_vars is not None:
            self._day_updates.update(day_vars.__dict__)
        if block_vars is not None:
            self._block_updates.update(block_vars.__dict__)
        if trade_vars is not None:
            self._trade_updates.update(trade_vars.__dict__)

    @property
    def run_updates(self) -> pd.DataFrame:
        r"""Converts internal list of state values into a dataframe"""
        return pd.DataFrame.from_dict(self._run_updates.__dict__)

    @property
    def day_updates(self) -> pd.DataFrame:
        r"""Converts internal list of state values into a dataframe"""
        return pd.DataFrame.from_dict(self._day_updates.__dict__)

    @property
    def block_updates(self) -> pd.DataFrame:
        r"""Converts internal list of state values into a dataframe"""
        return pd.DataFrame.from_dict(self._block_updates.__dict__)

    @property
    def trade_updates(self) -> pd.DataFrame:
        r"""Converts internal list of state values into a dataframe"""
        return pd.DataFrame.from_dict(self._trade_updates.__dict__)

    @property
    def combined_dataframe(self) -> pd.DataFrame:
        r"""Returns a single dataframe that combines the run, day, block, and trade variables
        The merged dataframe has the same number of rows as self.trade_updates,
        with entries in the smaller dataframes duplicated accordingly
        """
        return self.trade_updates.merge(self.block_updates.merge(self.day_updates.merge(self.run_updates)))


class Simulator:
    r"""Stores environment variables & market simulation outputs for AMM experimentation

    Member variables include input settings, random variable ranges, and simulation outputs.
    To be used in conjunction with the Market and PricingModel classes
    """

    # TODO: set up member (dataclass?) object that owns attributes instead of so many individual instance attributes
    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        config: Config,
        market: hyperdrive_market.Market,
        block_time: time.BlockTime,
    ):
        # User specified variables
        self.config = config.copy()
        logging.info("%s", self.config)
        self.market = market
        self.block_time = block_time
        self.set_rng(config.rng)
        self.config.check_variable_apr()
        # NOTE: lint error false positives: This message may report object members that are created dynamically,
        # but exist at the time they are accessed.
        self.config.freeze()  # type: ignore
        self.agents: dict[int, Agent] = {}

        # Simulation variables
        self.run_number = 0
        self.day = 0
        self.block_number = 0
        self.daily_block_number = 0
        seconds_in_a_day = 86400
        self.time_between_blocks = seconds_in_a_day / self.config.num_blocks_per_day
        self.trade_number = 0
        if self.config.do_dataframe_states:
            self.new_simulation_state = NewSimulationState()
        self.simulation_state = SimulationState()

    def set_rng(self, rng: NumpyGenerator) -> None:
        r"""Assign the internal random number generator to a new instantiation
        This function is useful for forcing identical trade volume and directions across simulation runs

        Parameters
        ----------
        rng : Generator
            Random number generator, constructed using np.random.default_rng(seed)
        """
        if not isinstance(rng, NumpyGenerator):
            raise TypeError(f"rng type must be a random number generator, not {type(rng)}.")
        self.rng = rng

    def get_simulation_state_string(self) -> str:
        r"""Returns a formatted string containing all of the Simulation class member variables

        Returns
        -------
        state_string : str
            Simulator class member variables (keys & values in self.__dict__) cast to a string, separated by a new line
        """
        if self.config.do_dataframe_states:
            return str(self.new_simulation_state)
        strings = [
            f"{attribute} = {value}"
            for attribute, value in self.__dict__.items()
            if attribute not in ("simulation_state", "rng")
        ]
        return "\n".join(strings)

    @property
    def time_step(self) -> float:
        r"""Returns minimum time increment in years

        Returns
        -------
        float
            time between blocks, which is computed as 1 / blocks_per_year
        """
        blocks_per_year = 365 * self.config.num_blocks_per_day
        return 1 / blocks_per_year

    def add_agents(self, agent_list: list[Agent]) -> None:
        r"""Append the agents and simulation_state member variables

        If trades have already happened (as indicated by self.trade_number), then empty wallet states are
        prepended to the simulation_state for each new agent so that the state can still easily be converted into
        a pandas dataframe.

        Parameters
        ----------
        agent_list : list[Agent]
            A list of instantiated Agent objects
        """
        for agent in agent_list:
            self.agents.update({agent.wallet.address: agent})
            for key in agent.wallet.get_state_keys():
                setattr(self.simulation_state, key, [None] * self.trade_number)

    def collect_and_execute_trades(self, last_block_in_sim: bool = False) -> None:
        r"""Get trades from the agent list, execute them, and update states

        Parameters
        ----------
        last_block_in_sim : bool
            If True, indicates if the current set of trades are occuring on the final block in the simulation
        """
        if self.config.shuffle_users:
            if last_block_in_sim:
                agent_ids: list[int] = self.rng.permutation(  # shuffle wallets except init_lp
                    [key for key in self.agents if key > 0]  # exclude init_lp before shuffling
                ).tolist()
                if self.config.init_lp:
                    agent_ids.append(0)  # add init_lp so that they're always last
            else:
                agent_ids = self.rng.permutation(
                    list(self.agents)
                ).tolist()  # random permutation of keys (agent wallet addresses)
        else:  # we are in a deterministic mode
            agent_ids = list(self.agents)[::-1] if last_block_in_sim else list(self.agents)
        # Collect trades from all of the agents.
        # TODO: This API causes a unnecessary double loop; first over agents, then trades,
        #       then we loop again over all trades. In the future we want to simulate something like
        #       the mempool, which has all agent trades. But for now it would be better if we could
        #       get all of the block's trades without an extra loop.
        trades = self.collect_trades(agent_ids, liquidate=last_block_in_sim)
        # Execute the trades
        self.execute_trades(trades)

    def collect_trades(self, agent_ids: list[int], liquidate: bool = False) -> list[tuple[int, types.Trade]]:
        r"""Collect trades from a set of provided agent IDs.

        Parameters
        ----------
        agent_ids: list[int]
            A list of agent IDs. These IDs must correspond to agents that are
            registered in the simulator.

        liquidate: bool
            If true, have agents collect their liquidation trades. Otherwise, agents collect their normal trades.

        Returns
        -------
        list[tuple[int, Trade]]
            A list of trades associated with specific agents.
        """
        agents_and_trades: list[tuple[int, types.Trade]] = []
        for agent_id in agent_ids:
            agent = self.agents[agent_id]
            if liquidate:
                logging.debug("Collecting liquiditation trades for market closure")
                trades = agent.get_liquidation_trades(self.market)
            else:
                trades = agent.get_trades(self.market)
            agents_and_trades.extend((agent_id, trade) for trade in trades)
        return agents_and_trades

    def execute_trades(self, agent_actions: list[tuple[int, types.Trade]]) -> None:
        r"""Execute a list of trades associated with agents in the simulator.

        Parameters
        ----------
        trades : list[tuple[int, list[Trade]]]
            A list of agent trades. These will be executed in order.
            for trade in trades:
                trade[0] is the agent wallet address;
                trade[1].market is the trade market;
                trade[1].trade is the action
        """
        for trade in agent_actions:
            # TODO: In a follow-up PR we will decompose the trade into the
            # agent ID, market, and market action before sending the info off to the correct market
            action_details = (trade[0], trade[1].trade)
            agent_id, agent_deltas, market_deltas = self.market.perform_action(action_details)
            print(f"{trade[1].trade=}\n")
            self.agents[agent_id].log_status_report()
            # TODO: need to log deaggregated trade informaiton, i.e. trade_deltas
            # issue #215
            self.update_simulation_state()
            if self.config.do_dataframe_states:
                self.new_simulation_state.update(
                    trade_vars=TradeSimVariables(
                        self.run_number,
                        self.day,
                        self.block_number,
                        self.trade_number,
                        self.market.fixed_apr,
                        self.market.spot_price,
                        trade[1].trade,
                        market_deltas,
                        agent_id,
                        agent_deltas,
                    )
                )
            self.trade_number += 1

    def run_simulation(self, liquidate_on_end: bool = True) -> None:
        r"""Run the trade simulation and update the output state dictionary

        This helper function advances time and orchestrates trades.
        Typically, the simulation executes as follows:

        .. code-block::
           for day in num_trading_days:
               # update simulation state day variables
               for block in num_blocks_per_day:
                   # update simulation state block variables
                   for agent in agents:
                       for trade in agent.trades:
                           # do_trade
                           # update simulation state trade variables

        Parameters
        ----------
        liquidate_on_end : bool
            if True, liquidate trades when the simulation is complete
        """
        last_block_in_sim = False
        if self.config.do_dataframe_states:
            self.new_simulation_state.update(
                run_vars=RunSimVariables(
                    run_number=self.run_number,
                    config=self.config,
                    agent_init=[agent.wallet for agent in self.agents.values()],
                    market_init=self.market.market_state,
                    time_step=self.time_step,
                    position_duration=self.market.position_duration,
                )
            )
        for day in range(self.config.num_trading_days):
            self.day = day
            self.market.market_state.variable_apr = self.config.variable_apr[self.day]
            # Vault return can vary per day, which sets the current price per share
            if self.day > 0:  # Update only after first day (first day set to init_share_price)
                if self.config.compound_variable_apr:  # Apply return to latest price (full compounding)
                    price_multiplier = self.market.market_state.share_price
                else:  # Apply return to starting price (no compounding)
                    price_multiplier = self.market.market_state.init_share_price
                delta = hyperdrive_actions.MarketDeltas(
                    d_share_price=(
                        self.market.market_state.variable_apr  # current day's apy
                        / 365  # convert annual yield to daily
                        * price_multiplier
                    )
                )
                self.market.update_market(delta)
            if self.config.do_dataframe_states:
                self.new_simulation_state.update(
                    day_vars=DaySimVariables(
                        self.run_number,
                        self.day,
                        self.market.market_state.variable_apr,
                        self.market.market_state.share_price,
                    )
                )
            for daily_block_number in range(self.config.num_blocks_per_day):
                self.daily_block_number = daily_block_number
                last_block_in_sim = (self.day == self.config.num_trading_days - 1) and (
                    self.daily_block_number == self.config.num_blocks_per_day - 1
                )
                liquidate = last_block_in_sim and liquidate_on_end
                if self.config.do_dataframe_states:
                    self.new_simulation_state.update(
                        block_vars=BlockSimVariables(self.run_number, self.day, self.block_number, self.block_time.time)
                    )
                self.collect_and_execute_trades(liquidate)
                logging.debug(
                    "day = %g, daily_block_number = %g, block_time = %g\n",
                    self.day,
                    self.daily_block_number,
                    self.block_time.time,
                )
                if not last_block_in_sim:
                    self.block_time.tick(self.time_step)
                    self.block_number += 1
        # simulation has ended
        for agent in self.agents.values():
            agent.log_final_report(self.market)

    def update_simulation_state(self) -> None:
        r"""Increment the list for each key in the simulation_state output variable

        .. todo:: This gets duplicated in notebooks when we make the pandas dataframe.
            Instead, the simulation_state should be a dataframe.
            issue #215
        """
        # pylint: disable=too-many-statements
        self.simulation_state.model_name.append(self.market.pricing_model.model_name())
        self.simulation_state.run_number.append(self.run_number)
        self.simulation_state.day.append(self.day)
        self.simulation_state.block_number.append(self.block_number)
        self.simulation_state.daily_block_number.append(self.daily_block_number)
        self.simulation_state.current_time.append(self.block_time.time)
        self.simulation_state.trade_number.append(self.trade_number)
        self.simulation_state.time_step_size.append(self.time_step)
        self.simulation_state.position_duration.append(self.market.position_duration)
        self.simulation_state.fixed_apr.append(self.market.fixed_apr)
        self.simulation_state.current_variable_apr.append(self.config.variable_apr[self.day])
        self.simulation_state.add_dict_entries({"config." + key: val for key, val in self.config.__dict__.items()})
        self.simulation_state.add_dict_entries(self.market.market_state.__dict__)
        for agent in self.agents.values():
            self.simulation_state.add_dict_entries(agent.wallet.get_state(self.market))
        # TODO: This is a HACK to prevent test_sim from failing on market shutdown
        # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
        if self.market.market_state.share_reserves > 0:  # there is money in the market
            self.simulation_state.spot_price.append(self.market.spot_price)
        else:
            self.simulation_state.spot_price.append(np.nan)

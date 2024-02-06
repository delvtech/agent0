from __future__ import annotations

import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Any

import gymnasium as gym
import numpy as np
from fixedpointmath import FixedPoint
from gymnasium import spaces

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.hyperdrive.policies import PolicyZoo

# Global suppression of warnings, TODO fix
warnings.filterwarnings("ignore")


class Actions(Enum):
    Sell = 0
    Buy = 1


class Positions(Enum):
    Short = 0
    Long = 1

    def opposite(self):
        return Positions.Short if self == Positions.Long else Positions.Long


# TODO there's lots of things here that can be abstracted to share code between this and full_hyperdrive_env
class SimpleHyperdriveEnv(gym.Env):
    """
    A simple hyperdrive environment that allows for 2 positions, long and short
    """

    @dataclass(kw_only=True)
    class Config:
        """The configuration for SimpleHyperdriveEnv."""

        # How to render the environment
        # TODO figure out what this does
        render_mode: str | None = None

        # RL Bot Config
        # The constant trade amounts for longs and shorts
        rl_agent_budget: FixedPoint = FixedPoint(1_000_000)
        trade_base_amount: FixedPoint = FixedPoint(1000)
        reward_scale: float = 1e-17
        window_size: int = 10
        episode_length: int = 200

        # Other bots config
        num_random_bots: int = 3
        random_bot_budget: FixedPoint = FixedPoint(1_000_000)

    # Defines allowed render modes and fps
    metadata = metadata = {"render_modes": ["human"], "render_fps": 4}

    def __init__(
        self,
        gym_config: Config,
    ):
        """Initializes the environment"""
        # TODO parameterize these in the gym config
        local_chain_config = LocalChain.Config(block_timestamp_interval=3600)
        self.chain = LocalChain(local_chain_config)
        initial_pool_config = InteractiveHyperdrive.Config()
        self.interactive_hyperdrive = InteractiveHyperdrive(self.chain, initial_pool_config)

        # Define the rl bot
        self.rl_bot = self.interactive_hyperdrive.init_agent(base=gym_config.rl_agent_budget, name="rl_bot")
        # Define the random bots
        self.random_bots = [
            self.interactive_hyperdrive.init_agent(
                base=gym_config.random_bot_budget,
                policy=PolicyZoo.random,
                # TODO set the seed per random bot here for reproducability
                policy_config=PolicyZoo.random.Config(),
                name="random_bot_" + str(i),
            )
            for i in range(gym_config.num_random_bots)
        ]

        # Save a snapshot of initial conditions for resets
        self.chain.save_snapshot()

        assert gym_config.render_mode is None or gym_config.render_mode in self.metadata["render_modes"]
        self.render_mode = gym_config.render_mode

        self.gym_config = gym_config

        # This action space encompasses buy and sell of bonds based on the current taken position
        # Following https://github.com/AminHP/gym-anytrading/tree/master
        # This binary action space with a position state variable results in one of the 4 following trades:
        # - If the current position is short and the agent's action is to buy, the environment will
        #     close the short position and open a long position. The current position is then set to long.
        # - If the current position is long and the agent's action is to buy, this is noop (i.e., hold long position)
        # - If the current position is long and the agent's action is to sell, the environment will
        #   close the long position and open a short position. The current position is then set to short.
        # - If the current position is short and the agent's action is to sell, this is noop (i.e., hold short position)
        self.action_space = spaces.Discrete(len(Actions))

        # The space of observations from the environment
        # This is a timeseries of window_size samples of the spot price and the share price
        # TODO add more data for rl bot input
        self.observation_space = spaces.Box(low=0, high=1e10, shape=(self.gym_config.window_size, 2), dtype=np.float64)

        # For a more complex environment:

        # The space of allowed actions to take
        # Following https://github.com/AminHP/gym-mtsim
        # These actions are encoded into a 1d vector of continuous values
        # This is due to not all algorithms supporting dict or multidimention box actions

        # Here, these actions are for 3 types of trades: longs, shorts, and LP,
        # each encoded as an array of length max_positions + 2
        # For a given type of trade, the elements are interpreted as
        # [
        #    probability of closing order 1,
        #    probability of closing order 2,
        #    ...
        #    probability of closing order max_positions,
        #    probability of holding or creating a new order,
        #    volume of the new order
        # ]
        # The last two define the probability of creating a new order (or no op), with the volume of the new order
        # Probabilities are in logit space to ensure probability values are in range [0, 1]

        # self.action_space.spaces.Box(
        #    low=-1e2, high=1e2, dtype=np.float64, shape=(3 * (self.max_positions + 2))
        # )  # (longs, shorts, lp) -> close_order_i(logit), hold(logit), volume)
        # INF = 1e10
        # self.observation_space = spaces.Dict({
        #    'balance': spaces.Box(low=-INF, high=INF, shape=(1,), dtype=np.float64),
        #    'equity': spaces.Box(low=-INF, high=INF, shape=(1,), dtype=np.float64),
        #    'margin': spaces.Box(low=-INF, high=INF, shape=(1,), dtype=np.float64),
        #    'features': spaces.Box(low=-INF, high=INF, shape=self.features_shape, dtype=np.float64),
        #    'orders': spaces.Box(
        #        low=-INF, high=INF, dtype=np.float64,
        #        shape=(len(self.trading_symbols), self.symbol_max_orders, 3)
        #    )  # symbol, order_i -> [entry_price, volume, profit]
        # })

        # episode variables
        self._position = None
        self._open_position = None
        self._obs_buffer = np.zeros((self.gym_config.window_size, 2), dtype=np.float64)
        # The amount of base lost/gained in one step
        self._base_delta: float = 0.0
        self._step_count = 0

    def reset(
        self, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Resets the environment to an initial internal state.
        Arguments
        ---------
        seed: int | None
            The seed to initialize the random generator to pass for each bot
        options: dict[str, Any] | None
            A dictionary of options to pass to the environment
        Returns
        -------
        tuple[ObsType, dict[str, Any]]
            The observation and info from the environment
        """

        # TODO do random seeds properly
        super().reset(seed=seed)

        # TODO randomize pool parameters here
        # We can do this by deploying a new pool
        # For now, we use a single pool with default parameters
        # and use snapshotting to reset

        # Load the snapshot for initial conditions
        self.chain.load_snapshot()

        # Reset internal member variables
        self._position = None
        self._obs_buffer = np.zeros((self.gym_config.window_size, 2), dtype=np.float64)
        self._base_delta = 0.0
        self._step_count = 0

        # Get first observation and info
        observation = self._get_observation()
        info = self._get_info()

        return observation, info

    def do_trade(self) -> bool:
        assert self._position is not None
        terminated = False

        agent_wallet = self.rl_bot.wallet

        self._position = self._position.opposite()
        if self._position == Positions.Long:
            # Close short position (if exists), open long
            if len(agent_wallet.shorts) > 0:
                # Sanity check, only one short open
                assert len(agent_wallet.shorts) == 1
                short = list(agent_wallet.shorts.values())[0]
                # Close short
                try:
                    # print(f"Closing short {short.maturity_time} with balance {short.balance}")
                    trade_result = self.rl_bot.close_short(short.maturity_time, short.balance)
                    self._base_delta += trade_result.base_amount.scaled_value
                except Exception as err:
                    print(f"Warning: Failed to close short: {err=}")
                    # Terminate if error
                    terminated = True
            # Open a long position
            try:
                # print(f"Opening long with base amount {self.gym_config.long_base_amount}")
                trade_result = self.rl_bot.open_long(self.gym_config.trade_base_amount)
                self._base_delta -= trade_result.base_amount.scaled_value
            except Exception as err:
                print(f"Warning: Failed to open long: {err=}")
                # Terminate if error
                terminated = True

        elif self._position == Positions.Short:
            # Close long position (if exists), open short
            if len(agent_wallet.longs) > 0:
                # Sanity check, only one long open
                assert len(agent_wallet.longs) == 1
                long = list(agent_wallet.longs.values())[0]
                # Close long
                try:
                    # print(f"Closing long {long.maturity_time} with balance {long.balance}")
                    trade_result = self.rl_bot.close_long(long.maturity_time, long.balance)
                    self._base_delta += trade_result.base_amount.scaled_value
                except Exception as err:
                    print(f"Warning: Failed to close long: {err=}")
                    # Terminate if error
                    terminated = True
            # Open a short position
            try:
                # print(f"Opening short with bond amount {self.gym_config.short_bond_amount}")
                # TODO calc max short can fail with low short values
                max_short = self.interactive_hyperdrive.interface.calc_max_short(
                    self.gym_config.trade_base_amount, self.interactive_hyperdrive.interface.current_pool_state
                )
                trade_result = self.rl_bot.open_short(max_short)
                self._base_delta -= trade_result.base_amount.scaled_value
            except Exception as err:
                print(f"Warning: Failed to open short: {err=}")
                # Terminate if error
                terminated = True
        return terminated

    def step(self, action: Actions) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        """Takes a step in the the environment.

        Arguments
        ---------
        action: ActType
            An action provided by the agent to update the environment state

        Returns
        -------
        observation: ObsType
            An element of the environment's observation_space.
        reward: float
            Reward for taking the action.
        terminated: bool
            Whether the agent reaches the terminal state, which can be positive or negative.
            If true, user needs to call reset
        truncated: bool
            Whether the truncation condition outside the scope of the MDP is satisfied,
            e.g., timelimit, or agent going out of bounds.
            If true, user needs to call reset
        info: dict[str, Any]
            Contains auxiliary diagnostic information for debugging, learning, logging.
        """

        # Run other bots
        for random_bot in self.random_bots:
            try:
                random_bot.execute_policy_action()
            except Exception as err:
                print(f"Warning: Failed to execute random bot: {err=}")
                # We ignore errors in random bots
                continue

        # Initial condition, ensure first trade always goes through
        if self._position is None:
            if action == Actions.Buy.value:
                self._position = Positions.Short
            elif action == Actions.Sell.value:
                self._position = Positions.Long
            else:
                raise ValueError

        # Reset base delta per trade
        self._base_delta = 0.0

        # print(f"Action: {action}")
        trade = False
        if (action == Actions.Buy.value and self._position == Positions.Short) or (
            action == Actions.Sell.value and self._position == Positions.Long
        ):
            trade = True

        terminated = False
        if trade:
            # Trading updates self._base_delta variable
            terminated = self.do_trade()

        observation = self._get_observation()
        info = self._get_info()
        step_reward = self._calculate_reward()

        self._step_count += 1
        truncated = False

        if self._step_count > self.gym_config.episode_length:
            truncated = True

        # TODO when does the episode stop?
        return observation, step_reward, terminated, truncated, info

    def _get_info(self) -> dict:
        # TODO return aux info here
        return {}

    def _get_observation(self) -> np.ndarray:
        # Get the spot price and share price of hyperdrive
        pool_state_df = self.interactive_hyperdrive.get_pool_state(coerce_float=True)
        self._obs_buffer = (
            pool_state_df[["lp_share_price", "spot_price"]].iloc[-self.gym_config.window_size :].to_numpy()
        )
        # If not enough data points, we left pad with zeros
        if self._obs_buffer.shape[0] < self.gym_config.window_size:
            pad_size = self.gym_config.window_size - self._obs_buffer.shape[0]
            self._obs_buffer = np.pad(self._obs_buffer, ((pad_size, 0), (0, 0)))

        # Sanity check
        assert self._obs_buffer.shape == (self.gym_config.window_size, 2)

        return self._obs_buffer

    def _calculate_reward(self) -> float:
        # The total delta for this episode
        raw_reward = self._base_delta

        # Testing only using base difference for reward,
        # ignoring open positions

        ## TODO these functions should be in hyperdrive_sdk
        # assert self._account is not None
        # current_block = self.web3.eth.get_block_number()
        # if self._open_position and self._position == Positions.Long:
        #    fn_args = (
        #        self._open_position.maturity_time_seconds,
        #        self._open_position.bond_amount.scaled_value,
        #        0,
        #        self._account.checksum_address,
        #        True,
        #    )
        #    try:
        #        position_pnl = smart_contract_preview_transaction(
        #            self.hyperdrive_contract,
        #            self._account.checksum_address,
        #            "closeLong",
        #            *fn_args,
        #            block_identifier=current_block,
        #        )
        #        raw_reward += position_pnl["value"]
        #    except Exception as err:
        #        print(f"Warning: Failed to preview close long: {err=}")

        # elif self._open_position and self._position == Positions.Short:
        #    fn_args = (
        #        self._open_position.maturity_time_seconds,
        #        self._open_position.bond_amount.scaled_value,
        #        0,
        #        self._account.checksum_address,
        #        True,
        #    )
        #    try:
        #        position_pnl = smart_contract_preview_transaction(
        #            self.hyperdrive_contract,
        #            self._account.checksum_address,
        #            "closeShort",
        #            *fn_args,
        #            block_identifier=current_block,
        #        )
        #        raw_reward += position_pnl["value"]
        #    except Exception as err:
        #        print(f"Warning: Failed to preview close short: {err=}")

        return raw_reward * self.gym_config.reward_scale

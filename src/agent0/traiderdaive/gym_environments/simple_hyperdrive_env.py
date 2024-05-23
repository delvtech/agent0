"""A simple hyperdrive rl gym environment."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Any

import gymnasium as gym
import numpy as np
from fixedpointmath import FixedPoint
from gymnasium import spaces

from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive
from agent0.core.hyperdrive.policies import PolicyZoo

# Global suppression of warnings, TODO fix
warnings.filterwarnings("ignore")


class Actions(Enum):
    """The actions that can be taken in the environment. These actions map directly to what the RL bot outputs."""

    SHORT = 0
    LONG = 1


class CurrentPosition(Enum):
    """The positions that the agent holds. These positions are one step behind an action.

    For example:
    - If the action is to long and the current position is a short, then the trader will close their
    short position (if it exists) and open a long position, and swap the current position to Long.

    - If the action is to short and the current position is a long, then the trader will close their
    long position (if it exists) and open a short position, and swap the current position to Short.

    - Otherwise, take no action
    """

    SHORT = 0
    LONG = 1

    def opposite(self):
        """Swaps the current position to the other position.

        Returns
        -------
        Positions
            The other position
        """
        return CurrentPosition.SHORT if self == CurrentPosition.LONG else CurrentPosition.LONG


# TODO there's lots of things here that can be abstracted to share code between this and full_hyperdrive_env
class SimpleHyperdriveEnv(gym.Env):
    """A simple hyperdrive environment that allows for 2 positions, long and short."""

    # pylint: disable=too-many-instance-attributes

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
        reward_scale: float = 1
        window_size: int = 10
        episode_length: int = 200

        # Other bots config
        num_random_bots: int = 3
        num_random_hold_bots: int = 3
        random_bot_budget: FixedPoint = FixedPoint(1_000_000)

    # Defines allowed render modes and fps
    metadata = {"render_modes": ["human"], "render_fps": 4}

    def __init__(
        self,
        gym_config: Config,
    ):
        """Initializes the environment"""
        # TODO parameterize these in the gym config
        local_chain_config = LocalChain.Config(block_timestamp_interval=3600)
        self.chain = LocalChain(local_chain_config)
        initial_pool_config = LocalHyperdrive.Config()
        self.interactive_hyperdrive = LocalHyperdrive(self.chain, initial_pool_config)

        # Define the rl bot
        self.rl_bot = self.chain.init_agent(
            base=gym_config.rl_agent_budget, eth=FixedPoint(100), pool=self.interactive_hyperdrive, name="rl_bot"
        )
        # Define the random bots
        self.random_bots = [
            self.chain.init_agent(
                base=gym_config.random_bot_budget,
                eth=FixedPoint(100),
                pool=self.interactive_hyperdrive,
                policy=PolicyZoo.random,
                # TODO set the seed per random bot here for reproducability
                policy_config=PolicyZoo.random.Config(),
                name="random_bot_" + str(i),
            )
            for i in range(gym_config.num_random_bots)
        ]

        self.random_bots.extend(
            [
                self.chain.init_agent(
                    base=gym_config.random_bot_budget,
                    eth=FixedPoint(100),
                    pool=self.interactive_hyperdrive,
                    policy=PolicyZoo.random_hold,
                    # TODO set the seed per random bot here for reproducability
                    policy_config=PolicyZoo.random_hold.Config(
                        trade_chance=FixedPoint("0.8"),
                        max_open_positions=1000,
                    ),
                    name="random_bot_" + str(i),
                )
                for i in range(gym_config.num_random_hold_bots)
            ]
        )

        # Save a snapshot of initial conditions for resets
        self.chain.save_snapshot()

        assert gym_config.render_mode is None or gym_config.render_mode in self.metadata["render_modes"]
        self.render_mode = gym_config.render_mode

        self.gym_config = gym_config

        # This action space encompasses longing and shorting bonds based on the current taken position
        # Following https://github.com/AminHP/gym-anytrading/tree/master
        # This binary action space with a position state variable results in one of the 4 following trades:
        # - If the current position is short and the agent's action is to long, the environment will
        #     close the short position and open a long position. The current position is then set to long.
        # - If the current position is long and the agent's action is to long, this is noop
        #     (i.e., hold long position)
        # - If the current position is long and the agent's action is to short, the environment will
        #     close the long position and open a short position. The current position is then set to short.
        # - If the current position is short and the agent's action is to short, this is noop
        #     (i.e., hold short position)
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
        self._current_position = None
        self._obs_buffer = np.zeros((self.gym_config.window_size, 2), dtype=np.float64)
        self._prev_pnl: float = 0.0
        self._step_count = 0

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Resets the environment to an initial internal state.

        Arguments
        ---------
        seed: int | None
            The seed to initialize the random generator to pass for each bot
        options: dict[str, Any] | None
            Additional information to specify how the environment is reset (optional,
            depending on the specific environment)

        Returns
        -------
        tuple[np.ndarray, dict[str, Any]]
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
        self._current_position = None
        self._obs_buffer = np.zeros((self.gym_config.window_size, 2), dtype=np.float64)
        self._prev_pnl = 0.0
        self._step_count = 0

        # Get first observation and info
        observation = self._get_observation()
        info = self._get_info()

        return observation, info

    def do_trade(self) -> bool:
        """Performs a trade in the environment. This function swaps the current position the agent holds,
        i.e., if the position is now long, the agent will close the open short and open a new long, and
        if the position is now short, the agent will close the open long and open a new short.

        Returns
        -------
        bool
            Whether the agent reaches the terminal state due to a failed trade.
        """
        assert self._current_position is not None
        terminated = False

        agent_wallet = self.rl_bot.get_wallet()

        self._current_position = self._current_position.opposite()
        if self._current_position == CurrentPosition.LONG:
            # Close short position (if exists), open long
            if len(agent_wallet.shorts) > 0:
                # Sanity check, only one short open
                assert len(agent_wallet.shorts) == 1
                short = list(agent_wallet.shorts.values())[0]
                # Close short
                try:
                    self.rl_bot.close_short(short.maturity_time, short.balance)
                except Exception as err:  # pylint: disable=broad-except
                    # TODO use logging here
                    print(f"Warning: Failed to close short: {err=}")
                    # Terminate if error
                    terminated = True
            # Open a long position
            try:
                self.rl_bot.open_long(self.gym_config.trade_base_amount)
            except Exception as err:  # pylint: disable=broad-except
                print(f"Warning: Failed to open long: {err=}")
                # Terminate if error
                terminated = True

        elif self._current_position == CurrentPosition.SHORT:
            # Close long position (if exists), open short
            if len(agent_wallet.longs) > 0:
                # Sanity check, only one long open
                assert len(agent_wallet.longs) == 1
                long = list(agent_wallet.longs.values())[0]
                # Close long
                try:
                    self.rl_bot.close_long(long.maturity_time, long.balance)
                except Exception as err:  # pylint: disable=broad-except
                    print(f"Warning: Failed to close long: {err=}")
                    # Terminate if error
                    terminated = True
            # Open a short position
            try:
                # TODO calc max short can fail with low short values
                max_short = self.interactive_hyperdrive.interface.calc_max_short(
                    self.gym_config.trade_base_amount, self.interactive_hyperdrive.interface.current_pool_state
                )
                self.rl_bot.open_short(max_short)
            except Exception as err:  # pylint: disable=broad-except
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
        tuple[np.ndarray, float, bool, bool, dict[str, Any]]
            Contains the following

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
            except Exception as err:  # pylint: disable=broad-except
                print(f"Warning: Failed to execute random bot: {repr(err)}")
                # We ignore errors in random bots
                continue

        # Initial condition, ensure first trade always goes through
        if self._current_position is None:
            if action == Actions.LONG.value:
                self._current_position = CurrentPosition.SHORT
            elif action == Actions.SHORT.value:
                self._current_position = CurrentPosition.LONG
            else:
                raise ValueError

        trade = False
        if (action == Actions.LONG.value and self._current_position == CurrentPosition.SHORT) or (
            action == Actions.SHORT.value and self._current_position == CurrentPosition.LONG
        ):
            trade = True

        terminated = False
        truncated = False
        if trade:
            truncated = self.do_trade()

        observation = self._get_observation()
        info = self._get_info()
        step_reward = self._calculate_reward()

        self._step_count += 1

        if self._step_count > self.gym_config.episode_length:
            terminated = True

        # TODO when does the episode stop?
        return observation, step_reward, terminated, truncated, info

    def _get_info(self) -> dict:
        # TODO return aux info here
        return {}

    def _get_observation(self) -> np.ndarray:
        # Get the spot price and share price of hyperdrive
        pool_state_df = self.interactive_hyperdrive.get_pool_info(coerce_float=True)
        self._obs_buffer = (
            pool_state_df[["lp_share_price", "spot_price"]].iloc[-self.gym_config.window_size :].to_numpy()
        )
        # If not enough data points, we left pad with zeros
        if self._obs_buffer.shape[0] < self.gym_config.window_size:
            pad_size = self.gym_config.window_size - self._obs_buffer.shape[0]
            self._obs_buffer = np.pad(self._obs_buffer, pad_width=((pad_size, 0), (0, 0)))

        # Sanity check
        assert self._obs_buffer.shape == (self.gym_config.window_size, 2)

        return self._obs_buffer

    def _calculate_reward(self) -> float:
        # The total delta for this episode

        current_wallet = self.interactive_hyperdrive.get_positions()
        # Filter by rl bot
        rl_bot_wallet = current_wallet[current_wallet["wallet_address"] == self.rl_bot.address]
        # The rl_bot_wallet shows the pnl of all positions
        # Sum across all positions
        # TODO one option here is to only look at base positions instead of sum across all positions.
        # TODO handle the case where pnl calculation doesn't return a number
        # when you can't close the position
        total_pnl = float(rl_bot_wallet["pnl"].sum())

        # reward is in units of base
        # We use the change in pnl as the reward
        reward = total_pnl - self._prev_pnl
        self._prev_pnl = total_pnl

        return reward * self.gym_config.reward_scale

    def render(self) -> None:
        """Renders the environment. No rendering available for hyperdrive env."""
        return None

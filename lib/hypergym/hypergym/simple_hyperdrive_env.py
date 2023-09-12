from __future__ import annotations

from enum import Enum
from typing import Any

import gymnasium as gym
import numpy as np
from ethpy import EthConfig, build_eth_config
from gymnasium import spaces


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

    # Required attribute for environment defining allowed render modes
    metadata = {"render_modes": ["human"], "render_fps": 3}

    def __init__(self, gym_config: dict[str, Any], eth_config: EthConfig | None = None, render_mode: str | None = None):
        """Initializes the environment"""

        if eth_config is None:
            # Load parameters from env vars if they exist
            eth_config = build_eth_config()
        self.eth_config = eth_config

        assert render_mode is None or render_mode in self.metadata["render-modes"]
        self.render_mode = render_mode

        # Get config variables
        # The constant base amount to open a long
        self.long_base_amount = gym_config["long_base_amount"]
        # The constant bond amount to open a short
        self.short_bond_amount = gym_config["short_bond_amount"]
        # Number of blocks (current and previous blocks) returned as a gym observation
        self.window_size = gym_config["window_size"]

        # Defines environment attributes

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
        self.observation_space = spaces.Box(low=0, high=1e10, shape=(self.window_size, 2), dtype=np.float64)

        # episode variables
        self._position = None

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
        super().reset(seed=seed, options=options)
        # We use the env's random number generator for anything random, i.e.,
        # self.np_random
        self.action_space.seed(int((self.np_random.uniform(0, seed if seed is not None else 1))))

        self._position = None

        # TODO
        observation = self._get_observation()
        info = self._get_info()

        return observation, info

    def step(self, action: Actions) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        """Resets the environment to an initial internal state.

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
        step_reward = self._calculate_reward(action)

        # Initial condition, ensure first trade always goes through
        if self._position is None:
            if action == Actions.Buy.value:
                self._position = Positions.Short
            elif action == Actions.Sell.value:
                self._position = Positions.Long
            else:
                raise ValueError

        trade = False
        if (action == Actions.Buy.value and self._position == Positions.Short) or (
            action == Actions.Sell.value and self._position == Positions.Long
        ):
            trade = True

        if trade:
            self._position = self._position.opposite()
            # TODO do trade based on position
            if self._position == Positions.Long:
                # Close short position (if exists), open long
                pass
            elif self._position == Positions.Short:
                # Close long position, open short
                pass

        observation = self._get_observation()
        info = self._get_info()

        return observation, step_reward, False, False, info

    def _get_info(self) -> dict:
        # TODO return aux info here
        return {}

    def _get_observation(self) -> np.ndarray:
        # TODO get the spot price and share price of hyperdrive
        return np.zeros((self.window_size, 2))

    def _calculate_reward(self, action: Actions) -> float:
        # TODO calculate the pnl of closing the current position
        return 0.0

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
from scipy.special import expit

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.hyperdrive.policies import PolicyZoo

# Global suppression of warnings, TODO fix
warnings.filterwarnings("ignore")


class TradeTypes(Enum):
    LONG = 0
    SHORT = 1


# TODO there's lots of things here that can be abstracted to share code between this and simple_hyperdrive_env
class FullHyperdriveEnv(gym.Env):
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
        max_trade_amount: FixedPoint = FixedPoint(10_000)
        max_positions_per_type: int = 10
        reward_scale: float = 1
        window_size: int = 10
        episode_length: int = 200
        # The thresholds for opening and closing orders
        open_threshold: FixedPoint = FixedPoint(0.5)
        close_threshold: FixedPoint = FixedPoint(0.5)

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
        initial_pool_config = InteractiveHyperdrive.Config()
        self.interactive_hyperdrive = InteractiveHyperdrive(self.chain, initial_pool_config)

        # Define the rl bot
        self.rl_bot = self.interactive_hyperdrive.init_agent(base=gym_config.rl_agent_budget, name="rl_bot")
        # Define the random bots
        self.random_bots = [
            self.interactive_hyperdrive.init_agent(
                base=gym_config.random_bot_budget,
                policy=PolicyZoo.random,
                # TODO set the seed per random bot here for reproducibility
                policy_config=PolicyZoo.random.Config(),
                name="random_bot_" + str(i),
            )
            for i in range(gym_config.num_random_bots)
        ]

        self.random_bots.extend(
            [
                self.interactive_hyperdrive.init_agent(
                    base=gym_config.random_bot_budget,
                    policy=PolicyZoo.random_hold,
                    # TODO set the seed per random bot here for reproducibility
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

        # The space of allowed actions to take
        # Following https://github.com/AminHP/gym-mtsim
        # These actions are encoded into a 1d vector of continuous values
        # This is due to not all algorithms supporting dict or multidimention box actions

        # Here, these actions are for 2 types of trades: longs, shorts
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

        # The final 4 fields specify LP positions, interpreted as
        # [
        #    probability of adding liquidity,
        #    volume of add liquidity,
        #    probability of removing liquidity,
        #    volume of remove liquidity
        # ]

        # (longs, shorts) -> close_order_i(logit), new_order(logit), volume)
        # (lp) -> add_lp_order(logit), volume_add_lp, remove_lp_order(logit), volume_remove_lp)
        self.action_space = spaces.Box(
            low=-1e2, high=1e2, dtype=np.float64, shape=(len(TradeTypes) * (gym_config.max_positions_per_type + 2) + 4,)
        )

        # Observation space is
        # TODO add more features
        # Pool Features: spot price, lp share price
        # TODO use pnl instead of value
        # Long Orders: trade type, order_i -> [entry_spot_price, volume, value, normalized_time_to_maturity]
        # Short Orders: trade type, order_i -> [entry_spot_price, volume, value, normalized_time_to_maturity]
        # LP: -> [volume, value]
        # Here, orders_i is a direct mapping to agent.wallet
        # Note normalize_time_to_maturity will always be 0 for LP positions
        self.features_shape = (2,)
        INF = 1e10
        self.observation_space = spaces.Dict(
            {
                # "balance": spaces.Box(low=-INF, high=INF, shape=(1,), dtype=np.float64),
                # "equity": spaces.Box(low=-INF, high=INF, shape=(1,), dtype=np.float64),
                # "margin": spaces.Box(low=-INF, high=INF, shape=(1,), dtype=np.float64),
                "pool_features": spaces.Box(low=-INF, high=INF, shape=self.features_shape, dtype=np.float64),
                "long_orders": spaces.Box(
                    low=-INF, high=INF, dtype=np.float64, shape=(gym_config.max_positions_per_type * 4,)
                ),
                "short_orders": spaces.Box(
                    low=-INF, high=INF, dtype=np.float64, shape=(gym_config.max_positions_per_type * 4,)
                ),
                "lp_orders": spaces.Box(low=-INF, high=INF, dtype=np.float64, shape=(2,)),
                # Note normalize_time_to_maturity will always be 0 for LP positions
            }
        )

        # episode variables
        self._current_position = None
        self._prev_pnl: float = 0.0
        self._step_count = 0

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
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
        self._prev_pnl = 0.0
        self._step_count = 0

        # Get first observation and info
        observation = self._get_observation()
        info = self._get_info()

        return observation, info

    def _apply_action(self, action: np.ndarray) -> bool:
        action = action.reshape((len(TradeTypes), self.gym_config.max_positions_per_type + 2))
        long_short_actions = action[:-4]
        lp_actions = action[-4:]
        for trade_type in TradeTypes:
            symbol_action = long_short_actions[trade_type.value, :]
            close_orders_logit = symbol_action[:-2]
            hold_logit = symbol_action[-2]
            volume = symbol_action[-1]

            # We convert logit space to probability space
            close_orders_probability = expit(close_orders_logit)
            open_probability = expit(hold_logit)
            # While volume isn't strictly a probability, we interpret it as a value between 0 and 1
            # where 0 is no volume and 1 is max trade amount
            volume_adjusted = expit(volume) * self.gym_config.max_trade_amount

            # Handle closing orders
            # The index of orders here is from oldest to newest
            # TODO if we want the rl bot to explicitly learn how to close orders based on
            # the orders input feature, we can shuffle the order of closing orders
            # TODO we threshold probabilities here, another option is to sample from a distribution.
            # However, we may want the actual RL bots to handle that, and keep the environment deterministic.
            orders_to_close_index = np.nonzero(close_orders_probability > self.gym_config.close_threshold)
            pass
        return False

    def step(self, action: np.ndarray) -> tuple[dict[str, np.ndarray], float, bool, bool, dict[str, Any]]:
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

        truncated = self._apply_action(action)

        # Run other bots
        for random_bot in self.random_bots:
            try:
                random_bot.execute_policy_action()
            except Exception as err:  # pylint: disable=broad-except
                print(f"Warning: Failed to execute random bot: {err=}")
                # We ignore errors in random bots
                continue

        observation = self._get_observation()
        info = self._get_info()
        step_reward = self._calculate_reward()

        self._step_count += 1
        terminated = False

        if self._step_count > self.gym_config.episode_length:
            terminated = True

        # TODO when does the episode stop?
        return observation, step_reward, terminated, truncated, info

    def _get_info(self) -> dict:
        # TODO return aux info here
        return {}

    def _get_pool_features(self) -> np.ndarray:
        # Get the spot price and share price of hyperdrive
        pool_state_df = self.interactive_hyperdrive.get_pool_state(coerce_float=True)

        _obs_buffer = pool_state_df[["lp_share_price", "spot_price"]].iloc[-self.gym_config.window_size :].to_numpy()
        # If not enough data points, we left pad with zeros
        if _obs_buffer.shape[0] < self.gym_config.window_size:
            pad_size = self.gym_config.window_size - _obs_buffer.shape[0]
            _obs_buffer = np.pad(_obs_buffer, pad_width=((pad_size, 0), (0, 0)))
        assert _obs_buffer.shape == (self.gym_config.window_size, 2)
        return _obs_buffer

    def _get_observation(self) -> dict[str, np.ndarray]:
        # Get the spot price and share price of hyperdrive
        pool_state_df = self.interactive_hyperdrive.get_pool_state(coerce_float=True)
        out_obs = {}
        out_obs["pool_features"] = self._get_pool_features()

        current_wallet = self.interactive_hyperdrive.get_current_wallet()
        # Filter for rl bot
        rl_bot_wallet = current_wallet[current_wallet["wallet_address"] == self.rl_bot.checksum_address]
        # Build observation for all positions
        pass

        # Sanity check
        return out_obs

    def _calculate_reward(self) -> float:
        # The total delta for this episode

        current_wallet = self.interactive_hyperdrive.get_current_wallet()
        # Filter by rl bot
        rl_bot_wallet = current_wallet[current_wallet["wallet_address"] == self.rl_bot.checksum_address]
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

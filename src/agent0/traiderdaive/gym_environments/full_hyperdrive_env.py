"""A hyperdrive rl gym environment."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Any

import gymnasium as gym
import numpy as np
import pandas as pd
from fixedpointmath import FixedPoint
from gymnasium import spaces
from scipy.special import expit

from agent0.core.hyperdrive.interactive import ILocalChain, ILocalHyperdrive
from agent0.core.hyperdrive.policies import PolicyZoo

# Global suppression of warnings, TODO fix
warnings.filterwarnings("ignore")


class TradeTypes(Enum):
    """Enum denoting between long and short indices"""

    LONG = 0
    SHORT = 1


# TODO there's lots of things here that can be abstracted to share code between this and simple_hyperdrive_env
class FullHyperdriveEnv(gym.Env):
    """A simple hyperdrive environment that allows for 2 positions, long and short."""

    # pylint: disable=too-many-instance-attributes

    @dataclass(kw_only=True)
    class Config:
        """The configuration for FullHyperdriveEnv."""

        # How to render the environment
        # TODO figure out what this does
        render_mode: str | None = None

        # RL Bot Config
        # The constant trade amounts for longs and shorts
        rl_agent_budget: FixedPoint = FixedPoint(1_000_000)
        max_trade_amount: FixedPoint = FixedPoint(1_000)
        max_positions_per_type: int = 10
        reward_scale: float = 1
        window_size: int = 10
        episode_length: int = 200
        # The threshold for the probability of opening and closing orders
        open_threshold: float = 0.5
        close_threshold: float = 0.5

        # Other bots config
        num_random_bots: int = 2
        num_random_hold_bots: int = 2
        random_bot_budget: FixedPoint = FixedPoint(1_000_000)

    # Defines allowed render modes and fps
    metadata = {"render_modes": ["human"], "render_fps": 4}

    def __init__(
        self,
        gym_config: Config,
    ):
        """Initializes the environment"""
        # TODO parameterize these in the gym config
        local_chain_config = ILocalChain.Config(block_timestamp_interval=3600)
        self.chain = ILocalChain(local_chain_config)
        initial_pool_config = ILocalHyperdrive.Config()
        self.interactive_hyperdrive = ILocalHyperdrive(self.chain, initial_pool_config)

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
        #    add liquidity volume,
        #    probability of removing liquidity,
        #    add liquidity volume,
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
        # TODO add bookkeeping for entry spot price
        # Long Orders: trade type, order_i -> [volume, value, normalized_time_remaining]
        # Short Orders: trade type, order_i -> [volume, value, normalized_time_remaining]
        # LP: -> [volume, value]
        # Here, orders_i is a direct mapping to agent.wallet
        # Note normalize_time_to_maturity will always be 0 for LP positions
        # Removing timestamp and block number from pool state
        self.num_pool_features = len(self.interactive_hyperdrive.get_pool_state(coerce_float=True).columns) - 2
        inf = 1e10
        self.observation_space = spaces.Dict(
            {
                # "balance": spaces.Box(low=-INF, high=INF, shape=(1,), dtype=np.float64),
                # "equity": spaces.Box(low=-INF, high=INF, shape=(1,), dtype=np.float64),
                # "margin": spaces.Box(low=-INF, high=INF, shape=(1,), dtype=np.float64),
                "pool_features": spaces.Box(low=-inf, high=inf, shape=(self.num_pool_features,), dtype=np.float64),
                "long_orders": spaces.Box(
                    low=-inf, high=inf, dtype=np.float64, shape=(gym_config.max_positions_per_type * 3,)
                ),
                "short_orders": spaces.Box(
                    low=-inf, high=inf, dtype=np.float64, shape=(gym_config.max_positions_per_type * 3,)
                ),
                "lp_orders": spaces.Box(low=-inf, high=inf, dtype=np.float64, shape=(2,)),
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
        # TODO
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-nested-blocks

        long_short_actions = action[:-4]
        long_short_actions = long_short_actions.reshape((len(TradeTypes), self.gym_config.max_positions_per_type + 2))
        close_long_short_actions = long_short_actions[:, :-2]
        open_long_short_actions = long_short_actions[:, -2:]

        # Get current wallet positions
        # We need exact decimals here to avoid rounding errors
        rl_bot_wallet = self._get_rl_wallet_positions(coerce_float=False)

        # TODO should likely try and handle these trades as fast as possible
        # Otherwise action could lag behind observation, especially with accelerated time
        # One option is to don't do accelerated time, but manually advance time per step
        # after all bot actions

        # The RL bot handles trades in this order:
        # (1) Close long tokens
        # (2) Close short tokens
        # (2) Open long tokens
        # (4) Open short tokens
        # (5) Add liqidity
        # (6) Remove liquidity
        # (7) Redeem withdrawal shares

        # Closing trades
        for trade_type in TradeTypes:
            close_orders_probability = expit(close_long_short_actions[trade_type.value, :])

            # Handle closing orders
            # The index of orders here is from oldest to newest
            # TODO if we want the rl bot to explicitly learn how to close orders based on
            # the orders input feature, we can shuffle the order of closing orders
            # TODO we threshold probabilities here, another option is to sample from a distribution.
            # However, we may want the actual RL bots to handle that, and keep the environment deterministic.
            orders_to_close_index = np.nonzero(close_orders_probability > self.gym_config.close_threshold)[0]

            # TODO Close orders
            trade_positions = rl_bot_wallet[rl_bot_wallet["base_token_type"] == trade_type.name]
            # Ensure positions are sorted from oldest to newest
            trade_positions = trade_positions.sort_values("maturity_time")
            num_trade_positions = len(trade_positions)

            # Filter orders to close to be only the number of trade positions
            orders_to_close_index = orders_to_close_index[orders_to_close_index < num_trade_positions]
            positions_to_close = trade_positions.iloc[orders_to_close_index]

            # Close positions
            try:
                for _, position_to_close in positions_to_close.iterrows():
                    if trade_type == TradeTypes.LONG:
                        self.rl_bot.close_long(
                            maturity_time=int(position_to_close["maturity_time"]),
                            bonds=FixedPoint(position_to_close["position"]),
                        )
                    elif trade_type == TradeTypes.SHORT:
                        self.rl_bot.close_short(
                            maturity_time=int(position_to_close["maturity_time"]),
                            bonds=FixedPoint(position_to_close["position"]),
                        )
            except Exception as err:  # pylint: disable=broad-except
                # TODO use logging here
                print(f"Warning: Failed to close trade: {err=}")
                # Terminate if error
                return True

        # Get current wallet positions again after closing trades
        rl_bot_wallet = self._get_rl_wallet_positions(coerce_float=False)

        # Open trades
        for trade_type in TradeTypes:
            # Only open trades if we haven't maxed out positions
            trade_positions = rl_bot_wallet[rl_bot_wallet["base_token_type"] == trade_type.name]
            num_trade_positions = len(trade_positions)
            if num_trade_positions < self.gym_config.max_positions_per_type:
                new_order_probability = expit(open_long_short_actions[trade_type.value, 0])
                # While volume isn't strictly a probability, we interpret it as a value between 0 and 1
                # where 0 is no volume and 1 is max trade amount
                volume_adjusted = (
                    FixedPoint(expit(open_long_short_actions[trade_type.value, 1])) * self.gym_config.max_trade_amount
                )

                # Opening orders
                try:
                    if new_order_probability > self.gym_config.open_threshold:
                        # If the wallet has enough money
                        if volume_adjusted <= self.rl_bot.wallet.balance.amount:
                            if trade_type == TradeTypes.LONG:
                                self.rl_bot.open_long(base=volume_adjusted)
                            elif trade_type == TradeTypes.SHORT:
                                max_short = self.interactive_hyperdrive.interface.calc_max_short(
                                    volume_adjusted,
                                    self.interactive_hyperdrive.interface.current_pool_state,
                                )
                                self.rl_bot.open_short(bonds=max_short)
                # Base exception here to catch rust errors
                except BaseException as err:  # pylint: disable=broad-except
                    # TODO use logging here
                    print(f"Warning: Failed to open trade: {err=}")
                    # Terminate if error
                    return True

        # LP actions
        lp_actions_expit = expit(action[-4:])
        add_lp_probability = lp_actions_expit[0]
        add_lp_volume = FixedPoint(lp_actions_expit[1]) * self.gym_config.max_trade_amount
        remove_lp_probability = lp_actions_expit[2]
        remove_lp_volume = FixedPoint(lp_actions_expit[3]) * self.gym_config.max_trade_amount

        try:
            if add_lp_probability > self.gym_config.open_threshold:
                self.rl_bot.add_liquidity(add_lp_volume)
            if (
                remove_lp_probability > self.gym_config.close_threshold
                and remove_lp_volume <= self.rl_bot.wallet.lp_tokens
            ):
                self.rl_bot.remove_liquidity(remove_lp_volume)
            # Always try and remove withdrawal shares
            if self.rl_bot.wallet.withdraw_shares > 0:
                # TODO error handling or check when withdrawal shares are not withdrawable
                self.rl_bot.redeem_withdraw_share(self.rl_bot.wallet.withdraw_shares)
        except Exception as err:  # pylint: disable=broad-except
            # TODO use logging here
            print(f"Warning: Failed to LP: {err=}")
            # Terminate if error
            return True

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

    def _get_rl_wallet_positions(self, coerce_float: bool) -> pd.DataFrame:
        current_wallet = self.interactive_hyperdrive.get_current_wallet(coerce_float=coerce_float)
        # Filter for rl bot
        rl_bot_wallet = current_wallet[current_wallet["wallet_address"] == self.rl_bot.checksum_address]
        return rl_bot_wallet

    def _get_observation(self) -> dict[str, np.ndarray]:
        # Get the latest pool state feature from the db
        pool_state_df = self.interactive_hyperdrive.get_pool_state(coerce_float=True)
        pool_state_columns = [c for c in pool_state_df.columns if c not in ("timestamp", "block_number")]
        pool_state_df = pool_state_df[pool_state_columns].iloc[-1].astype(float)

        out_obs = {}
        out_obs["pool_features"] = pool_state_df.values

        # Observation data uses floats
        rl_bot_wallet = self._get_rl_wallet_positions(coerce_float=True)

        position_duration = self.interactive_hyperdrive.config.position_duration
        # We convert timestamp to epoch time here
        # We keep negative values for time past maturity
        rl_bot_wallet["normalized_time_remaining"] = (
            rl_bot_wallet["maturity_time"] - (rl_bot_wallet["timestamp"].astype(int) / int(1e9))
        ) / position_duration

        long_orders = rl_bot_wallet[rl_bot_wallet["base_token_type"] == "LONG"]
        # Ensure data is the same as the action space
        long_orders = long_orders.sort_values("maturity_time")
        long_orders = long_orders[["position", "pnl", "normalized_time_remaining"]].values.flatten()

        short_orders = rl_bot_wallet[rl_bot_wallet["base_token_type"] == "LONG"]
        # Ensure data is the same as the action space
        short_orders = short_orders.sort_values("maturity_time")
        short_orders = short_orders[["position", "pnl", "normalized_time_remaining"]].values.flatten()

        lp_orders = rl_bot_wallet[rl_bot_wallet["base_token_type"] == "LP"]
        lp_orders = lp_orders[["position", "pnl"]].values.flatten()

        # TODO can also add other features, e.g., opening spot price
        # Long Orders: trade type, order_i -> [volume, value, normalized_time_remaining]
        # Short Orders: trade type, order_i -> [volume, value, normalized_time_remaining]
        out_obs["long_orders"] = np.zeros(self.gym_config.max_positions_per_type * 3)
        out_obs["short_orders"] = np.zeros(self.gym_config.max_positions_per_type * 3)
        # LP: -> [volume, value]
        out_obs["lp_orders"] = np.zeros(2)

        # Add data to static size arrays
        out_obs["long_orders"][: len(long_orders)] = long_orders
        out_obs["short_orders"][: len(short_orders)] = short_orders
        out_obs["lp_orders"][: len(lp_orders)] = lp_orders

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

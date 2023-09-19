from __future__ import annotations

import asyncio
import logging
import os
import warnings
from enum import Enum
from typing import Any

import eth_utils
import gymnasium as gym
import numpy as np
from agent0 import initialize_accounts
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import (
    async_transact_and_parse_logs,
    create_and_fund_user_account,
    fund_agents,
    get_agent_accounts,
    trade_if_new_block,
)
from chainsync.analysis import calc_spot_price
from eth_typing import BlockNumber
from ethpy import EthConfig, build_eth_config
from ethpy.base import smart_contract_preview_transaction
from ethpy.hyperdrive import (
    HyperdriveAddresses,
    fetch_hyperdrive_address_from_url,
    get_hyperdrive_config,
    get_hyperdrive_pool_info,
    get_web3_and_hyperdrive_contracts,
)
from gymnasium import spaces

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

    # Required attribute for environment defining allowed render modes
    metadata = {"render_modes": ["human"], "render_fps": 3}

    def __init__(
        self,
        env_config: EnvironmentConfig,
        agent_config: list[AgentConfig],
        gym_config: dict[str, Any],
        eth_config: EthConfig | None = None,
        contract_addresses: HyperdriveAddresses | None = None,
        render_mode: str | None = None,
    ):
        """Initializes the environment"""

        # Set up connection to the chain

        if eth_config is None:
            # Load parameters from env vars if they exist
            eth_config = build_eth_config()

        # Get addresses either from artifacts url defined in eth_config or from contract_addresses
        if contract_addresses is None:
            contract_addresses = fetch_hyperdrive_address_from_url(
                os.path.join(eth_config.ARTIFACTS_URL, "addresses.json")
            )

        self.env_config = env_config
        self.eth_config = eth_config
        self.contract_addresses = contract_addresses
        self.agent_config = agent_config
        self.agent_env_file = "hyperdrive_env.account.env"

        # Get web3 and contracts
        self.web3, self.base_contract, self.hyperdrive_contract = get_web3_and_hyperdrive_contracts(
            eth_config, contract_addresses
        )

        assert render_mode is None or render_mode in self.metadata["render-modes"]
        self.render_mode = render_mode

        # Get config variables
        # The constant base amount to open a long
        self.long_base_amount = gym_config["long_base_amount"]
        # The constant bond amount to open a short
        self.short_bond_amount = gym_config["short_bond_amount"]
        # Scaling for reward
        self.reward_scale = gym_config["reward_scale"]
        # Number of blocks (current and previous blocks) returned as a gym observation
        self.window_size = gym_config["window_size"]
        # Length of one episode for RL training
        self.episode_length = gym_config["episode_length"]

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
        self._obs_buffer = np.zeros((self.window_size, 2), dtype=np.float64)
        self._account = None
        # The amount of base lost/gained in one step
        self._base_delta = 0
        self._last_executed_block = 0
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

        # If there is an open position, close it
        self.do_trade(close_only=True)

        # super().reset(seed=seed, options=options)

        # Build accounts env var
        # This function writes a user defined env file location.
        # If it doesn't exist, create it based on agent_config
        # (If develop is False, will clean exit and print instructions on how to fund agent)
        # If it does exist, read it in and use it
        account_key_config = initialize_accounts(
            self.agent_config, env_file=self.agent_env_file, random_seed=self.env_config.random_seed, develop=True
        )

        # exposing the user account for debugging purposes
        user_account = create_and_fund_user_account(self.eth_config, account_key_config, self.contract_addresses)
        fund_agents(
            user_account, self.eth_config, account_key_config, self.contract_addresses
        )  # uses env variables created above as inputs

        rng = np.random.default_rng()
        self.agent_accounts = get_agent_accounts(
            self.web3,
            self.agent_config,
            account_key_config,
            self.base_contract,
            self.hyperdrive_contract.address,
            rng,
        )

        # Look for the no_action agent and bind that account to this env
        account_idx = [i for i, a in enumerate(self.agent_config) if a.policy.__name__ == "NoActionPolicy"]
        assert len(account_idx) == 1
        self._account = self.agent_accounts[account_idx[0]]

        # We use the env's random number generator for anything random, i.e.,
        # self.np_random
        # self.action_space.seed(int((self.np_random.uniform(0, seed if seed is not None else 1))))

        self._position = None
        self._open_position = None
        self._obs_buffer = np.zeros((self.window_size, 2), dtype=np.float64)
        self._last_executed_block = BlockNumber(0)
        self._base_delta = 0
        self._step_count = 0

        observation = self._get_observation()
        info = self._get_info()

        return observation, info

    def do_trade(self, close_only=False):
        # Do nothing if no position open and we're doing cleanup
        if close_only:
            if self._position is None:
                return False

        assert self._position is not None
        assert self._account is not None

        terminated = False
        self._position = self._position.opposite()
        if self._position == Positions.Long:
            # Close short position (if exists), open long
            if self._open_position is not None:
                # Close short
                fn_args = (
                    self._open_position.maturity_time_seconds,
                    self._open_position.bond_amount.scaled_value,
                    0,
                    self._account.checksum_address,
                    True,
                )
                try:
                    trade_result = asyncio.run(
                        async_transact_and_parse_logs(
                            self.web3, self.hyperdrive_contract, self._account, "closeShort", *fn_args
                        )
                    )
                    self._base_delta += trade_result.base_amount.scaled_value
                except Exception as err:
                    print(f"Warning: Failed to close short: {err=}")
                    terminated = True

            if not close_only:
                # Open long
                fn_args = (
                    self.long_base_amount,
                    0,
                    self._account.checksum_address,
                    True,
                )

                try:
                    self._open_position = asyncio.run(
                        async_transact_and_parse_logs(
                            self.web3, self.hyperdrive_contract, self._account, "openLong", *fn_args
                        )
                    )
                    self._base_delta -= self._open_position.base_amount.scaled_value
                except Exception as err:
                    print(f"Warning: Failed to open long: {err=}")
                    terminated = True

        elif self._position == Positions.Short:
            # Close long position (if exists), open short
            if self._open_position is not None:
                # Close long
                fn_args = (
                    self._open_position.maturity_time_seconds,
                    self._open_position.bond_amount.scaled_value,
                    0,
                    self._account.checksum_address,
                    True,
                )
                try:
                    trade_result = asyncio.run(
                        async_transact_and_parse_logs(
                            self.web3, self.hyperdrive_contract, self._account, "closeLong", *fn_args
                        )
                    )
                    self._base_delta += trade_result.base_amount.scaled_value
                except Exception as err:
                    print(f"Warning: Failed to close long: {err=}")
                    terminated = True

            if not close_only:
                # Open short
                max_deposit = eth_utils.currency.MAX_WEI
                fn_args = (
                    self.short_bond_amount,
                    max_deposit,
                    self._account.checksum_address,
                    True,
                )
                try:
                    self._open_position = asyncio.run(
                        async_transact_and_parse_logs(
                            self.web3, self.hyperdrive_contract, self._account, "openShort", *fn_args
                        )
                    )
                    self._base_delta -= -self._open_position.base_amount.scaled_value
                except Exception as err:
                    print(f"Warning: Failed to open short: {err=}")
                    terminated = True
        return terminated

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

        # Run other bots
        self._last_executed_block = trade_if_new_block(
            self.web3,
            self.hyperdrive_contract,
            self.agent_accounts,
            self.env_config.halt_on_errors,
            self._last_executed_block,
        )

        assert self._account is not None

        # Initial condition, ensure first trade always goes through
        if self._position is None:
            if action == Actions.Buy.value:
                self._position = Positions.Short
            elif action == Actions.Sell.value:
                self._position = Positions.Long
            else:
                raise ValueError

        # Reset base delta for this step
        self._base_delta = 0.0

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

        if self._step_count > self.episode_length:
            truncated = True

        # TODO when does the episode stop?
        return observation, step_reward, terminated, truncated, info

    def _get_info(self) -> dict:
        # TODO return aux info here
        return {}

    def _get_observation(self) -> np.ndarray:
        # Get the spot price and share price of hyperdrive
        current_block = self.web3.eth.get_block_number()
        pool_info = None
        pool_config = None
        retry_err = None
        for _ in range(10):
            try:
                pool_info = get_hyperdrive_pool_info(self.web3, self.hyperdrive_contract, current_block)
                # TODO gather pool config outside of the obs loop
                pool_config = get_hyperdrive_config(self.hyperdrive_contract)
                break
            except Exception as err:
                retry_err = err
                logging.warning(f"Warning: Failed to get pool info, retrying: {err=}")

        if ((pool_info is None) or (pool_config is None)) and retry_err is not None:
            raise retry_err

        assert pool_info is not None
        assert pool_config is not None

        # TODO calculate spot price
        new_spot_price = calc_spot_price(
            pool_info["shareReserves"],
            pool_info["bondReserves"],
            pool_config["initialSharePrice"],
            pool_config["invTimeStretch"],
        )
        new_share_price = pool_info["sharePrice"]
        # Cycle buffer
        self._obs_buffer[:-1, :] = self._obs_buffer[1:, :]
        # Update last entry
        self._obs_buffer[-1, 0] = new_spot_price
        self._obs_buffer[-1, 1] = new_share_price

        return self._obs_buffer

    def _calculate_reward(self) -> float:
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

        return raw_reward * self.reward_scale

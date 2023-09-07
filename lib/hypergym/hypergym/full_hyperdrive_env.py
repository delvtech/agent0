from typing import Any
import gymnasium as gym
from gymnasium import spaces


class FullHyperdriveEnv(gym.Env):
    metadata = {"render_modes": ["ansi"], "render_fps": 4}

    def __init__(self, config: dict[str|Any], render_mode: str | None = None):
        """Initializes the environment"""

        # Defines environment attributes

        # Custom configurations for environment
        # The maximum number of open positions overall
        self.max_positions = config["max_positions"]

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
        # The last two 
        self.action_space = spaces.Discrete(4)

        # The space of observations from the environment
        self.observation_space = spaces.Dict(
            {
                "agent_wallet": spaces.Box(0, size=1, shape(2,), dtype=int),
                "pool_info": spaces.Box(0, size=1, shape(2,), dtype=int),
            }
        )

        # The range of rewards, defaults to -inf to inf
        # self.reward_range = ...

        assert render_mode is None or render_mode in self.metadata["render-modes"]
        self.render_mode = render_mode


        pass

    def step(self, action: ActType) -> tuple[ObsType, float, bool, bool, dict[str, Any]]:
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
        pass

    def reset(self, seed: int | None = None, options: dict[str, Any] | None = None) -> tuple[ObsType, dict[str, Any]]:
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
        super().reset(seed=seed)

        # We use the env's random number generator for anything random, i.e.,
        # self.np_random
        pass

    def render(self) -> RenderFrame | list[RenderFrame] | None:
        """Computes the redner frames as specified by render_mode

        Returns
        -------
        RenderFrame | list[RenderFrame] | None
            For ansi render modes, returns a string

        """
        pass

    def close(self) => None:
        """Closes the environment"""
        pass

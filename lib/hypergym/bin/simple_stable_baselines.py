import logging
import os

import gymnasium as gym
import hypergym  # This import is needed since this is what's registering the env
import numpy as np
from agent0.base.config import AgentConfig, Budget, EnvironmentConfig
from agent0.base.policies import BasePolicies
from agent0.hyperdrive.policies import HyperdrivePolicies
from fixedpointmath import FixedPoint
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.results_plotter import load_results, ts2xy

# Stable baselines repo: https://github.com/DLR-RM/stable-baselines3
# The limiting factors of what algorithms you can use depend on the action space
# Since the simple hyperdrive env has discrete actions, below is the list of
# available algorithms we can use:
# ARS, A2C, DQN, HER, PPO, QR-DQN, RecurrentPPO, TRPO, Maskable PPO

# The more complicated hyperdrive has continuous action spaces (i.e., Box), and can use the
# following algorithms:
# ARS, A2C, DDPG, HER, PPO, RecurrentPPO, SAC, TD3, TQC, TRPO

gym_config = {
    "long_base_amount": int(1e12),
    "short_bond_amount": int(1e12),
    "reward_scale": 1e-12,
    "window_size": 10,
    "episode_length": 100,
}

# Define config for chain env
# Build environment config
env_config = EnvironmentConfig(
    delete_previous_logs=False,
    halt_on_errors=False,
    log_filename="rl_random_trade_log",
    log_level=logging.INFO,
    log_stdout=True,
    random_seed=1234,
    username="rl_random_trade",
)

agent_config: list[AgentConfig] = [
    AgentConfig(
        policy=HyperdrivePolicies.random_agent,
        number_of_agents=3,
        slippage_tolerance=FixedPoint("0.0001"),
        base_budget_wei=Budget(
            mean_wei=FixedPoint(5_000).scaled_value,  # 5k base
            std_wei=FixedPoint(1_000).scaled_value,  # 1k base
            min_wei=1,  # 1 WEI base
            max_wei=FixedPoint(100_000).scaled_value,  # 100k base
        ),
        eth_budget_wei=Budget(min_wei=FixedPoint(1).scaled_value, max_wei=FixedPoint(1).scaled_value),
        init_kwargs={"trade_chance": FixedPoint("0.8")},
    ),
    AgentConfig(
        policy=HyperdrivePolicies.long_louie,
        number_of_agents=0,
        base_budget_wei=Budget(
            mean_wei=FixedPoint(5_000).scaled_value,  # 5k base
            std_wei=FixedPoint(1_000).scaled_value,  # 1k base
            min_wei=1,  # 1 WEI base
            max_wei=FixedPoint(100_000).scaled_value,  # 100k base
        ),
        eth_budget_wei=FixedPoint(1).scaled_value,  # 1 base
        init_kwargs={"trade_chance": FixedPoint("0.8"), "risk_threshold": FixedPoint("0.9")},
    ),
    AgentConfig(
        policy=HyperdrivePolicies.short_sally,
        number_of_agents=0,
        base_budget_wei=Budget(
            mean_wei=FixedPoint(5_000).scaled_value,  # 5k base
            std_wei=FixedPoint(1_000).scaled_value,  # 1k base
            min_wei=1,  # 1 WEI base
            max_wei=FixedPoint(100_000).scaled_value,  # 100k base
        ),
        eth_budget_wei=Budget(min_wei=FixedPoint(1).scaled_value, max_wei=FixedPoint(1).scaled_value),
        init_kwargs={"trade_chance": FixedPoint("0.8"), "risk_threshold": FixedPoint("0.8")},
    ),
    # This policy is the RL bot
    AgentConfig(
        policy=BasePolicies.no_action,
        number_of_agents=1,
        base_budget_wei=Budget(
            mean_wei=FixedPoint(5_000).scaled_value,  # 5k base
            std_wei=FixedPoint(1_000).scaled_value,  # 1k base
            min_wei=1,  # 1 WEI base
            max_wei=FixedPoint(100_000).scaled_value,  # 100k base
        ),
        eth_budget_wei=Budget(min_wei=FixedPoint(1).scaled_value, max_wei=FixedPoint(1).scaled_value),
        init_kwargs={},
    ),
]


class SaveOnBestTrainingRewardCallback(BaseCallback):
    """
    Callback for saving a model (the check is done every ``check_freq`` steps)
    based on the training reward (in practice, we recommend using ``EvalCallback``).

    :param check_freq: (int)
    :param log_dir: (str) Path to the folder where the model will be saved.
      It must contains the file created by the ``Monitor`` wrapper.
    :param verbose: (int)
    """

    def __init__(self, check_freq: int, log_dir: str, verbose=1):
        super().__init__(verbose)
        self.check_freq = check_freq
        self.log_dir = log_dir
        self.save_path = os.path.join(log_dir, "best_model")
        self.best_mean_reward = -np.inf

    def _init_callback(self) -> None:
        # Create folder if needed
        if self.save_path is not None:
            os.makedirs(self.save_path, exist_ok=True)

    def _on_step(self) -> bool:
        if self.n_calls % self.check_freq == 0:
            # Retrieve training reward
            x, y = ts2xy(load_results(self.log_dir), "timesteps")
            if len(x) > 0:
                # Mean training reward over the last 100 episodes
                mean_reward = np.mean(y[-100:])
                if self.verbose > 0:
                    print(f"Num timesteps: {self.num_timesteps}")
                    print(
                        f"Best mean reward: {self.best_mean_reward:.2f} - Last mean reward per episode: {mean_reward:.2f}"
                    )

                # New best model, you could save the agent here
                if mean_reward > self.best_mean_reward:
                    self.best_mean_reward = mean_reward
                    # Example for saving best model
                    if self.verbose > 0:
                        print(f"Saving new best model to {self.save_path}.zip")
                    self.model.save(self.save_path)

        return True


# Create log dirs
log_dir = "./hypergym_logs/"
os.makedirs(log_dir, exist_ok=True)

env = gym.make(
    "hypergym/simple_hyperdrive_env", env_config=env_config, agent_config=agent_config, gym_config=gym_config
)

env = Monitor(env, log_dir)

# Create the callback
callback = SaveOnBestTrainingRewardCallback(check_freq=10, log_dir=log_dir)

# Training
model = DQN("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=10000, callback=callback)

# Evaluation
obs, info = env.reset()
while True:
    action, _states = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, info = env.reset()

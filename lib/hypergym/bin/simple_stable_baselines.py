import logging

import gymnasium as gym
import hypergym  # This import is needed since this is what's registering the env
from agent0.base.config import AgentConfig, Budget, EnvironmentConfig
from agent0.base.policies import BasePolicies
from agent0.hyperdrive.policies import HyperdrivePolicies
from fixedpointmath import FixedPoint
from stable_baselines3 import DQN

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

env = gym.make(
    "hypergym/simple_hyperdrive_env", env_config=env_config, agent_config=agent_config, gym_config=gym_config
)

# Training
model = DQN("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=10_000, log_interval=10)
model.save("dqn_simple_hyperdrive")

# Evaluation
obs, info = env.reset()
while True:
    action, _states = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, info = env.reset()

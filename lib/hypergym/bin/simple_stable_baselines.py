import gymnasium as gym
from stable_baselines3 import PPO

# Stable baselines repo: https://github.com/DLR-RM/stable-baselines3
# The limiting factors of what algorithms you can use depend on the action space
# Since the simple hyperdrive env has discrete actions, below is the list of
# available algorithms we can use:
# ARS, A2C, DQN, HER, PPO, QR-DQN, RecurrentPPO, TRPO, Maskable PPO

# The more complicated hyperdrive has continuous action spaces (i.e., Box), and can use the
# following algorithms:
# ARS, A2C, DDPG, HER, PPO, RecurrentPPO, SAC, TD3, TQC, TRPO


# TODO should we run other training bots here in this script, or keep it separate?


# TODO parameterize this call
env = gym.make("hypergym/simple_hyperdrive_env")

# Training
model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=10_000)

# Evaluation
# TODO do we need to implement a vectorized environment?
vec_env = model.get_env()
assert vec_env is not None
obs = vec_env.reset()
for i in range(1000):
    action, _states = model.predict(obs)
    obs, reward, done, info = vec_env.step(action)
    # TODO visualize

env.close()

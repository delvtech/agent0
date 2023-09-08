from stable_baselines3 import PPO

# Stable baselines repo: https://github.com/DLR-RM/stable-baselines3
# The limiting factors of what algorithms you can use depend on the action space
# Since the simple hyperdrive env has discrete actions, below is the list of
# available algorithms we can use:
# ARS, A2C, DQN, HER, PPO, QR-DQN, RecurrentPPO, TRPO, Maskable PPO

# The more complicated hyperdrive has continuous action spaces (i.e., Box), and can use the
# following algorithms:
# ARS, A2C, DDPG, HER, PPO, RecurrentPPO, SAC, TD3, TQC, TRPO


# TODO see how this interacts with hypergym to determine how much of launching the chain
# we need to implement within the environment
model = PPO("MlpPolicy", "hypergym/simple_hyperdrive_env").learn(10_000)

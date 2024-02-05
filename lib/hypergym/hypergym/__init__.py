from gymnasium.envs.registration import register

# Register simple hyperdrive env to gym
register(
    id="hypergym/gym_environments/simple_hyperdrive_env",
    entry_point="hypergym.gym_environments/simple_hyperdrive_env:SimpleHyperdriveEnv",
    max_episode_steps=300,
)

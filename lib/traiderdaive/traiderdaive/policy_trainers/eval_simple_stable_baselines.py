import os

import gymnasium as gym
from stable_baselines3 import A2C
from stable_baselines3.common.monitor import Monitor
from traiderdaive import SimpleHyperdriveEnv

if __name__ == "__main__":
    # Create log dirs
    log_dir = ".traider_models/"
    os.makedirs(log_dir, exist_ok=True)

    gym_config = SimpleHyperdriveEnv.Config()
    env = gym.make("traiderdaive/simple_hyperdrive_env", gym_config=gym_config)

    env = Monitor(env, log_dir)

    # Training
    # model = PPO("MlpPolicy", env, verbose=1)
    model = A2C.load(log_dir + "/best_model.zip", device="cpu")

    # Run Evaluation
    obs, info = env.reset()
    while True:
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            break

    # Run dashboard from env
    dashboard_cmd = env.interactive_hyperdrive.get_dashboard_command()
    print(dashboard_cmd)
    pass

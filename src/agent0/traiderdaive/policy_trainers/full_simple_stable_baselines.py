"""Simple stable baselines policy trainer"""

import os

import gymnasium as gym
import numpy as np
from stable_baselines3 import A2C
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor, load_results
from stable_baselines3.common.results_plotter import ts2xy

from agent0.traiderdaive import FullHyperdriveEnv

# Stable baselines repo: https://github.com/DLR-RM/stable-baselines3
# The limiting factors of what algorithms you can use depend on the action space
# Since the simple hyperdrive env has discrete actions, below is the list of
# available algorithms we can use:
# ARS, A2C, DQN, HER, PPO, QR-DQN, RecurrentPPO, TRPO, Maskable PPO

# The more complicated hyperdrive has continuous action spaces (i.e., Box), and can use the
# following algorithms:
# ARS, A2C, DDPG, HER, PPO, RecurrentPPO, SAC, TD3, TQC, TRPO


class SaveOnBestTrainingRewardCallback(BaseCallback):
    """Callback for saving a model (the check is done every ``check_freq`` steps)
    based on the training reward (in practice, we recommend using ``EvalCallback``).
    """

    def __init__(self, check_freq: int, log_dir: str, verbose=1):
        """Initializes the callback class.

        Arguments
        ----------
        check_freq: int
            How often to check and save the model.
        log_dir: str
            Path to the folder where the model will be saved.
            It must contains the file created by the ``Monitor`` wrapper.
        verbose: int
            The verbosity level
        """
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
                mean_reward = float(np.mean(y[-100:]))
                if self.verbose > 0:
                    print(f"Num timesteps: {self.num_timesteps}")
                    print(
                        f"Best mean reward: {self.best_mean_reward:.2f} - "
                        f"Last mean reward per episode: {mean_reward:.2f}"
                    )

                # New best model, you could save the agent here
                if mean_reward > self.best_mean_reward:
                    self.best_mean_reward = mean_reward
                    # Example for saving best model
                    if self.verbose > 0:
                        print(f"Saving new best model to {self.save_path}.zip")
                    self.model.save(self.save_path)

        return True


def run_train():
    """Runs training to generate a RL model."""
    # TODO parameterize these variables
    # Create log dirs
    log_dir = ".traider_models/"
    os.makedirs(log_dir, exist_ok=True)

    gym_config = FullHyperdriveEnv.Config()
    env = gym.make("traiderdaive/full_hyperdrive_env", gym_config=gym_config)

    env = Monitor(env, log_dir)

    # Create the callback
    callback = SaveOnBestTrainingRewardCallback(check_freq=10, log_dir=log_dir)

    # Training
    model = A2C("MultiInputPolicy", env, verbose=1, device="cpu")
    model.learn(total_timesteps=100000, callback=callback)


if __name__ == "__main__":
    run_train()

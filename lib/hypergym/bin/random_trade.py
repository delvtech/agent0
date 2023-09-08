import gymnasium as gym
import hypergym
import matplotlib.pyplot as plt

config = {
    "long_base_amount": 100,
    "short_bond_amount": 100,
    "window_size": 10,
}

env = gym.make("hypergym/simple_hyperdrive_env", config=config)

observation = env.reset(seed=2023)
while True:
    action = env.action_space.sample()
    print(f"{action=}")
    observation, reward, terminated, truncated, info = env.step(action)
    done = terminated or truncated

    # env.render()
    if done:
        print("info:", info)
        break

# plt.cla()
# env.unwrapped.render_all()
# plt.show()

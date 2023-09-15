import gymnasium as gym
import hypergym  # This import is needed since this is what's registering the env
from agent0.hyperdrive.agents import HyperdriveAgent
from eth_account.account import Account

gym_config = {
    "long_base_amount": 100,
    "short_bond_amount": 100,
    "window_size": 10,
}

# TODO use different account
# https://github.com/delvtech/elf-simulations/issues/816
# This is the private key of account 0 of the anvil pre-funded account
account_private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
account = HyperdriveAgent(Account().from_key(account_private_key), policy=None)

# TODO fund this account through some call


env = gym.make("hypergym/simple_hyperdrive_env", account=account, gym_config=gym_config)

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

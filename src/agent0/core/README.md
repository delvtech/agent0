# Running Agents

Agents can be deployed on-premesis or via cloud services.

We have two flows for running agents: via autonomous deployment or via interactive hyperdrive.
Each will be discussed below.

## Step 1: Install agent0

1.1.
The agent0 repo contains the agent0 library.
Install agent0 libraries by following the installation instructions found [on the agent0 github](https://github.com/delvtech/agent0/blob/main/INSTALL.md).

> **💡NOTE:**
> 
> **pyenv install for Linux:**
> 
> If you're running bash on Linux, then to install Pyenv you’ll want to follow the [automatic installer](https://github.com/pyenv/pyenv#automatic-installer) instructions, and then [add pyenv to your shell environment](https://github.com/pyenv/pyenv#set-up-your-shell-environment-for-pyenv).
> 
> **using a fork:**
> 
> If you want the ability to PR new agent policies into our repo then we recommend you make a fork of the delvtech/agent0 repo.
> ([repo link](https://github.com/delvtech/agent0), [GitHub fork instructions](https://docs.github.com/en/get-started/quickstart/fork-a-repo?tool=webui&platform=mac)).

1.2.
Run the agent0 tests to verify that everything installed correctly by executing `python -m pytest` from the repository root. Make sure you have enabled the correct Python environment, and installed the `requirements-dev.txt` file first.

## Interactive Hyperdrive

Interactive Hyperdrive also requires the user to install [Foundry](https://book.getfoundry.sh/getting-started/installation), which we use to run the Anvil local testnet node, as well as [docker](https://docs.docker.com/engine/install/) for hosting the node and a database.

With these tools installed, you can run Interactive Hyperdrive directly. See our [example script](https://github.com/delvtech/agent0/blob/main/lib/agent0/examples/interactive_hyperdrive_example.py) to get started.

If you wish to deploy autonomous bots (for example, to execute trading policies in a continuous loop), then follow the remaining steps:

## Step 2: Set your configuration

2.1.
Copy the `eth.env.sample` file to `eth.env` (`cp eth.env.sample eth.env`) and edit the file to specify the URIs of various endpoints to the chain.
The default values are set to run off a local chain on docker.
For example:

```bash
RPC_URI="http://localhost:8545"
ARTIFACTS_URI="http://localhost:8080"
DATABASE_API_URI="http://localhost:5002"
```

2.2.
Copy (or edit) one of the template scripts found in `lib/agent0/examples`:

- [`hyperdrive_agents.py`](https://github.com/delvtech/agent0/blob/main/lib/agent0/examples/hyperdrive_agents.py) for an example running existing policies.
- [`custom_agent.py`](https://github.com/delvtech/agent0/blob/main/lib/agent0/examples/custom_agent.py) for an example of writing and running a custom agent.

This will be the main script to run your agent.

2.3.
Update the parameters in the script. For example:

```python
# option to customize the env file name,
ENV_FILE = "hyperdrive_agents.account.env"
USERNAME = "<agent_username>"
```

2.4.
Change various bot arguments to your liking by adjusting the `AgentConfig` parameters.

## Step 3: Fund your agents (if you wish to fund the agents from your own wallet):

3.1.
Run the script once to generate an environment file (the name of the file is taken from the `ENV_FILE` variable in the script).

```bash
python lib/agent0/examples/hyperdrive_agents.py
```

> **💡NOTE:**
> This will generate new environment variables for the agents and write them to the specified `ENV_FILE`.
> The new variables are private keys as well as Base and Eth budgets for all of the agents you specified in your config.
> This is what your `.env` file might look like after:
>
> ```bash
> export USER_KEY=
> export AGENT_KEYS='["0xAGENT_PRIVATE_KEY"]'
> export AGENT_BASE_BUDGETS='[3396163194603698651136]'
> export AGENT_ETH_BUDGETS='[1000000000000000000]'
> ```
>
> These are the generated private keys for your agents. If you delete your `ENV_FILE` file or otherwise lose the agent private keys, then your money is gone forever.
> Hang on to those keys!
>

3.2. The output will tell you to run the funding script to fund your agents. For example,

```bash
python lib/agent0/bin/fund_agents_from_user_key.py -u 0xUSER_PRIVATE_KEY -f example_agents.accounts.env
```

Replace the `0xUSER_PRIVATE_KEY` in the above command with your private key for the chain (e.g., from Anvil).
This is the account that will fund the agents.
The script will automatically update the specified `ENV_FILE` to contain your user key, which is needed by the script.

## Step 4: Start trading!

4.1. Run the trading script again to start trading.

> **💡NOTE:**
> For development, you may pass in an environment variable `DEVELOP` to skip step 3 above. E.g.,
> 
> ```bash
> DEVELOP=true python lib/agent0/examples/hyperdrive_agents.py
> ```
> 

## Liquidating agents

The `LIQUIDATION` flag allows you to run your agents in liquidation mode.
When this flag is true, the agents will attempt to close out all open positions.
The script will exit when this is complete.

> **💡NOTE:**
> Bots that have open LP positions may not be able to fully liquidate if their LP is allocated to back a trade.

# Running Agents

Bots for the trading competition run on a dedicated AWS EC2 instance.
Each user must provide an SSH key to log in to the EC2 and deploy their bot.

Alternatively, you’re welcome to run bots on your own server, where you can skip directly to step 3.

## Step 1: Install elf-simulations

1.1.
**Optional**, if you want the ability to PR new bots into our repo:

Make a fork of the delvtech/elf-simulations repo. ([repo link](https://github.com/delvtech/elf-simulations), [GitHub fork instructions](https://docs.github.com/en/get-started/quickstart/fork-a-repo?tool=webui&platform=mac)).

1.2.
Install elf-simulations packages by following the installation instructions found [on github](https://github.com/delvtech/elf-simulations/blob/main/INSTALL.md).

    >**💡NOTE:**
    >
    >**pyenv install tips:**
    >
    >If you're using an AWS server running bash on Linux, then to install Pyenv you’ll want to follow the [automatic installer](https://github.com/pyenv/pyenv#automatic-installer) instructions, and then [add pyenv to your shell environment](https://github.com/pyenv/pyenv#set-up-your-shell-environment-for-pyenv).
    >
    >**git clone the correct repo:**
    >
    >You’ll want to clone your fork,
    >e.g.: `git clone https://github.com/[YOUR_USERNAME]/elf-simulations.git elf-simulations`
    >
    >You’ll probably also want to also configure the remote (`delvtech`) repository.
    >Once you’ve made the fork and cloned it, navigate inside (`cd elf-simulations`), and run
    >
    >```bash
    >git remote add upstream git@github.com:delvtech/elf-simulations.git
    >```
    >
    >to sync up an `upstream` repository.
    >Then whenever you want to sync your fork with the latest code you can run:
    >
    >```bash
    >git fetch upstream
    >git merge upstream/main
    >```
    >
    >**Hyperdrive contracts:**
    >
    >You don’t need to do any of the optional install Hyperdrive steps for eth_agents to work.
    >

1.3.
Navigate to the `elf-simulations` folder: `cd elf-simulations/`

1.4.
Run the elf-simulations tests to verify that everything installed correctly by executing `python -m pytest`. Make sure you have enabled the correct Python environment, and installed the `requirements-dev.txt` file first.

## Step 2: Set your configuration

2.1.
Copy (or edit) one of the template scripts found in `lib/agent0/examples`:

    - `hyperdrive_agents.py` for an example running existing policies.
    - `custom_agent.py` for an example of writing and running a custom agent.

   This will be the main script to run your agent.

2.2.
Update the parameters in the script. For example:

    ```python
    # option to customize the env file name,
    # leave unchanged for default behavior
    ENV_FILE = "hyperdrive_agents.account.env"
    RPC_URI = "<rpc_uri>"
    ARTIFACTS_URI = "<artifacts_uri>"
    DATABASE_API_URI = "<database_api_uri>"
    USERNAME = "<agent_username>"
    ```

2.3.
**Optional**: Change various bot arguments to your liking by adjusting the `AgentConfig` parameters.

## Step 3: Fund your agents (if you wish to fund the agents from your own wallet key):

3.1.

    ```bash
   python lib/agent0/examples/hyperdrive_agents.py
    ```
Run the script once to generate environment file, with filename set to `ENV_FILE` in the script.


    >**💡NOTE:**
    >This will generate new environment variables for the agents and write them to the specified `ENV_FILE`.
    >The new variables are private keys as well as Base and Eth budgets for all of the agents you specified in your config.
    >This is what your `.env` file might look like after:
    >
    >```bash
    >export USER_KEY=
    >export AGENT_KEYS='["0xAGENT_PRIVATE_KEY"]'
    >export AGENT_BASE_BUDGETS='[3396163194603698651136]'
    >export AGENT_ETH_BUDGETS='[1000000000000000000]'
    >```
    >
    >These are the generated private keys for your agents. If you delete your `ENV_FILE` file or otherwise lose the agent private keys, then your money is gone forever.
    >Hang on to those keys!
    >

3.2. The output will tell you to run the funding script to fund your bots. For example,

   ```bash
   python lib/agent0/bin/fund_agents_from_user_key.py -u 0xUSER_PRIVATE_KEY --host <host> -f example_agents.accounts.env
   ```

   Replace the `0xUSER_PRIVATE_KEY` in the above command with your private key for the chain (e.g., from Anvil), and the `<host>` to the host address for the chain.
   This is the account that will fund the agents.
   The script will automatically update the specified `ENV_FILE` to contain your user key, which is needed by the script.


## Step 4: Start trading!

4.1. Run the trading script again to start trading.

    >**💡NOTE:**
    >For development, you may pass in an environment variable `DEVELOP` to skip step 3 above. E.g.,
    > ```bash
    > DEVELOP=true python lib/agent0/examples/hyperdrive_agents.py
    > ```

## Liquidating bots

The `LIQUIDATION` flag allows you to run your bots in liquidation mode. When this flag is true,
the bots will attempt to close out all open positions. The script will exit when this is complete.

    >**💡NOTE:**
    >If your bot has an LP position open, it's very likely your bot will repeatedly throw an error
    >when in liquidation mode. This is due to attempting to close out withdrawal shares that are currently
    >not available to withdraw. You can keep your script running in this case; the script will exit when all
    >trades are successful.

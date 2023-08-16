# Running Agents

We have set up agents to run on a dedicated AWS EC2 instance.
These instructions can likely be followed for other unix/linux setups, however.

## Step 1: Install elf-simulations

1. make a fork of the [delvtech/elf-simulations repo](https://github.com/delvtech/elf-simulations) ([GitHub fork instructions](https://docs.github.com/en/get-started/quickstart/fork-a-repo?tool=webui&platform=mac)).

2. Install elf-simulations packages by following the installation instructions found [on github](https://github.com/delvtech/elf-simulations/blob/main/INSTALL.md).

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

3. navigate to the `elf-simulations` folder: `cd elf-simulations/`

4. run the elf-simulations tests to verify that everything installed correctly by executing `python -m pytest`. Make sure you have enabled the correct Python environment!

## Step 2: Set your configuration

1. [optional] If you need to connect to a remote chain, copy `eth.env.sample` to `eth.env` and edit the host.

2. Copy (or edit) one of the template scripts found in `lib/agent0/examples`:

    - `hyperdrive_agents.py` for an example running existing policies.
    - `example_agent.py` for an example of writing and running a custom agent.

   This will be the main script to run your agent.

3. Set `DEVLEOP=True` flag to automatically fund your agents, or set `DEVELOP=False` and go to step 3 to fund your agents from your own wallet key.

## [optional] Step 3: Fund your agents (if you wish to fund the agents from your own wallet key):

1. Run the script once to generate the `ENV_FILE` as defined in the script. For example, the script will generate `example_agents.account.env`

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

2. Run the funding script. The output of the script should print the fund command. For example,
   ```bash
       python lib/agent0/bin/fund_agents_from_user_key.py -u 0xUSER_PRIVATE_KEY -f example_agents.accounts.env
   ```
   Replace the `0xUSER_PRIVATE_KEY` in the above command with your private key for the chain (e.g., from Anvil). This is the account that will fund the agents. The script will automatically update the specified `ENV_FILE` to contain your user key, which is needed by the script.


## Step 4: Start trading!

1. run your trading script to start trading!

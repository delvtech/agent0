# Running Bots

We have set up bots to run on a dedicated AWS EC2 instance.
These instructions can likely be followed for other unix/linux setups, however.

## Step 1: Install elfpy

1. make a fork of the [delvtech/elf-simulations repo](https://github.com/delvtech/elf-simulations) ([GitHub fork instructions](https://docs.github.com/en/get-started/quickstart/fork-a-repo?tool=webui&platform=mac)).

    >**💡NOTE:**
    >You’ll probably want to also configure the remote (`delvtech`) repository.
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

2. Install elfpy by following the installation instructions found [on github](https://github.com/delvtech/elf-simulations/blob/main/INSTALL.md).

    >**💡NOTE:**
    >
    >**pyenv install tips:** If your using an AWS server running bash on Linux, then to install Pyenv you’ll want to follow the [automatic installer](https://github.com/pyenv/pyenv#automatic-installer) instructions, and then [add pyenv to your shell environment](https://github.com/pyenv/pyenv#set-up-your-shell-environment-for-pyenv).
    >
    >**git clone the correct repo**: You’ll want to clone your fork in step 2 of the install instructions.
    >e.g.: `git clone https://github.com/[YOUR_USERNAME]/elf-simulations.git elf-simulations`
    >
    >**Hyperdrive contracts** You don’t need to do any of the optional install Hyperdrive steps for eth_bots to work.

3. navigate to the `elf-simulations` folder: `cd elf-simulations/`

4. run the elfpy tests to verify that everything installed correctly by executing `python -m pytest`. Make sure you have enabled the correct Python environment!

## Step 2: Fund your bots & start trading!

1. get your private key for the chain (e.g. from Anvil)
2. modify `eth_bots/eth_bots_config.py` as you see fit for your experiment.

    >**💡NOTE:**
    >Make sure you change the URLs (e.g. to AWS or `localhost`):
    >
    >```python
    >username_register_url="http://<AWS_IP>:<UNAME_PORT>"
    >artifacts_url="http://<AWS_IP>:<ARTIFACTS_PORT>"
    >rpc_url="http://<AWS_IP>:<RPC_PORT>"
    >```
    >

3. run the `eth_bots/populate_env.py` script with your private key as an argument, and pipe the output to a `.env` file. For example:

    >**💡NOTE:**
    >This command overwrites your `.env` file, so make sure you're ok with losing whatever contents are in it first!
    >
    >```bash
    >python eth_bots/populate_env.py 0xUSER_PRIVATE_KEY > .env
    >```
    >
    >This will generate new environment variables for the bots and write them to the `.env` file.
    >The new variables are private keys as well as Base and Eth budgets for all of the agents you specified in your config.
    >This is what your `.env` file might look like after:
    >
    >```bash
    >export USER_KEY='0xUSER_PRIVATE_KEY'
    >export AGENT_KEYS='["0xAGENT_PRIVATE_KEY"]'
    >export AGENT_BASE_BUDGETS='[3396163194603698651136]'
    >export AGENT_ETH_BUDGETS='[1000000000000000000]'
    >```
    >

**CAREFUL!** In the time between steps 4 and 5, if you delete your `.env` file or otherwise lose the bot private keys, then your money is gone forever. Hang on to those keys!

4. run `python eth_bots/fund_bots.py` to fund your bots. This script will parse the `.env` file and allocate the budgets by transferring Base and Eth from the wallet corresponding to the `USER_KEY` environment variable.

5. run `python eth_bots/main.py` to start trading!

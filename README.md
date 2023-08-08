# Mihai's testing workflow

Lets you modify the data acquisition and PNL calculations, by running it outside of docker.

Following combination of:

1. [elf-simulations INSTALL.md](https://github.com/delvtech/elf-simulations/blob/main/INSTALL.md)
2. [agent0 INSTALL.md](https://github.com/delvtech/elf-simulations/tree/main/lib/agent0)
3. [infra repo README.md](https://github.com/delvtech/infra/blob/main/README.md)

## tldr;

| legend | meaning |
| ------ | ------- |
| **bold** | change from default |
| **(+)**  | step with minor changes |
| **(*)**  | step with major changes |

1. **(+)** have pyenv and **pyenv-virtualenv installed** ([pyenv instructions](https://github.com/pyenv/pyenv#installation))
2. clone repo
3. **(+)** set up virtualenv:
```zsh
pyenv install 3.10
pyenv global 3.10
pyenv virtualenv mihaipy
cd <repo_location>
pyenv local mihaipy
```
4. install elf-sims:
```zsh
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```
5. check out version of [infra repo](https://github.com/delvtech/infra/) to use (check main and PRs)
    - for example, on August 8 2023, main has `ELFPY_TAG=0.3.2` but I want to use latest elf-sims `ELFPY_TAG=0.4.1` so I check out [PR #66](https://github.com/delvtech/infra/pull/66) which has it
6. check out [hyperdrive repo](https://github.com/delvtech/hyperdrive/) in sym-linked folder (as per instructions)

start setting up the local dev environment:

7. **(+)** in `infra` folder set `ETH_PORT=8546` in `env/env.ports` so it works on my computer
8. **(+)** create `.env` with ``./setup_env.sh --devnet --ports --postgres``
9. docker login if you need to (should persist after first time)
10. run `docker compose down -v` (set to `dcd` alias) to ensure nothing is running in docker
11. run `docker compose up --pull always` (set to `dcu` alias) to run selected docker services
12. **(*)** apply my custom config, as in [this commit](https://github.com/wakamex/elf-simulations/commit/725ac696e3427f4d1e013329c48d44462a013e69):
```
in runner_config.py:
    - delete previous logs to True (from False)
    - format log messages as minimal one-liner
    - log level to DEBUG (from INFO)
    - rpc url port to 8546 (from 8545)
    - username to Mihai from changeme
in acquire_data.py, rpc url port to 8546 (from 8545)
```
13. **(*)** bring up username registration server with `python lib/chainsync/bin/register_username_server.py`
14. **(*)** bring up the data acquisition pipeline with `python lib/chainsync/bin/acquire_data.py`
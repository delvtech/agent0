### Migrations Image ###
# pinned to a specific image chosen from https://github.com/delvtech/hyperdrive/pkgs/container/hyperdrive%2Fmigrations
# v0.0.1 (2022-05-23)
# FROM ghcr.io/delvtech/hyperdrive/migrations:0.0.1 as migrations
# 2022-05-31
# FROM ghcr.io/delvtech/hyperdrive/migrations:nightly-3188e7df62a07a77c61c467ab640aeec836c79fe as migrations
# v0.0.3 w/ relative path imports to work with ape
FROM ghcr.io/delvtech/hyperdrive/migrations:212b56881cdc26135da4e11801b18b3a62dc4ae2 as migrations

# ### Python Image ###
FROM python:3.9.16-bullseye

# set bash as default shell
SHELL ["/bin/bash", "-c"]

WORKDIR /app

# copy everything in elf-simulations
COPY . ./

# install base dependencies
RUN python -m pip install --no-cache-dir --upgrade pip
RUN python -m pip install --no-cache-dir -r requirements.txt
RUN ape plugins install .

# install dev dependencies
RUN python -m pip install --no-cache-dir -r requirements-dev.txt

# copy hyperdrive contracts from migrations image
COPY --from=migrations /src/ ./hyperdrive_solidity/

# copy foundry over from migrations image
COPY --from=migrations /usr/local/bin/ /usr/local/bin

# install elf-simulations
RUN python -m pip install -e .
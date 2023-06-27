### Migrations Image ###
# pinned to a specific image chosen from https://github.com/delvtech/hyperdrive/pkgs/container/hyperdrive%2Fmigrations
FROM ghcr.io/delvtech/hyperdrive/migrations:0.0.4 as migrations

# ### Python Image ###
FROM python:3.9.16-bullseye

# set bash as default shell
SHELL ["/bin/bash", "-c"]

WORKDIR /app

# copy everything in elf-simulations
COPY . ./

# install elfpy
RUN python -m pip install --no-cache-dir --upgrade pip
RUN python -m pip install --no-cache-dir -e ."[with-dependencies,docs]"
RUN ape plugins install .

# copy hyperdrive contracts from migrations image
COPY --from=migrations /src/ ./hyperdrive_solidity/

# copy foundry over from migrations image
COPY --from=migrations /usr/local/bin/ /usr/local/bin

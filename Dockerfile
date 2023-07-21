### Migrations Image ###
# pinned to a specific image chosen from https://github.com/delvtech/hyperdrive/pkgs/container/hyperdrive%2Fdevnet
FROM ghcr.io/delvtech/hyperdrive/devnet:0.0.8 as migrations

# ### Python Image ###
FROM python:3.10-slim

WORKDIR /app

# copy everything in elf-simulations
COPY . ./

# install elfpy in one step, adding build tools, then removing them
# https://stackoverflow.com/questions/58300046/how-to-make-lightweight-docker-image-for-python-app-with-pipenv
RUN python -m pip install --no-cache-dir --upgrade pip && \
  apt-get update && \
  apt-get install -y --no-install-recommends gcc python3-dev libssl-dev git && \
  python -m pip install --no-cache-dir -e ."[with-dependencies,postgres,ape]" coverage && \
  apt-get remove -y gcc python3-dev libssl-dev && \
  apt-get autoremove -y && \
  pip uninstall pipenv -y

# copy hyperdrive contracts from migrations image
COPY --from=migrations /src/ ./hyperdrive_solidity/

# copy foundry over from migrations image
COPY --from=migrations /usr/local/bin/ /usr/local/bin

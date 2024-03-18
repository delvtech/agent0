# ### Python Image ###
FROM python:3.10-slim

WORKDIR /app

# copy everything in agent0
COPY . ./

# install packages in one step, adding build tools, then removing them
# https://stackoverflow.com/questions/58300046/how-to-make-lightweight-docker-image-for-python-app-with-pipenv
RUN apt-get update && \
  apt-get install -y --no-install-recommends gcc python3-dev libssl-dev git && \
  python -m pip install --no-cache-dir --upgrade pip && \
<<<<<<< HEAD
  python -m pip install --no-cache-dir . && \
=======
  python -m pip install --no-cache-dir uv && \
  python -m uv pip install --no-cache-dir agent0@.[all] && \
>>>>>>> e030f8e9 (remove hyperdrivepy txt install)
  apt-get remove -y gcc python3-dev libssl-dev && \
  apt-get autoremove -y && \
  pip uninstall pipenv -y
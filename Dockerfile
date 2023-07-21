# Migrations Image
FROM ghcr.io/delvtech/hyperdrive/devnet:0.0.8 as migrations

# Base Image
FROM python:3.10-slim as base
WORKDIR /app

# Compile Image
FROM base as compile-image
COPY . ./

RUN apt-get update && \
  apt-get install -y --no-install-recommends gcc python3-dev libssl-dev git lsb-release && \
  python -m venv /opt/venv && \
  . /opt/venv/bin/activate && \
  python -m pip install --no-cache-dir --upgrade pip && \
  python -m pip install --no-cache-dir -e ."[with-dependencies]" coverage

# Final Image
FROM base as final
RUN apt-get update && apt-get install -y git lsb-release jq curl
COPY --from=compile-image /opt/venv /opt/venv
COPY --from=migrations /src/ ./hyperdrive_solidity/
COPY --from=migrations /usr/local/bin/ /usr/local/bin
ENV PATH="/opt/venv/bin:$PATH"
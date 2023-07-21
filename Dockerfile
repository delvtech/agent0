# Migrations Image
FROM ghcr.io/delvtech/hyperdrive/devnet:0.0.8 as migrations

# Compile Image
FROM python:3.10-slim as compile-image
WORKDIR /app
COPY . ./

RUN python -m pip install --no-cache-dir --upgrade pip && \
  apt-get update && \
  apt-get install -y --no-install-recommends gcc python3-dev libssl-dev git lsb-release && \
  python -m venv /opt/venv && \
  . /opt/venv/bin/activate && \
  pip install --no-cache-dir -e ."[with-dependencies,postgres,ape]" coverage && \
  apt-get remove -y gcc python3-dev libssl-dev && \
  apt-get autoremove -y && \
  apt-get clean && \

# Final Image
FROM python:3.10-slim
COPY --from=compile-image /opt/venv /opt/venv
COPY --from=migrations /src/ ./hyperdrive_solidity/
COPY --from=migrations /usr/local/bin/ /usr/local/bin
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
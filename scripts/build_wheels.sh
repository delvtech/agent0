#!/bin/bash

# agent0 install

echo "install required packages for building wheels"
python -m pip install --upgrade pip uv
uv venv .venv -p 3.10
source .venv/bin/activate
uv pip install 'agent0[all]@.' build

echo "build the wheel for the current platform"
python -m build

# Move remaining wheels into wheelhouse folder
mkdir -p wheelhouse/
mv dist/* wheelhouse/
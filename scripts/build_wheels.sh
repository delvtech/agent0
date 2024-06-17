#!/bin/bash

# agent0 install

echo "install required packages for building wheels"
python -m pip install --upgrade pip uv
python -m venv --upgrade-deps .venv
source .venv/bin/activate
pip install '.[all]' build

echo "build the wheel for the current platform"
python -m build

# Move remaining wheels into wheelhouse folder
mkdir -p wheelhouse/
mv dist/* wheelhouse/
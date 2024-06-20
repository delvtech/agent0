#!/bin/bash

# agent0 install

echo "install required packages for building wheels"
python -m pip install --upgrade pip
python -m venv --upgrade-deps .venv
source .venv/bin/activate
pip install '.[all]' build

echo "build the wheel for the current platform"
python -m build

# Export dependency versions used to build the wheel
FREEZE_FILE="dist/frozen-requirements.txt"
timestamp="$(date)"
version="$(git describe --abbrev=12 --always)"
echo -e "# Generated at $timestamp ($version)\n" > $FREEZE_FILE
pip3 freeze | tee -a $FREEZE_FILE
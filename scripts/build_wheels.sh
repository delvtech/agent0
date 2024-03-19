#!/bin/bash

# agent0 install

echo "install required packages for building wheels"
python -m pip install --upgrade pip uv build
uv pip install agent0@.[all]

echo "build the wheel for the current platform"
python -m build

# Move remaining wheels into wheelhouse folder
mv dist/* wheelhouse/
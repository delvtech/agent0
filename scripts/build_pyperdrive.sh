#!/bin/bash

# Pyperdrive install for Linux-based platforms
# This is a temporary script until we finish seting up CI wheel building inside pyperdrive
# The script assumes that the `hyperdrive` and `pyperdrive` repos are cloned inside the repository root


echo "move hyperdrive folder relative paths"
mv hyperdrive pyperdrive/

echo "install required packages for building wheels"
python -m pip install --upgrade -r pyperdrive/requirements-dev.txt

echo "nav into the crate so relative paths work"
cd pyperdrive/crates/pyperdrive

echo "build the wheel for the current platform"
python setup.py bdist_wheel

echo "back to elf-simulations dir"
cd ../../.. 

echo "copy built wheel files from pyperdrive into packages"
cp pyperdrive/crates/pyperdrive/dist/* packages/pyperdrive/

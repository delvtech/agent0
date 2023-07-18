python3 --version
which python3
python3 -m ensurepip
python3 -m pip install --upgrade pip pip-tools

# install only dependencies using this one weird trick (https://github.com/pypa/pip/issues/11440#issuecomment-1638573638)
# the elf-simulations package is not required to builds docs and vercel does not support python 3.10 as of July 18, 2023
PYTHON=python3
EXTRAS=docs
PIPFLAGS="--no-warn-conflicts"
$PYTHON -m pip install pip-tools
$PYTHON -m piptools compile --extra=$EXTRAS -o - pyproject.toml |
$PYTHON -m pip install -r /dev/stdin $PIPFLAGS

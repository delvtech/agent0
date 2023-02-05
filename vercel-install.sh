python3 --version
which python3
python3 -m ensurepip
python3 -m pip install --upgrade pip
# repository dependencies
python3 -m pip install -r requirements.txt
# extra dependencies for the docs
python3 -m pip install -r requirements-dev.txt
# intstall elfpy package
python3 -m pip install -e .
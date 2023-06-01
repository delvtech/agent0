python3 --version
which python3
python3 -m ensurepip
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-dev.txt
# Needed for jupyter nbconvert
python3 -m pip install ipykernel
# For some reason kernel is missing libsqlite3
apt-get install libsqlite3-dev
python3 -m pip install pysqlite
# Install elfpy
python3 -m pip install .

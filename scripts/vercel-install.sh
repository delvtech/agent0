python3 --version
which python3
python3 -m ensurepip
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-dev.txt
# Needed for jupyter nbconvert
python3 -m pip install ipykernel
# For some reason python is missing libsqlite3
yum install sqlite-devel -y
python3 -m pip install pysqlite3
# Install elfpy
python3 -m pip install .

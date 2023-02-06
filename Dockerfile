FROM python:3.8.16-bullseye
WORKDIR /app
COPY . ./
RUN python -m pip install --upgrade pip
RUN python -m pip install --no-cache-dir -r requirements.txt
RUN python -m pip install --no-cache-dir -r requirements-dev.txt
RUN python -m pip install -e .
RUN python -m pip install jupyter

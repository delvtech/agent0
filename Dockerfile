FROM matthewfeickert/docker-python3-ubuntu:latest
WORKDIR /app/
COPY . ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-dev.txt
RUN pip install -e .

# Build

Our docker containers automatically build in the GitHub CI. However, if you wish to build it yourself you can do by following these steps:

First build the Python environment
```
docker build -t local-tag-python -f Dockerfile-python-base
```

Next build the elfpy packages
```
docker build -t local-tag-elfpy -f Dockerfile-elf-sims
```

Then in your Docker compose you can build with `image: local-tag-elfpy:latest`.

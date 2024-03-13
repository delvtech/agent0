# Build

We use Docker to manage our build environment.

To build a local image, make sure you have Docker installed and running, then use:

```bash
chmod +x scripts/build_local_docker_image.sh
./scripts/build_local_docker_image.sh
```

If built successfully, a `docker image ls` command should look like this:

```bash
REPOSITORY    TAG       IMAGE ID       CREATED          SIZE
agent0        latest    fd84351979d7   21 minutes ago   2.04GB
```

This image receives the `agent0` tag and can be reference with`image: agent0:latest`, for instance if you're using Docker Compose.
To build a local image and push it to ghcr.io, make sure you have Docker installed and running, then use:

```bash
>> ./scripts/build_and_push_docker_image.sh
```

If you get a 401 error, you'll need to make a GH Personal Access Token with write access.
You can optionally provide a tag:

```bash
>> ./scripts/build_and_push_docker_image.sh my-latest
```

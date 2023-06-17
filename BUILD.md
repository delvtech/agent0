# Build

We use Docker to manage our build environment.

This requires access to the private hyperdrive repo, available only to Delv team members currently.

To build a local image, make sure you have Docker installed and running, then use:

```bash
chmod +x build_local_docker_image.sh
./build_local_docker_image.sh
```

If built successfully, a `docker image ls` command should look like this:

```
REPOSITORY    TAG       IMAGE ID       CREATED          SIZE
elf-sims      latest    fd84351979d7   21 minutes ago   2.04GB
```

This image receives the `elf-sims` tag and can be reference with`image: elf-sims:latest`,
for instance if you're using Docker Compose.

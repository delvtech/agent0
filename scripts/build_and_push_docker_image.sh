#!/bin/bash

TAG="default"

if [ $# -eq 0 ]; then
  echo "Using 'default' as the tag for the image."
else
  TAG="$1"
  echo "Using $TAG as the tag for the image."
fi

echo "Tag: $TAG"

docker build --no-cache -t $TAG -f Dockerfile .
IMAGE_ID=$(docker image ls -q | awk 'NR==1{print}')
echo "Image Id: $IMAGE_ID"

if [[ "$TAG" == "default" ]]; then
    TAG=$IMAGE_ID
fi
echo "Tag: $TAG"

docker tag $IMAGE_ID ghcr.io/delvtech/elf-simulations/$TAG
docker image push ghcr.io/delvtech/elf-simulations/$TAG

echo "Tag pushed to ghcr.io/delvtech/elf-simulations/$TAG"
echo "Run the following command to retrieve the image:"
echo "docker image pull ghcr.io/delvtech/elf-simulations/$TAG"
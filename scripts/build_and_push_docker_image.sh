#!/bin/bash

TAG=""

if [ $# -eq 0 ]; then
  echo "Using Image ID as the tag for the image."
else
  TAG="$1"
  echo "Using $TAG as the tag for the image."
fi

TAG_OPTION=""
if [[ -n $TAG ]]; then
    TAG_OPTION="-t $TAG"
fi

IMAGE_ID=$(docker build --no-cache $TAG_OPTION -f Dockerfile ../ | tail -n 1 | awk '{ print $NF }')
echo "Image Id: $IMAGE_ID"

if [[ -n $TAG ]]; then
    TAG=$IMAGE_ID
fi

docker tag $IMAGE_ID ghcr.io/delvtech/elf-simulations/$TAG
docker image push ghcr.io/delvtech/elf-simulations/$TAG

echo "Tag pushed to ghcr.io/delvtech/elf-simulations$TAG"
echo "Run the following command to retrieve the image:"
echo "docker image pull ghcr.io/delvtech/elf-simulations$TAG"
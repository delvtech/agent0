#!/bin/bash

if [ $# -ne 1 ]; then
  echo "Usage: $0 <image-tag>"
  exit 1
fi

# Docker image details
image_name="agent0"
tag=$1

# Paths are relative to where the script was run from;
# it is assumed to be run from the agent0 root
docker build --no-cache -f Dockerfile -t $image_name:$tag .

echo "Docker image built and tagged as $image_name:$tag."

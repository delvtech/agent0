#!/bin/bash

if [ $# -ne 1 ]; then
  echo "Usage: $0 <tag>"
  exit 1
fi

# GitHub repository details
repo_owner="delvtech"
repo_name="elf-simulations"

# Docker image details
image_name="elfpy"
tag=$1

docker build --no-cache -t $image_name:$tag https://github.com/$repo_owner/$repo_name.git#$tag

echo "Docker image built and tagged as $image_name:$tag."

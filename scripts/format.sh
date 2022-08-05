#!/bin/sh -e
set -x

SRC_DIR="scraper"

autoflake \
 --remove-all-unused-imports \
 --recursive \
 --remove-unused-variables \
  --exclude=__init__.py \
 --in-place \
 $SRC_DIR

black $SRC_DIR

isort $SRC_DIR

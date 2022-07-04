#!/usr/bin/env bash

# Run from the repo's root folder

echo "Generating symlinks for all hosts inside the guests dir..."

# link json files
cd data/guests
ln -s ../hosts/* .

# link avatar images
cd ../../static/guests
ln -s ../hosts/* .

echo "Done."

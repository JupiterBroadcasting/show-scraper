#!/usr/bin/env bash
set -x

SRC_DIR="scraper"

mypy $SRC_DIR
black $SRC_DIR --check
isort --check-only $SRC_DIR
flake8 $SRC_DIR
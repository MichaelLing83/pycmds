#! /usr/bin/env bash

RUN_DIR=$(pwd)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR" || exit 1

uv venv --python ">=3.10,<=3.12"
source .venv/bin/activate
uv sync

cd $RUN_DIR || exit 1

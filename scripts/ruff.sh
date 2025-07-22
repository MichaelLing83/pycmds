#! /usr/bin/env bash

RUN_DIR=$(pwd)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR/.." || exit 1

UV_HTTP_TIMEOUT=3000 uv tool install ruff
uv tool run ruff check ./pycmds --fix
uv tool run ruff format ./pycmds

cd $RUN_DIR || exit 1
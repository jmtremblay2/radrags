#!/usr/bin/env bash
set -e
uv run black .
uv run pytest "$@"

#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 [--build|--open]"
    echo "  --build  Build static docs to site/ (default)"
    echo "  --open   Start live preview and open in browser"
    exit 1
}

MODE="${1:---build}"

uv sync --extra docs

case "$MODE" in
    --build)
        uv run mkdocs build
        echo "Documentation built in site/"
        ;;
    --open)
        uv run mkdocs serve --open
        ;;
    *)
        usage
        ;;
esac

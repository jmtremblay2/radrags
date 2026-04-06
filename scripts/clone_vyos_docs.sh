#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/vyos/vyos-documentation.git"
DEST_DIR="$(cd "$(dirname "$0")/.." && pwd)/vendor/vyos-documentation"

if [ -d "$DEST_DIR" ]; then
    echo "Already cloned: $DEST_DIR"
    exit 0
fi

echo "Cloning VyOS documentation into $DEST_DIR ..."
git clone --depth 1 "$REPO_URL" "$DEST_DIR"
echo "Done."

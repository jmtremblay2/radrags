#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/vyos/vyos-documentation.git"
TAG="1.4.3"
DEST_DIR="$(cd "$(dirname "$0")/.." && pwd)/vendor/vyos-documentation"

if [ -d "$DEST_DIR" ]; then
    echo "Already cloned: $DEST_DIR"
    echo "Ensuring tag $TAG is checked out ..."
    git -C "$DEST_DIR" fetch --tags --quiet
    git -C "$DEST_DIR" checkout --quiet "$TAG"
    echo "Done."
    exit 0
fi

echo "Cloning VyOS documentation (tag $TAG) into $DEST_DIR ..."
git clone --branch "$TAG" --depth 1 "$REPO_URL" "$DEST_DIR"
echo "Done."

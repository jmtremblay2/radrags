#!/usr/bin/env bash
set -euo pipefail

# Check if we're in a git repo
if git rev-parse --git-dir > /dev/null 2>&1; then
    # Determine version: use tag if at an exact tag, otherwise use 0.0.0+hash
    tag=$(git describe --tags --exact-match 2>/dev/null || echo "")
    short_hash=$(git rev-parse --short HEAD)

    if [[ -n "$tag" ]]; then
        version="${tag#v}"
    else
        version="0.0.0+${short_hash}"
    fi

    # If the repo is dirty, append .dirty
    if [[ -n "$(git status --porcelain)" ]]; then
        if [[ "$version" == *"+"* ]]; then
            version="${version}.dirty"
        else
            version="${version}+dirty"
        fi
    fi
else
    echo "Warning: not a git repository, using default version"
    version="0.0.0"
fi

echo "Building radrags version: $version"

# Write version file for hatchling
cat > src/radrags/_version.py << EOF
__version__ = "$version"
EOF

# Build wheel and sdist
uv build

echo "Done. Artifacts in dist/"

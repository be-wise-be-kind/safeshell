#!/usr/bin/env bash
# Auto-increment patch version on every commit

set -e

VERSION_FILE="src/safeshell/__version__.py"

# Read current version
current_version=$(grep '__version__' "$VERSION_FILE" | cut -d'"' -f2)

# Split version into major.minor.patch
IFS='.' read -r major minor patch <<< "$current_version"

# Increment patch version
new_patch=$((patch + 1))
new_version="${major}.${minor}.${new_patch}"

# Update version file
sed -i "s/__version__ = \".*\"/__version__ = \"${new_version}\"/" "$VERSION_FILE"

# Stage the version file
git add "$VERSION_FILE"

echo "Version bumped: ${current_version} -> ${new_version}"

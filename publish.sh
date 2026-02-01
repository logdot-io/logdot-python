#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BUMP=false

for arg in "$@"; do
  case "$arg" in
    --bump) BUMP=true ;;
    *)
      echo "Usage: $0 [--bump]"
      echo "  --bump  Bump patch version before publishing"
      exit 1
      ;;
  esac
done

# Read current version from pyproject.toml
CURRENT_VERSION=$(grep -m1 '^version' pyproject.toml | sed 's/.*"\(.*\)".*/\1/')

if [ "$BUMP" = true ]; then
  IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
  NEW_PATCH=$((PATCH + 1))
  NEW_VERSION="${MAJOR}.${MINOR}.${NEW_PATCH}"

  echo "Bumping version: ${CURRENT_VERSION} -> ${NEW_VERSION}"

  sed -i "s/^version = \"${CURRENT_VERSION}\"/version = \"${NEW_VERSION}\"/" pyproject.toml
  sed -i "s/^__version__ = \"${CURRENT_VERSION}\"/__version__ = \"${NEW_VERSION}\"/" logdot/__init__.py

  CURRENT_VERSION="$NEW_VERSION"
fi

echo "Publishing logdot-io-sdk v${CURRENT_VERSION}..."

echo "Cleaning dist/..."
rm -rf dist/

echo "Building..."
python -m build

echo "Publishing to PyPI..."
twine upload dist/*

echo "Successfully published logdot-io-sdk v${CURRENT_VERSION}"

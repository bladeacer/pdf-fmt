#!/bin/sh

set -e

LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || true)
CURRENT_VERSION=$(sed -n 's/^version *= *"\([^"]*\)".*/\1/p' pyproject.toml | head -n 1)
BASE_VERSION=${LAST_TAG:-$CURRENT_VERSION}
BASE_VERSION=${BASE_VERSION#v}

PATCH_SUGGESTION=""
MINOR_SUGGESTION=""
MAJOR_SUGGESTION=""
if printf '%s\n' "$BASE_VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    MAJOR=$(printf '%s\n' "$BASE_VERSION" | cut -d. -f1)
    MINOR=$(printf '%s\n' "$BASE_VERSION" | cut -d. -f2)
    PATCH=$(printf '%s\n' "$BASE_VERSION" | cut -d. -f3)
    PATCH_SUGGESTION="$MAJOR.$MINOR.$((PATCH + 1))"
    MINOR_SUGGESTION="$MAJOR.$((MINOR + 1)).0"
    MAJOR_SUGGESTION="$((MAJOR + 1)).0.0"
else
    echo "Warning: cannot parse '$BASE_VERSION'. Version suggestions are unavailable."
fi

echo "Last tag: ${LAST_TAG:-none}"
echo "Current version: ${CURRENT_VERSION:-none}"
if [ -n "$PATCH_SUGGESTION" ]; then
    echo "From $BASE_VERSION: patch $PATCH_SUGGESTION, minor $MINOR_SUGGESTION, major $MAJOR_SUGGESTION."
fi

DEFAULT_VERSION=${CURRENT_VERSION:-$PATCH_SUGGESTION}
if [ -z "$DEFAULT_VERSION" ]; then
    echo "Error: no version can be suggested. Enter one or set pyproject.toml first. Aborting."
    exit 1
fi

printf "Enter the version to release [%s]: " "$DEFAULT_VERSION"
read VERSION_NUMBER
if [ -z "$VERSION_NUMBER" ]; then
    VERSION_NUMBER=$DEFAULT_VERSION
fi

if ! printf '%s\n' "$VERSION_NUMBER" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "Error: version must use the major.minor.patch format. Aborting."
    exit 1
fi

printf "Enter a commit message (leave empty for 'Release version %s'): " "$VERSION_NUMBER"
read COMMIT_MSG
if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Release version $VERSION_NUMBER"
fi

if [ "$(uname)" = "Darwin" ]; then
    sed -i '' "0,/version = \".*\"/s//version = \"$VERSION_NUMBER\"/" ./pyproject.toml
else
    sed -i "0,/version = \".*\"/s//version = \"$VERSION_NUMBER\"/" ./pyproject.toml
fi

echo "Updated pyproject.toml to version $VERSION_NUMBER"
echo "Committing changes: $COMMIT_MSG"
git add -A
git commit -m "$COMMIT_MSG"
git push

echo "Cleaning up local and remote tag $VERSION_NUMBER..."
git tag -d "$VERSION_NUMBER" 2>/dev/null || true
git push --delete origin "$VERSION_NUMBER" 2>/dev/null || true

echo "Creating and pushing new tag: $VERSION_NUMBER"
git tag -a "$VERSION_NUMBER" -m "$COMMIT_MSG"
git push origin "$VERSION_NUMBER"

echo "Successfully updated to $VERSION_NUMBER and pushed."

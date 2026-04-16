#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# Get the Version Number
echo "Enter the new version number (e.g., 1.0.0):"
read VERSION_NUMBER

if [ -z "$VERSION_NUMBER" ]; then
    echo "Error: Version number cannot be empty. Aborting."
    exit 1
fi

# Get the Custom Commit Message
echo "Enter a commit message (leave empty for 'Release version $VERSION_NUMBER'):"
read COMMIT_MSG

if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Release version $VERSION_NUMBER"
fi

# Update pyproject.toml
if [ "$(uname)" = "Darwin" ]; then
    sed -i '' "0,/version = \".*\"/s//version = \"$VERSION_NUMBER\"/" ./pyproject.toml
else
    sed -i "0,/version = \".*\"/s//version = \"$VERSION_NUMBER\"/" ./pyproject.toml
fi

echo "Updated pyproject.toml to version $VERSION_NUMBER"

# Git Actions
echo "Committing changes: $COMMIT_MSG"
git add -A
git commit -m "$COMMIT_MSG"
git push

echo "Cleaning up local/remote tag $VERSION_NUMBER..."
git tag -d "$VERSION_NUMBER" 2>/dev/null || true 
git push --delete origin "$VERSION_NUMBER" 2>/dev/null || true

echo "Creating and pushing new tag: $VERSION_NUMBER"
git tag -a "$VERSION_NUMBER" -m "$COMMIT_MSG"
git push origin "$VERSION_NUMBER"

echo "Successfully updated to $VERSION_NUMBER and pushed."

#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

echo "Please enter the new version number (e.g., 1.4.0):"
read VERSION_NUMBER

if [ -z "$VERSION_NUMBER" ]; then
    echo "Error: Version number cannot be empty. Aborting."
    exit 1
fi

echo "Committing all changes with version tag: $VERSION_NUMBER"
git add -A
git commit -m "Version $VERSION_NUMBER"
git push -f

echo "Attempting to delete local and remote tag $VERSION_NUMBER (if they exist)..."
git tag -d "$VERSION_NUMBER" 2>/dev/null || true 
git push --delete origin "$VERSION_NUMBER" 2>/dev/null || true

echo "Creating and pushing new tag $VERSION_NUMBER"
git tag -a "$VERSION_NUMBER" -m "$VERSION_NUMBER"
git push origin "$VERSION_NUMBER"

echo "Successfully updated and pushed version $VERSION_NUMBER."

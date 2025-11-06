#!/bin/sh
set -e

act push \
    --job build \
    --eventpath ../.github/workflows/push_tag_event.json \
    --secret GITHUB_TOKEN="<YOUR_PAT>" \
    --env GITHUB_REF=refs/tags/latest \
    --env GITHUB_SHA=$(git rev-parse HEAD) \
    -P macos-latest=nektos/act-environments-ubuntu:22.04 \
    --artifact-server-path /tmp/artifacts \
    --verbose

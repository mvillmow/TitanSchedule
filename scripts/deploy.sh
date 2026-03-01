#!/usr/bin/env bash
set -euo pipefail

BRANCH="gh-pages"
echo "Deploying web/ to $BRANCH branch..."
git subtree push --prefix web origin "$BRANCH"
echo "Deployed to GitHub Pages"

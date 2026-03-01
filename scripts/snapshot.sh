#!/usr/bin/env bash
set -euo pipefail
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
if [ ! -d "web/data" ] || [ -z "$(ls -A web/data/ 2>/dev/null | grep -v .gitkeep)" ]; then
    echo "Error: web/data/ is empty. Run scrape.sh first."
    exit 1
fi
git add web/data/
git commit -m "data: tournament snapshot $TIMESTAMP"
echo "Committed snapshot at $TIMESTAMP"

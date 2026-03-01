#!/usr/bin/env bash
set -euo pipefail
URL="${1:?Usage: ./scripts/scrape.sh <AES_DIVISION_URL>}"
echo "Scraping: $URL"
pixi run python -m scraper.cli "$URL"

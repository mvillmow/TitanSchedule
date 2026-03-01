#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8080}"
echo "Serving web/ at http://localhost:$PORT"
echo "Press Ctrl+C to stop."
pixi run python -m http.server "$PORT" --directory web/

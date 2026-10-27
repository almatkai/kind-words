#!/usr/bin/env bash
set -euo pipefail
V2_DIR="$(cd "$(dirname "$0")/.." && pwd -P)"
exec python3 "$V2_DIR/qa/run.py"

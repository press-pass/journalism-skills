#!/usr/bin/env bash
# Build the lobbying+press investigation DB from scratch. Idempotent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

DATA_DIR="${LDA_DATA_DIR:-$ROOT/.context/data/data}"
DB_PATH="${LDA_DB_PATH:-$ROOT/.context/db/investigation.duckdb}"

mkdir -p "$(dirname "$DB_PATH")"

if [ ! -d "$DATA_DIR/congress_press" ]; then
  echo "FATAL: expected $DATA_DIR/congress_press not found" >&2
  echo "Run scripts/fetch_data.sh first." >&2
  exit 2
fi

echo "[1/3] Loading press releases..."
LDA_DATA_DIR="$DATA_DIR" LDA_DB_PATH="$DB_PATH" python3 etl/load_press.py
echo "[2/3] Loading Senate filings..."
LDA_DATA_DIR="$DATA_DIR" LDA_DB_PATH="$DB_PATH" python3 etl/load_senate.py
echo "[3/3] Loading House XML..."
LDA_DATA_DIR="$DATA_DIR" LDA_DB_PATH="$DB_PATH" python3 etl/load_house.py
echo "OK: $DB_PATH"

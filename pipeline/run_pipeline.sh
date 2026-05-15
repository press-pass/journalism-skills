#!/usr/bin/env bash
# Pipeline driver: build DB → entity resolve → bill mentions → revolving door
# → press links → foreign influence → spike detection.
# Run from repo root after `lobbying-corpus-ingest` has built lobbying.duckdb.

set -euo pipefail

DB=${DB:-.context/db/lobbying.duckdb}
OUT=${OUT:-.context/findings}
mkdir -p "$OUT"

echo "[1/6] entity resolve"
python3 skills/lobbying-entity-resolve/scripts/build_entity_tables.py --db "$DB"

echo "[2/6] bill mentions"
python3 skills/lobbying-bill-extract/scripts/extract_bill_mentions.py --db "$DB"

echo "[3/6] revolving door"
python3 skills/lobbying-revolving-door/scripts/parse_covered_positions.py --db "$DB"

echo "[4/6] press links"
python3 skills/lobbying-press-link/scripts/build_press_links.py --db "$DB"

echo "[5/6] foreign influence"
python3 skills/lobbying-foreign-influence/scripts/build_foreign_influence.py --db "$DB"

echo "[6/6] spike detection"
python3 skills/lobbying-issue-spike/scripts/detect_spikes.py --db "$DB" --out "$OUT" --min-income 250000 --top 100

echo "Pipeline complete. Findings tables + CSVs in $OUT"

---
name: lobbying-corpus-ingest
description: Ingest the GAIN corpus (Senate JSON, House XML, Congressional press JSONL) into a single deterministic DuckDB database for fast, reproducible analysis. Use when starting any investigation against the lobbying + press-release corpus described in data_manual.md.
---

# Ingest the lobbying + press corpus into DuckDB

This skill turns the raw GAIN corpus into a single queryable DuckDB database.
Every analytic skill in this plugin assumes this database exists. Run this once
per machine; downstream skills read `lobbying.duckdb` directly.

## When to use

- Starting a new investigation against the Senate/House LDA + Congress press corpus
- Re-running analyses with a fresh extract or after the manual updates the layout
- Verifying claims that depend on counts/sums (use raw SQL against this DB)

## Inputs

A decompressed `data/` directory exactly as described in `data_manual.md`:

```
data/
  congress_press/{YYYY/YYYY-MM.jsonl, 2026-MM.jsonl}
  senate/{YYYY/{filings, contributions}/*.json, constants/*.json}
  house/{YYYY_Registrations_XML, YYYY_{1st,2nd,3rd,4th}Quarter_XML}/*.xml
```

## Steps

1. Verify Python ≥3.11 and DuckDB Python package: `python3 -c "import duckdb"`.
   Install with `pip install duckdb` if missing.

2. Build the database. From the repo root:

   ```bash
   python3 skills/lobbying-corpus-ingest/scripts/build_db.py \
     --data-root <path/to/data> \
     --db <path/to/lobbying.duckdb>
   ```

   Selective rebuilds via `--skip senate-filings|senate-contributions|house|press|constants`.

3. Sanity-check the build:

   ```bash
   duckdb <path>/lobbying.duckdb -c "
     SELECT 'senate_filings' AS t, count(*) FROM senate_filings UNION ALL
     SELECT 'senate_activities', count(*) FROM senate_activities UNION ALL
     SELECT 'senate_lobbyists', count(*) FROM senate_lobbyists UNION ALL
     SELECT 'senate_contribution_items', count(*) FROM senate_contribution_items UNION ALL
     SELECT 'house_filings', count(*) FROM house_filings UNION ALL
     SELECT 'house_lobbyists', count(*) FROM house_lobbyists UNION ALL
     SELECT 'press_releases', count(*) FROM press_releases;
   "
   ```

   Expected magnitudes per `data_manual.md`: ~100K Senate filings/year, ~108K
   House records/year, ~48K press releases in 2025.

## Output schema

See `references/schema.md` for full column lists and `references/queries.md`
for canned SQL patterns the other skills depend on.

## Verifiability contract

Every row carries its source-of-record:

- Senate filings → `filing_uuid` (joins to lda.senate.gov)
- House filings → `house_file` (the original XML filename, joins to
  `disclosurespreview.house.gov`)
- Press releases → `url` (joins back to the original `*.house.gov` /
  `*.senate.gov` page)

Any downstream finding MUST quote one of these identifiers so an evaluator can
audit it.

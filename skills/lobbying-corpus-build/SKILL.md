---
description: Build a unified parquet corpus from Senate JSON + House XML Lobbying Disclosure Act filings, ready for cross-corpus queries. Use when the user wants to analyze lobbying disclosures, find spending outliers, or join lobbying activity to congressional press releases. Input: paths to raw Senate + House data directories.
---

You normalize the two parallel Lobbying Disclosure Act corpuses — the Senate's JSON files
(`filings_{YEAR}.json`, `contributions_{YEAR}.json`) and the House Clerk's hundreds of thousands of
XML files (`*_Quarter_XML/*.xml`, `*_Registrations_XML/*.xml`) — into a unified set of parquet
tables that can be queried with DuckDB or Polars in seconds.

The skill emphasizes:
- **Verifiability**: every row carries the original `filing_uuid` (Senate) or `house_filing_id` +
  `filing_dir` (House) so any chart datapoint can be traced back to the originating filing.
- **Efficiency**: streaming XML parse, batched parquet writes (~5 minutes total on 6 GB of data).
- **Reproducibility**: ships a Docker image (`lobbypress-analysis`) with pinned deps and a single
  invocation per dataset.

## Inputs

The user must supply two paths (defaults below match the GAIN challenge layout):

- `--senate_root` — directory containing `{YEAR}/filings/filings_{YEAR}.json` and
  `{YEAR}/contributions/contributions_{YEAR}.json`. Default: `data/senate`.
- `--house_root` — directory containing `{YEAR}_{Quarter}_XML/*.xml` and `{YEAR}_Registrations_XML/*.xml`.
  Default: `data/house`.

If the data is the GAIN corpus, point both at `data/` (which contains both subdirectories).

## Step 1: Build the analysis Docker image (one-time)

```bash
docker build -t lobbypress-analysis - <<'EOF'
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev libxslt1-dev build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir \
    pandas==2.2.2 polars==1.5.0 duckdb==1.1.1 lxml==5.2.2 orjson==3.10.6 \
    pyarrow==17.0.0 fastparquet==2024.5.0 rapidfuzz==3.9.4 tqdm==4.66.4
EOF
```

Skip this if `docker image inspect lobbypress-analysis` already returns a result.

## Step 2: Run the Senate ETL

```bash
docker run --rm \
  -v "$(realpath <SENATE_ROOT>):/data/senate:ro" \
  -v "$(realpath <OUT_PARQUET_DIR>):/parquet" \
  -v "$(realpath skills/lobbying-corpus-build/scripts):/scripts:ro" \
  lobbypress-analysis \
  python /scripts/etl_senate.py --senate_root /data/senate --out_dir /parquet
```

Writes five tables:

| Table | Grain | Notes |
|---|---|---|
| `senate_filings.parquet` | one row per filing | includes `income`, `expenses`, `client_name`, `registrant_name`, `foreign_entity_names` |
| `senate_activities.parquet` | one row per `lobbying_activity` inside a filing | `issue_code` (ALI), `description`, denormalized client/registrant |
| `senate_lobbyists.parquet` | one row per lobbyist × activity | includes `covered_position` revolving-door text |
| `senate_contrib_filings.parquet` | one row per LD-203 filing | summary counts |
| `senate_contrib_items.parquet` | one row per contribution line item | `payee`, `honoree`, `amount`, `date` |

## Step 3: Run the House ETL

```bash
docker run --rm \
  -v "$(realpath <HOUSE_ROOT>):/data/house:ro" \
  -v "$(realpath <OUT_PARQUET_DIR>):/parquet" \
  -v "$(realpath skills/lobbying-corpus-build/scripts):/scripts:ro" \
  lobbypress-analysis \
  python /scripts/etl_house.py --house_root /data/house --out_dir /parquet
```

Writes three tables (`house_filings.parquet`, `house_activities.parquet`, `house_lobbyists.parquet`)
that mirror the Senate schema, plus House-only fields (`report_type`, `signed_date`, `no_lobbying`,
`senate_id`/`house_id` cross-walk).

## Step 4: Sanity-check the output

```bash
docker run --rm -v "$(realpath <OUT_PARQUET_DIR>):/parquet:ro" lobbypress-analysis python -c "
import polars as pl
for nm in ['senate_filings','senate_activities','senate_lobbyists',
          'senate_contrib_filings','senate_contrib_items',
          'house_filings','house_activities','house_lobbyists']:
    df = pl.read_parquet(f'/parquet/{nm}.parquet')
    print(f'{nm:30s} rows={df.height:>10,}  cols={len(df.columns)}')
"
```

Expected counts for the 2022 Q1 – 2026 Q1 corpus (approximate):

| Table | Rows |
|---|---|
| senate_filings | ~418K |
| senate_activities | ~800K |
| senate_lobbyists | ~2.1M |
| senate_contrib_items | ~640K |
| house_filings | ~410K |
| house_activities | ~785K |
| house_lobbyists | ~640K |

If any of these are an order of magnitude off, re-run the ETL after confirming the source data
is fully decompressed.

## Outputs

Parquet files compressed with zstd, queryable directly with:

```python
import polars as pl
filings = pl.read_parquet("/parquet/senate_filings.parquet")
```

or DuckDB:

```python
import duckdb
con = duckdb.connect()
con.execute("CREATE VIEW filings AS SELECT * FROM '/parquet/senate_filings.parquet'")
```

## Caveats — make sure the user knows these

- Income/expenses are self-reported and frequently NULL on registrations and termination filings.
- House and Senate report the *same* engagement separately; deduplicate via the `senateID`/
  `houseID` fields before computing per-engagement totals.
- House XML files have many empty `<lobbyist>` slots (up to 18 per filing); the ETL drops blank rows.
- 2026 is partial: Senate = Q1 only; House = Q1 + first batch of 2026 registrations as of 2026-03-31.

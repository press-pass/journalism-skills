---
description: Normalize the Congress Press JSONL corpus into a single parquet table keyed by bioguide_id, ready for keyword search and cross-corpus joins. Use when the user wants to analyze congressional press releases at scale or join press output to lobbying data. Input: directory of {YYYY-MM}.jsonl files.
---

You ingest the [Congress Press](https://thescoop.org/congress-press/) JSONL release dumps into a
single parquet table with normalized member metadata and pre-lowercased text columns for fast
substring search.

## Inputs

- `--press_root` — directory containing `{YYYY}-{MM}.jsonl` files (optionally inside year
  subdirectories `2022/`, `2023/`, etc). Default in the GAIN corpus: `data/congress_press`.

## Step 1: Build the analysis Docker image (one-time)

If it doesn't exist yet, build the shared `lobbypress-analysis` image (see
`lobbying-corpus-build` skill — same image is reused). Otherwise skip.

## Step 2: Run the press ETL

```bash
docker run --rm \
  -v "$(realpath <PRESS_ROOT>):/data/congress_press:ro" \
  -v "$(realpath <OUT_PARQUET_DIR>):/parquet" \
  -v "$(realpath skills/press-corpus-build/scripts):/scripts:ro" \
  lobbypress-analysis \
  python /scripts/etl_press.py --press_root /data/congress_press --out /parquet/press.parquet
```

Writes one parquet table:

| Column | Type | Notes |
|---|---|---|
| `url` | str | canonical release URL |
| `title` | str | release headline |
| `date` | str | `YYYY-MM-DD` (member-site reported) |
| `domain` | str | e.g. `warren.senate.gov` |
| `bioguide_id` | str | join key to lobbying analyses / Congress.gov |
| `member_name` | str | display name |
| `party` | str | `Democrat`/`Republican`/`Independent` |
| `state` | str | 2-letter, includes territories (MP, GU, ...) |
| `chamber` | str | `House`/`Senate` |
| `text` | str | full release body |
| `title_lc` / `text_lc` | str | lowercased copies for substring matching |
| `word_count` | int | rough word count |

## Step 3: Sanity-check coverage

```bash
docker run --rm -v "$(realpath <OUT_PARQUET_DIR>):/parquet:ro" lobbypress-analysis python -c "
import polars as pl
p = pl.read_parquet('/parquet/press.parquet')
print('total releases:', p.height)
print('by year:'); print(p.with_columns(pl.col('date').str.slice(0,4).alias('y')).group_by('y').len().sort('y'))
print('by chamber:'); print(p['chamber'].value_counts())
print('per-month range:')
print(p.with_columns(pl.col('date').str.slice(0,7).alias('ym')).group_by('ym').len().sort('ym').head(60))
"
```

For 2022 Q1 – 2026 Q1 expect ~141K releases. Look for **scraper gaps**: any month with <800
releases is suspect (e.g., 2024-11 in the GAIN corpus has only 374 — flag and exclude when
computing trend lines).

## Step 4: Quick keyword search example

```python
import polars as pl
p = pl.read_parquet("/parquet/press.parquet")
# All releases mentioning a topic, by member
hits = (
    p.filter(pl.col("text_lc").str.contains("artificial intelligence"))
     .group_by(["bioguide_id", "member_name", "party"]).len()
     .sort("len", descending=True)
)
print(hits.head(20))
```

## Caveats — tell the user

- `date_source = scraper` for every record — Congress press dates are inferred from the page,
  not parsed from any authoritative timestamp. Off-by-one-day errors happen near midnight.
- Some scrapers occasionally drop a month entirely (e.g., 2024-11 was incompletely scraped).
  Always inspect the monthly count series before drawing trend conclusions.
- `text` body sometimes contains boilerplate footers ("###", "Background", office addresses).
  Strip those before doing semantic similarity work.
- A few records have `null` `member`/`chamber` — they're scraping anomalies and should be
  excluded with `pl.col("bioguide_id").is_not_null()` when joining.

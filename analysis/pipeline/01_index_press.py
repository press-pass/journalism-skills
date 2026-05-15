"""Index Congress press releases into Parquet.

Reads every JSONL file under /data/congress_press, normalizes member metadata,
and writes a partitioned-by-year Parquet store at /parquet/press/.

Run from container: python analysis/pipeline/01_index_press.py
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
PARQUET_DIR = Path(os.environ.get("PARQUET_DIR", "/parquet"))


def main() -> None:
    src = DATA_DIR / "congress_press"
    out = PARQUET_DIR / "press"
    out.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("PRAGMA threads=8")

    # Glob all JSONL files: 2022-2025 are under year subdirs, 2026 at root
    paths = sorted([str(p) for p in src.rglob("*.jsonl")])
    print(f"Found {len(paths)} JSONL files")

    # DuckDB read_json_auto handles JSONL with format='newline_delimited'
    # We standardize the schema and write one Parquet per year for partitioned reads.
    con.execute(
        f"""
        CREATE OR REPLACE TABLE press AS
        SELECT
            url,
            title,
            CAST(date AS DATE) AS date,
            date_source,
            source,
            domain,
            scraper,
            member.bioguide_id AS bioguide_id,
            member.name AS member_name,
            member.party AS party,
            member.state AS state,
            member.chamber AS chamber,
            text,
            length(text) AS text_len,
            EXTRACT(YEAR FROM CAST(date AS DATE)) AS year,
            EXTRACT(MONTH FROM CAST(date AS DATE)) AS month
        FROM read_json_auto({paths!r}, format='newline_delimited', union_by_name=true)
        """
    )

    # Stats
    n = con.execute("SELECT COUNT(*) FROM press").fetchone()[0]
    members = con.execute("SELECT COUNT(DISTINCT bioguide_id) FROM press").fetchone()[0]
    yr_min, yr_max = con.execute(
        "SELECT MIN(year), MAX(year) FROM press WHERE year IS NOT NULL"
    ).fetchone()
    print(f"Loaded {n:,} press releases from {members:,} members, years {yr_min}-{yr_max}")

    # Partition by year for efficient downstream queries
    con.execute(
        f"COPY press TO '{out}' (FORMAT PARQUET, PARTITION_BY (year), OVERWRITE_OR_IGNORE)"
    )
    print(f"Wrote partitioned Parquet to {out}")


if __name__ == "__main__":
    main()

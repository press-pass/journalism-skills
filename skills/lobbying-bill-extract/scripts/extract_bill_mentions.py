#!/usr/bin/env python3
"""Extract bill numbers from lobbying descriptions and press releases using
DuckDB's regex functions (no negative lookaheads — supported subset of PCRE).

The patterns prefer the dotted forms ("H.R. 1234", "S. 1234") because that is
how the LDA filings overwhelmingly format bill numbers. False positives from
ambiguous "S 1234" style citations are intentionally avoided.
"""
from __future__ import annotations
import argparse
import time
import duckdb


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


# Each capture is the full bill citation. We post-process kind & number with
# additional regex_extract calls per row.
BILL_RE = (
    r"(?i)\b("
    r"H\.\s*J\.\s*Res\.\s*\d{1,5}"
    r"|S\.\s*J\.\s*Res\.\s*\d{1,5}"
    r"|H\.\s*Con\.\s*Res\.\s*\d{1,5}"
    r"|S\.\s*Con\.\s*Res\.\s*\d{1,5}"
    r"|H\.\s*Res\.\s*\d{1,5}"
    r"|S\.\s*Res\.\s*\d{1,5}"
    r"|H\.\s*R\.\s*\d{1,5}"
    r"|S\.\s*\d{1,5}"
    r")\b"
)
KIND_RE = (
    r"(?i)^(H\.\s*J\.\s*Res\.|S\.\s*J\.\s*Res\.|H\.\s*Con\.\s*Res\.|S\.\s*Con\.\s*Res\.|H\.\s*Res\.|S\.\s*Res\.|H\.\s*R\.|S\.)"
)
NUM_RE = r"(\d{1,5})$"

NORMALIZE_KIND = (
    "CASE upper(regexp_replace(kind_raw, '[ \\.]+', '', 'g'))"
    " WHEN 'HJRES' THEN 'HJRES'"
    " WHEN 'SJRES' THEN 'SJRES'"
    " WHEN 'HCONRES' THEN 'HCONRES'"
    " WHEN 'SCONRES' THEN 'SCONRES'"
    " WHEN 'HRES' THEN 'HRES'"
    " WHEN 'SRES' THEN 'SRES'"
    " WHEN 'HR' THEN 'HR'"
    " WHEN 'S' THEN 'S'"
    " ELSE upper(regexp_replace(kind_raw, '[ \\.]+', '', 'g'))"
    "END"
)
CONGRESS = (
    "CASE WHEN filing_year BETWEEN 2021 AND 2022 THEN '117-'"
    "     WHEN filing_year BETWEEN 2023 AND 2024 THEN '118-'"
    "     WHEN filing_year BETWEEN 2025 AND 2026 THEN '119-'"
    "     ELSE 'unk-' END"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()
    con = duckdb.connect(args.db)
    con.execute("""
        DROP TABLE IF EXISTS bill_mentions_lobbying;
        CREATE TABLE bill_mentions_lobbying (
            source VARCHAR,
            filing_uuid VARCHAR,
            house_file VARCHAR,
            filing_year INTEGER,
            bill_id VARCHAR,
            bill_kind VARCHAR,
            bill_number VARCHAR,
            raw_match VARCHAR
        );
        DROP TABLE IF EXISTS bill_mentions_press;
        CREATE TABLE bill_mentions_press (
            url VARCHAR,
            bioguide_id VARCHAR,
            date DATE,
            filing_year INTEGER,
            bill_id VARCHAR,
            bill_kind VARCHAR,
            bill_number VARCHAR,
            raw_match VARCHAR
        );
    """)

    log("Senate activities")
    con.execute(f"""
        INSERT INTO bill_mentions_lobbying
        WITH exploded AS (
            SELECT
                a.filing_uuid,
                f.filing_year,
                unnest(regexp_extract_all(a.description, $bill$, 1)) AS raw
            FROM senate_activities a
            JOIN senate_filings f USING (filing_uuid)
            WHERE a.description IS NOT NULL
              AND length(a.description) > 0
              AND regexp_matches(a.description, $bill$)
        ),
        parsed AS (
            SELECT filing_uuid, filing_year, raw,
                   regexp_extract(raw, $kind$, 1) AS kind_raw,
                   regexp_extract(raw, $num$, 1) AS bill_number
            FROM exploded
        )
        SELECT
            'senate', filing_uuid, NULL, filing_year,
            {CONGRESS} || {NORMALIZE_KIND} || '-' || bill_number AS bill_id,
            {NORMALIZE_KIND} AS bill_kind,
            bill_number, raw
        FROM parsed
        WHERE bill_number != ''
    """.replace("$bill$", f"'{BILL_RE}'").replace("$kind$", f"'{KIND_RE}'").replace("$num$", f"'{NUM_RE}'"))
    n = con.execute("SELECT COUNT(*) FROM bill_mentions_lobbying WHERE source='senate'").fetchone()[0]
    log(f"  senate: {n:,}")

    log("House activities")
    con.execute(f"""
        INSERT INTO bill_mentions_lobbying
        WITH exploded AS (
            SELECT
                a.house_file,
                h.filing_year,
                unnest(regexp_extract_all(a.description, $bill$, 1)) AS raw
            FROM house_activities a
            JOIN house_filings h USING (house_file)
            WHERE a.description IS NOT NULL
              AND length(a.description) > 0
              AND regexp_matches(a.description, $bill$)
        ),
        parsed AS (
            SELECT house_file, filing_year, raw,
                   regexp_extract(raw, $kind$, 1) AS kind_raw,
                   regexp_extract(raw, $num$, 1) AS bill_number
            FROM exploded
        )
        SELECT
            'house', NULL, house_file, filing_year,
            {CONGRESS} || {NORMALIZE_KIND} || '-' || bill_number AS bill_id,
            {NORMALIZE_KIND} AS bill_kind,
            bill_number, raw
        FROM parsed
        WHERE bill_number != ''
    """.replace("$bill$", f"'{BILL_RE}'").replace("$kind$", f"'{KIND_RE}'").replace("$num$", f"'{NUM_RE}'"))
    n = con.execute("SELECT COUNT(*) FROM bill_mentions_lobbying WHERE source='house'").fetchone()[0]
    log(f"  house: {n:,}")

    log("Press releases")
    con.execute(f"""
        INSERT INTO bill_mentions_press
        WITH exploded AS (
            SELECT url, bioguide_id, date,
                   EXTRACT(YEAR FROM date)::INTEGER AS filing_year,
                   unnest(regexp_extract_all(text, $bill$, 1)) AS raw
            FROM press_releases
            WHERE text IS NOT NULL AND length(text) > 50
              AND regexp_matches(text, $bill$)
        ),
        parsed AS (
            SELECT url, bioguide_id, date, filing_year, raw,
                   regexp_extract(raw, $kind$, 1) AS kind_raw,
                   regexp_extract(raw, $num$, 1) AS bill_number
            FROM exploded
        )
        SELECT
            url, bioguide_id, date, filing_year,
            {CONGRESS} || {NORMALIZE_KIND} || '-' || bill_number AS bill_id,
            {NORMALIZE_KIND} AS bill_kind,
            bill_number, raw
        FROM parsed
        WHERE bill_number != ''
    """.replace("$bill$", f"'{BILL_RE}'").replace("$kind$", f"'{KIND_RE}'").replace("$num$", f"'{NUM_RE}'"))
    n = con.execute("SELECT COUNT(*) FROM bill_mentions_press").fetchone()[0]
    log(f"  press: {n:,}")

    log("Indexes")
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_bmlobb_bill ON bill_mentions_lobbying(bill_id);
        CREATE INDEX IF NOT EXISTS idx_bmpress_bill ON bill_mentions_press(bill_id);
        CREATE INDEX IF NOT EXISTS idx_bmpress_date ON bill_mentions_press(date);
        ANALYZE;
    """)
    log("Done.")


if __name__ == "__main__":
    main()

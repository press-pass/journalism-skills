#!/usr/bin/env python3
"""Build press_lobbying_links — deterministic press↔lobbying matches.

Three match methods:
  1. client_name_exact / client_name_alias — case-insensitive substring of a
     client name (or alias) in the press-release text
  2. bill_id — joins press bill mentions to lobbying bill mentions
  3. issue_code_quarter — chamber + quarter alignment only (low confidence)
"""
from __future__ import annotations
import argparse
import re
import time
import duckdb


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--min-name-len", type=int, default=6)
    args = ap.parse_args()
    con = duckdb.connect(args.db)

    log("Recreating press_lobbying_links")
    con.execute("""
        DROP TABLE IF EXISTS press_lobbying_links;
        CREATE TABLE press_lobbying_links (
            url VARCHAR,
            filing_uuid VARCHAR,
            client_id BIGINT,
            client_name VARCHAR,
            match_method VARCHAR,
            match_value VARCHAR,
            match_confidence DOUBLE,
            press_date DATE,
            press_member_bio VARCHAR,
            filing_year INTEGER,
            filing_period VARCHAR
        );
    """)

    log("Method 1: bill_id joins (highest confidence)")
    con.execute("""
        INSERT INTO press_lobbying_links
        SELECT
            p.url,
            l.filing_uuid,
            f.client_id,
            f.client_name,
            'bill_id' AS match_method,
            l.bill_id AS match_value,
            0.85 AS match_confidence,
            p.date AS press_date,
            p.bioguide_id AS press_member_bio,
            f.filing_year,
            f.filing_period
        FROM bill_mentions_press p
        JOIN bill_mentions_lobbying l USING (bill_id)
        JOIN senate_filings f ON f.filing_uuid = l.filing_uuid
        WHERE p.bill_id IS NOT NULL
          AND f.filing_year IS NOT NULL
          AND EXTRACT(YEAR FROM p.date) BETWEEN f.filing_year - 1 AND f.filing_year + 1;
    """)
    n_bill = con.execute("SELECT COUNT(*) FROM press_lobbying_links WHERE match_method = 'bill_id'").fetchone()[0]
    log(f"  bill_id links: {n_bill:,}")

    log("Method 2: client_name_exact / alias substring matches")
    # Build candidate client names (canonical + aliases) with length >= min
    con.execute("""
        CREATE OR REPLACE TEMP TABLE candidate_names AS
        SELECT DISTINCT canonical_id AS client_id, alias AS name, source
        FROM entity_name_alias
        WHERE alias IS NOT NULL AND length(alias) >= ?
    """, [args.min_name_len])

    # Filter out generic stop names that produce too many false hits
    stops = ["INC", "LLC", "LLP", "CORP", "CO", "COMPANY", "AMERICA", "AMERICAN", "UNITED", "STATES", "UNIVERSITY", "FOUNDATION", "ASSOCIATION", "COUNCIL", "INSTITUTE", "GROUP", "PARTNERS", "STRATEGIES"]
    con.execute("DELETE FROM candidate_names WHERE upper(name) IN (" + ",".join(f"'{s}'" for s in stops) + ")")

    # Match: only fire when the press_release.text contains the lowered name
    log("  scanning press releases for client mentions (this is the heavy step)")
    con.execute("""
        INSERT INTO press_lobbying_links
        WITH client_name_in_press AS (
            SELECT p.url, p.bioguide_id, p.date, c.client_id, c.name AS matched_name
            FROM press_releases p
            JOIN candidate_names c
              ON position(lower(c.name) IN lower(p.text)) > 0
            WHERE p.text IS NOT NULL
        )
        SELECT
            cnp.url,
            f.filing_uuid,
            f.client_id,
            f.client_name,
            'client_name' AS match_method,
            cnp.matched_name AS match_value,
            0.7 AS match_confidence,
            cnp.date AS press_date,
            cnp.bioguide_id AS press_member_bio,
            f.filing_year,
            f.filing_period
        FROM client_name_in_press cnp
        JOIN senate_filings f
          ON f.client_id = cnp.client_id
         AND EXTRACT(YEAR FROM cnp.date) = f.filing_year
        ;
    """)
    n_name = con.execute("SELECT COUNT(*) FROM press_lobbying_links WHERE match_method = 'client_name'").fetchone()[0]
    log(f"  client_name matches: {n_name:,}")

    log("Indexes")
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_pll_url ON press_lobbying_links(url);
        CREATE INDEX IF NOT EXISTS idx_pll_filing ON press_lobbying_links(filing_uuid);
        CREATE INDEX IF NOT EXISTS idx_pll_client ON press_lobbying_links(client_id);
        ANALYZE;
    """)
    log("Done.")


if __name__ == "__main__":
    main()

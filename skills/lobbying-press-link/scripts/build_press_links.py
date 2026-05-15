#!/usr/bin/env python3
"""Build press_lobbying_links — deterministic press↔lobbying matches.

This v2 prioritises the highest-signal joins so the table is useful in
seconds rather than hours.

Methods (in priority order):

1. **bill_id** — joins via `bill_mentions_press.bill_id` ↔
   `bill_mentions_lobbying.bill_id`. Highest confidence.
2. **client_name** — exact substring of the *top-K* most-active client names
   in the press release text, restricted to names that contain at least one
   token >= 6 chars long. Limit to top-K avoids the O(141K × 41K) blow-up
   and keeps the build deterministic.
"""
from __future__ import annotations
import argparse
import time
import duckdb


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--client-topk", type=int, default=400,
                    help="Limit client-name matching to the top-K most-active clients by filings")
    ap.add_argument("--min-token-len", type=int, default=7)
    ap.add_argument("--skip-name-match", action="store_true",
                    help="Skip client-name substring matching; only build bill_id links")
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

    log("Method 1: bill_id joins")
    con.execute("""
        INSERT INTO press_lobbying_links
        SELECT DISTINCT
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
        WHERE l.source = 'senate'
          AND p.bill_id IS NOT NULL
          AND f.filing_year IS NOT NULL
          AND EXTRACT(YEAR FROM p.date) BETWEEN f.filing_year - 1 AND f.filing_year + 1;
    """)
    n_bill = con.execute("SELECT COUNT(*) FROM press_lobbying_links WHERE match_method='bill_id'").fetchone()[0]
    log(f"  bill_id links: {n_bill:,}")

    if args.skip_name_match:
        log("Skipping client-name matching (--skip-name-match set)")
    else:
        _name_match(con, args)
    log("Indexes")
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_pll_url ON press_lobbying_links(url);
        CREATE INDEX IF NOT EXISTS idx_pll_filing ON press_lobbying_links(filing_uuid);
        CREATE INDEX IF NOT EXISTS idx_pll_client ON press_lobbying_links(client_id);
        ANALYZE;
    """)
    log("Done.")


def _name_match(con, args):
    log("Method 2: top-K client-name substring matches")
    log(f"  Selecting top {args.client_topk} clients by filing count")
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE top_clients AS
        SELECT client_id, client_name,
               upper(regexp_replace(client_name, '[^a-zA-Z0-9 ]', '', 'g')) AS norm_name,
               COUNT(*) AS n_filings
        FROM senate_filings
        WHERE client_id IS NOT NULL
          AND client_name IS NOT NULL
          AND length(client_name) >= 6
        GROUP BY 1, 2
        ORDER BY n_filings DESC
        LIMIT {args.client_topk}
    """)
    # Filter out names whose tokens are all <min_token_len chars
    con.execute(f"""
        DELETE FROM top_clients
        WHERE NOT regexp_matches(norm_name, '[A-Z]{{{args.min_token_len},}}')
    """)
    # Filter out generic stop names that produce too many false hits
    stops = ["INC","LLC","LLP","CORP","CO","COMPANY","AMERICA","AMERICAN","UNITED","STATES",
             "UNIVERSITY","FOUNDATION","ASSOCIATION","COUNCIL","INSTITUTE","GROUP",
             "PARTNERS","STRATEGIES","SERVICES","SOLUTIONS","HOLDINGS","INTERNATIONAL"]
    con.execute("DELETE FROM top_clients WHERE upper(client_name) IN (" + ",".join(f"'{s}'" for s in stops) + ")")
    n_top = con.execute("SELECT COUNT(*) FROM top_clients").fetchone()[0]
    log(f"  candidates after filtering: {n_top:,}")

    # Build cartesian-style match via cross join, limited by client_topk
    log("  scanning press releases for top-client mentions")
    con.execute("""
        INSERT INTO press_lobbying_links
        SELECT DISTINCT
            p.url,
            f.filing_uuid,
            tc.client_id,
            tc.client_name,
            'client_name' AS match_method,
            tc.client_name AS match_value,
            0.7 AS match_confidence,
            p.date AS press_date,
            p.bioguide_id AS press_member_bio,
            f.filing_year,
            f.filing_period
        FROM top_clients tc
        JOIN press_releases p
          ON p.text IS NOT NULL
         AND position(lower(tc.client_name) IN lower(p.text)) > 0
        JOIN senate_filings f
          ON f.client_id = tc.client_id
         AND EXTRACT(YEAR FROM p.date) = f.filing_year;
    """)
    n_name = con.execute("SELECT COUNT(*) FROM press_lobbying_links WHERE match_method='client_name'").fetchone()[0]
    log(f"  client_name matches: {n_name:,}")


if __name__ == "__main__":
    main()

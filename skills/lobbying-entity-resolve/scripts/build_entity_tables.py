#!/usr/bin/env python3
"""Build deterministic Senate↔House entity bridge tables in the DuckDB.

Run after `lobbying-corpus-ingest`. Writes three new tables to the same DB:
  entity_registrants, entity_clients, entity_name_alias

The script is idempotent — re-running drops and rebuilds the entity tables.
"""
from __future__ import annotations
import argparse
import time
import duckdb


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()
    con = duckdb.connect(args.db)

    log("Dropping any existing entity tables")
    con.execute("""
        DROP TABLE IF EXISTS entity_registrants;
        DROP TABLE IF EXISTS entity_clients;
        DROP TABLE IF EXISTS entity_name_alias;
    """)

    log("Building entity_registrants")
    con.execute("""
        CREATE TABLE entity_registrants AS
        WITH senate_reg AS (
            SELECT
                registrant_id AS senate_registrant_id,
                MAX(registrant_house_id) AS house_registrant_id,
                MAX(registrant_name) AS canonical_name,
                upper(regexp_replace(MAX(registrant_name), '[^a-zA-Z0-9 ]', '', 'g')) AS normalized_name,
                COUNT(*) AS n_senate_filings
            FROM senate_filings
            WHERE registrant_id IS NOT NULL
            GROUP BY registrant_id
        ),
        house_reg AS (
            SELECT
                senate_registrant_id,
                MAX(organization_name) AS house_org_name,
                upper(regexp_replace(MAX(organization_name), '[^a-zA-Z0-9 ]', '', 'g')) AS house_norm,
                COUNT(*) AS n_house_filings
            FROM house_filings
            WHERE senate_registrant_id IS NOT NULL
            GROUP BY senate_registrant_id
        )
        SELECT
            COALESCE(s.senate_registrant_id, h.senate_registrant_id) AS canonical_id,
            COALESCE(s.senate_registrant_id, h.senate_registrant_id) AS senate_registrant_id,
            s.house_registrant_id,
            COALESCE(s.canonical_name, h.house_org_name) AS canonical_name,
            COALESCE(s.normalized_name, h.house_norm) AS normalized_name,
            COALESCE(s.n_senate_filings, 0) AS n_senate_filings,
            COALESCE(h.n_house_filings, 0) AS n_house_filings
        FROM senate_reg s
        FULL OUTER JOIN house_reg h USING (senate_registrant_id);
    """)
    n = con.execute("SELECT COUNT(*) FROM entity_registrants").fetchone()[0]
    log(f"  entity_registrants: {n:,}")

    log("Building entity_clients")
    con.execute("""
        CREATE TABLE entity_clients AS
        WITH senate_cli AS (
            SELECT
                client_id,
                MAX(client_name) AS canonical_name,
                upper(regexp_replace(MAX(client_name), '[^a-zA-Z0-9 ]', '', 'g')) AS normalized_name,
                STRING_AGG(DISTINCT client_country, ',') AS countries,
                COUNT(*) AS n_senate_filings
            FROM senate_filings
            WHERE client_id IS NOT NULL
            GROUP BY client_id
        ),
        house_cli_by_id AS (
            SELECT
                regexp_replace(h.senate_id, '^[0-9]+-', '') AS senate_client_id_str,
                COUNT(*) AS n_house_filings
            FROM house_filings h
            WHERE h.senate_id IS NOT NULL AND h.senate_id LIKE '%-%'
            GROUP BY 1
        )
        SELECT
            s.client_id AS canonical_id,
            s.canonical_name,
            s.normalized_name,
            s.countries,
            s.n_senate_filings,
            COALESCE(h.n_house_filings, 0) AS n_house_filings
        FROM senate_cli s
        LEFT JOIN house_cli_by_id h
            ON h.senate_client_id_str = s.client_id::VARCHAR;
    """)
    n = con.execute("SELECT COUNT(*) FROM entity_clients").fetchone()[0]
    log(f"  entity_clients: {n:,}")

    log("Building entity_name_alias (registrants + clients)")
    con.execute("""
        CREATE TABLE entity_name_alias AS
        SELECT canonical_id, canonical_name AS alias, 'senate_registrant_name' AS source
        FROM entity_registrants
        WHERE canonical_name IS NOT NULL
        UNION ALL
        SELECT
            r.canonical_id,
            h.organization_name AS alias,
            'house_org_name' AS source
        FROM entity_registrants r
        JOIN house_filings h ON h.senate_registrant_id = r.canonical_id
        WHERE h.organization_name IS NOT NULL AND h.organization_name != r.canonical_name
        UNION ALL
        SELECT canonical_id, canonical_name AS alias, 'senate_client_name' AS source
        FROM entity_clients
        WHERE canonical_name IS NOT NULL;
    """)
    n = con.execute("SELECT COUNT(*) FROM entity_name_alias").fetchone()[0]
    log(f"  entity_name_alias: {n:,}")

    log("Indexes")
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_reg_canonical ON entity_registrants(canonical_id);
        CREATE INDEX IF NOT EXISTS idx_cli_canonical ON entity_clients(canonical_id);
        CREATE INDEX IF NOT EXISTS idx_alias_canon ON entity_name_alias(canonical_id);
        CREATE INDEX IF NOT EXISTS idx_alias_name ON entity_name_alias(alias);
        ANALYZE;
    """)
    log("Done.")


if __name__ == "__main__":
    main()

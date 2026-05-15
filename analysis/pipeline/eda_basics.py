"""Initial EDA across the three corpora to find chart angles."""
from __future__ import annotations

import os
from pathlib import Path

import duckdb

PARQUET_DIR = Path(os.environ.get("PARQUET_DIR", "/parquet"))


def q(con, sql: str, n: int = 20) -> None:
    rows = con.execute(sql).fetchall()
    cols = [d[0] for d in con.description]
    print("  " + " | ".join(cols))
    print("  " + "-" * 80)
    for r in rows[:n]:
        print("  " + " | ".join(str(x)[:50] for x in r))
    print()


def main() -> None:
    con = duckdb.connect()
    con.execute("PRAGMA threads=8")
    con.execute("SET memory_limit='16GB'")

    # Build views
    con.execute(f"""
        CREATE VIEW press AS SELECT * FROM read_parquet('{PARQUET_DIR}/press/**/*.parquet', hive_partitioning=true);
    """)
    con.execute(f"""
        CREATE VIEW sen_filings AS SELECT * FROM read_parquet('{PARQUET_DIR}/senate/filings/**/*.parquet', hive_partitioning=true);
    """)
    con.execute(f"""
        CREATE VIEW sen_activities AS SELECT * FROM read_parquet('{PARQUET_DIR}/senate/activities/**/*.parquet', hive_partitioning=true);
    """)
    con.execute(f"""
        CREATE VIEW sen_lobbyists AS SELECT * FROM read_parquet('{PARQUET_DIR}/senate/lobbyists/**/*.parquet', hive_partitioning=true);
    """)
    con.execute(f"""
        CREATE VIEW sen_gov_entities AS SELECT * FROM read_parquet('{PARQUET_DIR}/senate/gov_entities/**/*.parquet', hive_partitioning=true);
    """)
    con.execute(f"""
        CREATE VIEW sen_foreign_entities AS SELECT * FROM read_parquet('{PARQUET_DIR}/senate/foreign_entities/**/*.parquet', hive_partitioning=true);
    """)
    con.execute(f"""
        CREATE VIEW sen_contrib_items AS SELECT * FROM read_parquet('{PARQUET_DIR}/senate/contrib_items/**/*.parquet', hive_partitioning=true);
    """)
    con.execute(f"""
        CREATE VIEW house_filings AS SELECT * FROM read_parquet('{PARQUET_DIR}/house/filings/*.parquet');
    """)
    con.execute(f"""
        CREATE VIEW house_lobbyists AS SELECT * FROM read_parquet('{PARQUET_DIR}/house/lobbyists/*.parquet');
    """)
    con.execute(f"""
        CREATE VIEW house_issues AS SELECT * FROM read_parquet('{PARQUET_DIR}/house/issues/*.parquet');
    """)
    con.execute(f"""
        CREATE VIEW house_agencies AS SELECT * FROM read_parquet('{PARQUET_DIR}/house/agencies/*.parquet');
    """)

    print("=== Counts by source ===")
    q(con, """
        SELECT 'press' AS src, COUNT(*) AS n, MIN(date) AS mn, MAX(date) AS mx FROM press
        UNION ALL SELECT 'sen_filings', COUNT(*), MIN(dt_posted)::DATE, MAX(dt_posted)::DATE FROM sen_filings
        UNION ALL SELECT 'sen_activities', COUNT(*), NULL, NULL FROM sen_activities
        UNION ALL SELECT 'sen_contrib_items', COUNT(*), MIN(contribution_date), MAX(contribution_date) FROM sen_contrib_items
        UNION ALL SELECT 'house_filings', COUNT(*), NULL, NULL FROM house_filings
        UNION ALL SELECT 'house_lobbyists', COUNT(*), NULL, NULL FROM house_lobbyists
        UNION ALL SELECT 'house_issues', COUNT(*), NULL, NULL FROM house_issues
    """)

    print("=== Top 15 Senate issue codes by activity count (2022-2026 Q1) ===")
    q(con, """
        SELECT issue_code, issue_display, COUNT(*) AS n_activities,
               COUNT(DISTINCT client_name) AS n_clients
        FROM sen_activities
        WHERE issue_code IS NOT NULL
        GROUP BY 1, 2 ORDER BY n_activities DESC
        LIMIT 15
    """)

    print("=== Top 15 lobbying spenders (Senate, sum of income across all filings) ===")
    # Note: many filings double-count. Use sen_filings only.
    q(con, """
        SELECT client_name, COUNT(*) AS n_filings, SUM(income) AS total_income,
               SUM(expenses) AS total_expenses
        FROM sen_filings
        WHERE client_name IS NOT NULL
        GROUP BY 1 ORDER BY total_income DESC NULLS LAST
        LIMIT 15
    """)

    print("=== Top 15 most active press release senders ===")
    q(con, """
        SELECT member_name, state, party, chamber, COUNT(*) AS n_releases
        FROM press
        GROUP BY 1, 2, 3, 4 ORDER BY n_releases DESC
        LIMIT 15
    """)

    print("=== Releases by party-chamber-year ===")
    q(con, """
        SELECT party, chamber, year, COUNT(*) AS n,
               COUNT(DISTINCT bioguide_id) AS n_members
        FROM press
        WHERE year IS NOT NULL
        GROUP BY 1, 2, 3 ORDER BY year, chamber, party
    """)

    print("=== Senate filings revenue by year (just LD-2 quarterlies) ===")
    q(con, """
        SELECT filing_year, COUNT(*) AS n,
               SUM(income) / 1e6 AS income_M,
               SUM(expenses) / 1e6 AS expenses_M
        FROM sen_filings
        WHERE filing_type LIKE 'Q%'
        GROUP BY filing_year ORDER BY filing_year
    """)

    print("=== Foreign-entity filings by country (top 20) ===")
    q(con, """
        SELECT foreign_entity_country, COUNT(*) AS n_filings,
               COUNT(DISTINCT registrant_name) AS n_registrants,
               COUNT(DISTINCT client_name) AS n_clients
        FROM sen_foreign_entities
        WHERE foreign_entity_country IS NOT NULL
        GROUP BY 1 ORDER BY n_filings DESC
        LIMIT 20
    """)

    print("=== Most-lobbied government entities ===")
    q(con, """
        SELECT gov_entity_name, COUNT(*) AS n_activities,
               COUNT(DISTINCT client_name) AS n_clients
        FROM sen_gov_entities
        WHERE gov_entity_name IS NOT NULL
        GROUP BY 1 ORDER BY n_activities DESC
        LIMIT 20
    """)

    print("=== Top contribution honorees (recipients) by total $ across all years ===")
    q(con, """
        SELECT honoree_name, COUNT(*) AS n_items, ROUND(SUM(amount), 0) AS total_dollars
        FROM sen_contrib_items
        WHERE honoree_name IS NOT NULL AND amount > 0
        GROUP BY 1 ORDER BY total_dollars DESC
        LIMIT 25
    """)

    print("=== House issues — sample of specific_issues text ===")
    q(con, """
        SELECT ali_code, description
        FROM house_issues
        WHERE description IS NOT NULL AND length(description) BETWEEN 50 AND 200
          AND year = 2025
        LIMIT 10
    """)

    print("=== Top covered_position patterns (Senate lobbyists) ===")
    q(con, """
        SELECT covered_position, COUNT(*) AS n
        FROM sen_lobbyists
        WHERE covered_position IS NOT NULL AND covered_position != ''
        GROUP BY 1 ORDER BY n DESC
        LIMIT 20
    """)


if __name__ == "__main__":
    main()

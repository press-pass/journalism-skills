"""Drill down on EDA leads.

1. The "STATE OF LOC" $180M spender — what is it?
2. Trump-Vance Inaugural contributors — who gave?
3. Mike Collins (R-GA) outlier — what's his messaging look like?
4. BVI / Cayman / Luxembourg — what kind of foreign entities are funneling through?
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb

PARQUET_DIR = Path(os.environ.get("PARQUET_DIR", "/parquet"))


def q(con, sql: str, n: int = 30) -> None:
    rows = con.execute(sql).fetchall()
    cols = [d[0] for d in con.description]
    print("  " + " | ".join(cols))
    print("  " + "-" * 80)
    for r in rows[:n]:
        print("  " + " | ".join(str(x)[:60] for x in r))
    print()


def main() -> None:
    con = duckdb.connect()
    con.execute("PRAGMA threads=8")
    con.execute("SET memory_limit='16GB'")
    for name, glob in [
        ("press", "press/**/*.parquet"),
        ("sen_filings", "senate/filings/**/*.parquet"),
        ("sen_activities", "senate/activities/**/*.parquet"),
        ("sen_lobbyists", "senate/lobbyists/**/*.parquet"),
        ("sen_gov_entities", "senate/gov_entities/**/*.parquet"),
        ("sen_foreign_entities", "senate/foreign_entities/**/*.parquet"),
        ("sen_contrib_items", "senate/contrib_items/**/*.parquet"),
        ("house_filings", "house/filings/*.parquet"),
        ("house_issues", "house/issues/*.parquet"),
    ]:
        con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{PARQUET_DIR}/{glob}', hive_partitioning=true)")

    print("=== STATE OF LOC ... what is it? ===")
    q(con, """
        SELECT filing_year, filing_period, filing_type, registrant_name, income, expenses, filing_uuid
        FROM sen_filings
        WHERE client_name LIKE 'STATE OF LOC%'
        ORDER BY filing_year, filing_period
    """)

    print("=== Other top-revenue suspicious clients (LD-203 contribution reports include $) ===")
    q(con, """
        SELECT client_name, COUNT(*) AS n, SUM(income) AS total_income, AVG(income) AS avg_income
        FROM sen_filings
        WHERE filing_type LIKE 'Q%' AND income IS NOT NULL
        GROUP BY 1
        ORDER BY total_income DESC
        LIMIT 25
    """)

    print("=== Trump-Vance Inaugural — who gave, when? ===")
    q(con, """
        SELECT contributor_name, payee_name, ROUND(amount,0) AS amount, contribution_date,
               contribution_type_display, registrant_name
        FROM sen_contrib_items
        WHERE LOWER(honoree_name) LIKE '%inaugural%'
           OR (LOWER(honoree_name) LIKE '%trump%' AND amount >= 100000)
        ORDER BY amount DESC
        LIMIT 30
    """)

    print("=== Inaugural / Trump committee contributions by registrant ===")
    q(con, """
        SELECT registrant_name, COUNT(*) AS n, ROUND(SUM(amount),0) AS total
        FROM sen_contrib_items
        WHERE LOWER(honoree_name) LIKE '%inaugural%' OR honoree_name = 'Trump Vance Inaugural Committee, Inc.'
        GROUP BY 1
        ORDER BY total DESC
        LIMIT 20
    """)

    print("=== Mike Collins (R-GA) outlier press output ===")
    q(con, """
        SELECT EXTRACT(YEAR FROM date) AS yr, EXTRACT(MONTH FROM date) AS mo, COUNT(*) AS n
        FROM press
        WHERE bioguide_id = (SELECT MIN(bioguide_id) FROM press WHERE member_name = 'Mike Collins' AND state = 'GA')
        GROUP BY 1,2 ORDER BY 1,2
        LIMIT 50
    """)

    print("=== Mike Collins compared to other House members (releases per month) ===")
    q(con, """
        WITH m AS (
            SELECT member_name, state, party, COUNT(*) AS n,
                   COUNT(DISTINCT (year || '-' || LPAD(month::text,2,'0'))) AS active_months
            FROM press
            WHERE chamber = 'House'
            GROUP BY 1, 2, 3
            HAVING COUNT(*) >= 100
        )
        SELECT member_name, state, party, n, active_months, ROUND(n::DOUBLE / active_months, 1) AS rel_per_month
        FROM m
        ORDER BY rel_per_month DESC
        LIMIT 25
    """)

    print("=== Sample of Mike Collins press release titles ===")
    q(con, """
        SELECT date, title
        FROM press
        WHERE member_name = 'Mike Collins' AND state = 'GA'
        ORDER BY date DESC
        LIMIT 20
    """)

    print("=== Offshore: BVI / Cayman / Luxembourg foreign entities and their issues ===")
    q(con, """
        SELECT fe.foreign_entity_country, fe.client_name, fe.foreign_entity_name,
               fe.foreign_ownership_pct, fe.foreign_contribution
        FROM sen_foreign_entities fe
        WHERE fe.foreign_entity_country IN
              ('Virgin Islands (British)', 'Cayman Islands', 'Luxembourg', 'Bermuda', 'Bahamas')
          AND fe.foreign_entity_name IS NOT NULL
        ORDER BY fe.foreign_contribution DESC NULLS LAST, fe.foreign_ownership_pct DESC NULLS LAST
        LIMIT 30
    """)

    print("=== Foreign entity countries trend by year ===")
    q(con, """
        SELECT filing_year, foreign_entity_country, COUNT(*) AS n
        FROM sen_foreign_entities
        WHERE foreign_entity_country IS NOT NULL
        GROUP BY 1, 2
        HAVING COUNT(*) >= 30
        ORDER BY filing_year, n DESC
        LIMIT 40
    """)


if __name__ == "__main__":
    main()

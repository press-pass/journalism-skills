"""Register named DuckDB views over the Parquet corpus.

Used by query.py, dbshell.py, and any other analysis script. The view names
match the documentation in `skills/lda-corpus-query/SKILL.md`.
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb

PARQUET_DIR = Path(os.environ.get("PARQUET_DIR", "/parquet"))

# (view_name, parquet_glob_relative_to_PARQUET_DIR, hive_partitioning)
VIEWS = [
    ("press", "press/**/*.parquet", True),
    ("sen_filings", "senate/filings/**/*.parquet", True),
    ("sen_activities", "senate/activities/**/*.parquet", True),
    ("sen_lobbyists", "senate/lobbyists/**/*.parquet", True),
    ("sen_gov_entities", "senate/gov_entities/**/*.parquet", True),
    ("sen_foreign_entities", "senate/foreign_entities/**/*.parquet", True),
    ("sen_contrib_items", "senate/contrib_items/**/*.parquet", True),
    ("sen_contrib_reports", "senate/contrib_reports/**/*.parquet", True),
    ("house_filings", "house/filings/*.parquet", False),
    ("house_lobbyists", "house/lobbyists/*.parquet", False),
    ("house_issues", "house/issues/*.parquet", False),
    ("house_agencies", "house/agencies/*.parquet", False),
    ("issue_codes", "senate/constants/lobbying_activity_issues.parquet", False),
    ("gov_entities_catalog", "senate/constants/government_entities.parquet", False),
    ("filing_types", "senate/constants/filing_types.parquet", False),
    ("countries_catalog", "senate/constants/countries.parquet", False),
    ("states_catalog", "senate/constants/states.parquet", False),
    ("contribution_item_types", "senate/constants/contribution_item_types.parquet", False),
    ("lobbyist_prefixes", "senate/constants/lobbyist_prefixes.parquet", False),
    ("lobbyist_suffixes", "senate/constants/lobbyist_suffixes.parquet", False),
]


def register(con: duckdb.DuckDBPyConnection) -> None:
    for name, glob, hive in VIEWS:
        path = PARQUET_DIR / glob
        # Detect whether the underlying files exist before creating the view
        if not list(PARQUET_DIR.glob(glob)):
            continue
        hive_clause = ", hive_partitioning=true" if hive else ""
        con.execute(
            f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{path}'{hive_clause})"
        )


def connect(memory_limit: str = "16GB", threads: int = 8) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"PRAGMA threads={threads}")
    con.execute(f"SET memory_limit='{memory_limit}'")
    con.execute("SET preserve_insertion_order=false")
    register(con)
    return con

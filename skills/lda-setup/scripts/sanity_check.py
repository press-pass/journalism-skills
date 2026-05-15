#!/usr/bin/env python3
"""Quick row-count smoke test on the investigation DB."""
import duckdb, os, sys
from pathlib import Path

DB = os.environ.get("LDA_DB_PATH") or str(
    Path(__file__).resolve().parents[3] / ".context" / "db" / "investigation.duckdb"
)
con = duckdb.connect(DB, read_only=True)
tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
expected = {
    "press", "press_member",
    "senate_filing", "senate_activity", "senate_lobbyist",
    "senate_govt_entity", "senate_foreign_entity",
    "senate_contrib_report", "senate_contrib_pac", "senate_contrib_item",
    "house_filing", "house_activity", "house_lobbyist", "house_foreign",
}
missing = expected - set(tables)
if missing:
    print(f"FAIL: missing tables {missing}", file=sys.stderr)
    sys.exit(1)
print(f"{'table':<24}  rows")
print("-" * 36)
for t in sorted(expected):
    n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    print(f"{t:<24}  {n:>10,}")
con.close()

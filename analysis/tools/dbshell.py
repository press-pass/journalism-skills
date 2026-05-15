"""Interactive DuckDB shell with all standard views pre-registered."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from views import VIEWS, connect  # type: ignore


def main() -> int:
    con = connect()
    print("Florence LDA corpus shell.")
    print("Registered views:")
    for name, _, _ in VIEWS:
        row = con.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{name}'").fetchone()
        if row and row[0]:
            print(f"  {name}")
    print()
    print("Hint: SELECT * FROM sen_filings LIMIT 3;  -- press q to exit pager")
    print("Use .quit to exit.")
    con.sql("INSTALL httpfs; LOAD httpfs;") if False else None
    # Hand off to DuckDB's built-in shell on the same db
    con.close()

    # Run duckdb CLI? We have duckdb python only. So do a poor-man's REPL.
    import duckdb as ddb
    con = connect()
    while True:
        try:
            line = input("florence> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        line = line.strip()
        if not line:
            continue
        if line in {".quit", "exit", "quit"}:
            return 0
        try:
            df = con.execute(line).df()
        except Exception as e:
            print(f"ERROR: {e}")
            continue
        if not df.empty:
            print(df.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""One-off SQL runner.

Usage:
    python analysis/tools/query.py --sql "SELECT COUNT(*) FROM press"
    python analysis/tools/query.py --file my_query.sql
    python analysis/tools/query.py --sql "..." --csv out.csv
    python analysis/tools/query.py --sql "..." --json out.json
    python analysis/tools/query.py --sql "..." --parquet out.parquet
    python analysis/tools/query.py --sql "..." --limit 100

Always wires views for the standard table names — see views.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

# Allow `python analysis/tools/query.py ...` from project root
sys.path.insert(0, str(Path(__file__).resolve().parent))
from views import connect  # type: ignore


def main() -> int:
    ap = argparse.ArgumentParser(description="Query the LDA + press Parquet corpus.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sql", help="Inline SQL to run")
    g.add_argument("--file", help="Path to a .sql file to run")
    ap.add_argument("--csv", help="Write result to a CSV file")
    ap.add_argument("--json", help="Write result to a JSON file (records)")
    ap.add_argument("--parquet", help="Write result to a Parquet file")
    ap.add_argument("--limit", type=int, default=50, help="Console row cap when no --csv/--json/--parquet")
    args = ap.parse_args()

    sql = args.sql or Path(args.file).read_text()
    con = connect()
    res = con.execute(sql)

    if args.csv:
        con.execute(f"COPY ({sql}) TO '{args.csv}' (HEADER, DELIMITER ',')")
        print(f"wrote {args.csv}", file=sys.stderr)
        return 0
    if args.parquet:
        con.execute(f"COPY ({sql}) TO '{args.parquet}' (FORMAT PARQUET)")
        print(f"wrote {args.parquet}", file=sys.stderr)
        return 0
    if args.json:
        df = res.df()
        Path(args.json).write_text(df.to_json(orient="records", date_format="iso"))
        print(f"wrote {args.json}", file=sys.stderr)
        return 0

    df = res.df()
    if args.limit and len(df) > args.limit:
        head = df.head(args.limit)
        print(head.to_string(index=False))
        print(f"... ({len(df) - args.limit:,} rows truncated)")
    else:
        print(df.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

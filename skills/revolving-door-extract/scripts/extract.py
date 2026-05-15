"""Extract revolving-door references from lobbyist 'covered_position' free text.

Output: parquet with one row per (lobbyist_id, member_bioguide_id, evidence_text).
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path
import polars as pl
import pyarrow as pa, pyarrow.parquet as pq


TITLE_RE = re.compile(
    r"\b(?:Sen(?:ator)?|Rep(?:resentative)?|Cong(?:ressman|resswoman|ressmember)?)\.?\s+"
    r"([A-Z][A-Za-z'\-\.]+(?:\s+[A-Z][A-Za-z'\-\.]+){0,2})",
    re.IGNORECASE,
)
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def member_lookup(press_parquet: str) -> dict[str, dict]:
    p = pl.read_parquet(press_parquet)
    members = (
        p.filter(pl.col("member_name").is_not_null())
         .select(["bioguide_id", "member_name", "party", "state", "chamber"])
         .unique()
    )
    rows = []
    for r in members.iter_rows(named=True):
        toks = [t for t in re.split(r"[\s.]+", r["member_name"] or "") if t]
        while toks and toks[-1].lower() in SUFFIX:
            toks.pop()
        if not toks:
            continue
        rows.append((toks[-1].lower(), r["bioguide_id"], r["member_name"], r["party"], r["state"], r["chamber"]))
    df = pl.DataFrame(rows, schema=["surname", "bioguide_id", "member_name", "party", "state", "chamber"], orient="row")
    counts = df.group_by("surname").agg(pl.col("bioguide_id").n_unique().alias("n_members"))
    unique_surnames = counts.filter(pl.col("n_members") == 1)["surname"].to_list()
    lookup = {}
    for r in df.filter(pl.col("surname").is_in(unique_surnames)).iter_rows(named=True):
        lookup[r["surname"]] = {
            "bioguide_id": r["bioguide_id"],
            "member_name": r["member_name"],
            "party": r["party"],
            "state": r["state"],
            "chamber": r["chamber"],
        }
    return lookup


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lobbyists_parquet", required=True)
    ap.add_argument("--press_parquet", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    lookup = member_lookup(args.press_parquet)
    surnames = set(lookup)
    print(f"unique-surname lookup size: {len(surnames)}", file=sys.stderr)

    lo = pl.read_parquet(args.lobbyists_parquet)
    lo = lo.filter(pl.col("covered_position").str.strip_chars() != "")
    lo = lo.filter(~pl.col("covered_position").str.to_lowercase().is_in(["see prior filing", "n/a", "none", "n.a."]))

    out_rows = []
    for row in lo.filter(pl.col("lobbyist_id").is_not_null()).iter_rows(named=True):
        cp = row["covered_position"] or ""
        for m in TITLE_RE.finditer(cp):
            grp = m.group(1).strip().rstrip(".,;:")
            toks = [t for t in re.split(r"[\s.]+", grp) if t]
            while toks and toks[-1].lower() in SUFFIX:
                toks.pop()
            if not toks:
                continue
            surname = toks[-1].lower()
            if surname in surnames:
                rec = lookup[surname]
                out_rows.append({
                    "lobbyist_id": row["lobbyist_id"],
                    "lobbyist_first": row.get("first_name"),
                    "lobbyist_last": row.get("last_name"),
                    "matched_surname": surname,
                    "bioguide_id": rec["bioguide_id"],
                    "member_name": rec["member_name"],
                    "party": rec["party"],
                    "state": rec["state"],
                    "chamber": rec["chamber"],
                    "evidence_text": cp,
                    "filing_uuid": row.get("filing_uuid"),
                })
    if not out_rows:
        print("no matches", file=sys.stderr)
        return
    df = pl.DataFrame(out_rows)
    # dedupe to unique (lobbyist_id, bioguide_id)
    print(f"raw matches: {df.height}", file=sys.stderr)
    df.write_parquet(args.out, compression="zstd")
    print(f"wrote {df.height} edges to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()

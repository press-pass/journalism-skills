#!/usr/bin/env python3
"""Extract specific bill-number mentions from lobbying activity descriptions
and from congressional press releases. Bridges the two corpora.

Tables produced (in investigation.duckdb):
  bill_mentions_lobby   — one row per (filing_uuid, act_idx, bill_id) match
  bill_mentions_press   — one row per (press_url, bill_id) match
  bill_index            — distinct bill_id with normalized variants

A bill_id is a normalized canonical token like "HR1234" / "S47" / "HRES23".
We accept these patterns:
  - "HR 1234", "H.R. 1234", "H Res 22", "H.RES.22"
  - "S 47", "S.J.Res. 5", "S.Res 17"
"""
import duckdb
import os
import re
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DB = Path(os.environ.get("LDA_DB_PATH", ROOT / ".context" / "db" / "investigation.duckdb"))

con = duckdb.connect(str(DB))

# Three precision-first patterns. We do NOT accept "S 2022" (year) as a bill.
# A bill must look like:
#   - "H.R. 5376" / "H. R. 5376" / "H.R.5376" (House bill)
#   - "S. 47" / "S.47" (Senate bill)
#   - "H. Res. 8" / "H.Res.8" / "HRes 8" (House resolution)
#   - "S. Res. 12" / "S.Res.12"
#   - "H.J. Res. 5" / "S.J. Res. 5"
#   - "H. Con. Res. 23" / "S. Con. Res. 23"
#   - bare "HR 1234" but ONLY when no period-less variant nearby
# Critical: the chamber letter is followed by a dot (or a recognized kind word).

# Pattern A: chamber-with-period + optional kind + number
PATTERN_A = re.compile(
    r"""
    \b
    (?P<chamber>H|S)\.\s*         # H. or S. (period REQUIRED)
    (?:(?P<kind>J\.?\s*Res|Con\.?\s*Res|Res|J\.?\s*R|Con\.?\s*R|R)\.?)?\s*
    (?P<num>\d{1,5})
    \b
    """,
    re.VERBOSE | re.IGNORECASE,
)
# Pattern B: chamber-no-period + EXPLICIT kind word (HRes, SRes, HJRes, SJRes, HCONRes, SCONRes, HR, S)
PATTERN_B = re.compile(
    r"""
    \b
    (?P<chamber>H|S)
    (?P<kind>J\s*Res|Con\s*Res|Res|J\s*R|Con\s*R|R)
    \.?\s*
    (?P<num>\d{1,5})
    \b
    """,
    re.VERBOSE | re.IGNORECASE,
)
# Pattern C: "Bill: HR 1234" or "House bill 1234" — kept narrow to avoid year-collisions
PATTERN_C = re.compile(
    r"""
    \b(?:House|Senate)\s+(?P<chamber>Bill|Joint\s+Resolution|Resolution|Concurrent\s+Resolution|Res)?\s*
    (?P<num>\d{1,5})\b
    """,
    re.VERBOSE | re.IGNORECASE,
)  # Pattern C is too noisy; not currently used.


def normalize(chamber, kind, num):
    chamber = chamber.upper()
    if kind:
        k = re.sub(r"[\s.]", "", kind).upper()
        # H.R. → House bill = "HR"; "Res" → Resolution; "JRES" → JointResolution; "CONRES" → ConRes
        if k == "R":
            kind_n = "R"  # House BILL  → HR{num}, Senate BILL → SR{num}? No, "SR" is unusual.
        elif k == "RES":
            kind_n = "RES"
        elif k in {"JR", "JRES"}:
            kind_n = "JRES"
        elif k in {"CONR", "CONRES"}:
            kind_n = "CONRES"
        else:
            kind_n = k
    else:
        # No kind word: H. 1234 doesn't exist as a real form. S. 1234 = Senate Bill.
        if chamber == "S":
            return f"S{int(num)}"
        # H without kind is invalid — drop
        return None

    if chamber == "H":
        if kind_n == "R":
            return f"HR{int(num)}"
        return f"H{kind_n}{int(num)}"
    if chamber == "S":
        if kind_n == "R":
            # "S.R." is rare — treat as plain Senate bill
            return f"S{int(num)}"
        return f"S{kind_n}{int(num)}"
    return None


def extract(text):
    if not text:
        return set()
    found = set()
    for rx in (PATTERN_A, PATTERN_B):
        for m in rx.finditer(text):
            c = m.group("chamber")
            k = m.group("kind")
            n = m.group("num")
            try:
                if int(n) < 1 or int(n) > 9999:
                    continue
            except ValueError:
                continue
            bill_id = normalize(c, k, n)
            if bill_id:
                found.add(bill_id)
    return found


def main():
    # 1) Lobbying activities → bills
    print("Scanning senate_activity descriptions...", file=sys.stderr)
    df = con.execute("""
        SELECT filing_uuid, act_idx, general_issue_code, description
        FROM senate_activity
        WHERE description IS NOT NULL AND length(description) > 10
    """).fetch_df()
    print(f"  {len(df):,} activity descriptions", file=sys.stderr)
    rows = []
    for r in df.itertuples(index=False):
        bills = extract(r.description)
        for b in bills:
            rows.append({
                "filing_uuid": r.filing_uuid,
                "act_idx": r.act_idx,
                "general_issue_code": r.general_issue_code,
                "bill_id": b,
            })
    print(f"  lobbying bill-mentions: {len(rows):,}", file=sys.stderr)
    bm_lobby = pd.DataFrame(rows)
    con.register("_bml", bm_lobby)
    con.execute("DROP TABLE IF EXISTS bill_mentions_lobby")
    con.execute("CREATE TABLE bill_mentions_lobby AS SELECT * FROM _bml")
    con.unregister("_bml")

    # 2) House activities → bills (description column)
    print("Scanning house_activity descriptions...", file=sys.stderr)
    df = con.execute("""
        SELECT filing_id, act_idx, issue_code, description
        FROM house_activity
        WHERE description IS NOT NULL AND length(description) > 10
    """).fetch_df()
    print(f"  {len(df):,} house activity descriptions", file=sys.stderr)
    rows = []
    for r in df.itertuples(index=False):
        for b in extract(r.description):
            rows.append({
                "filing_id": r.filing_id,
                "act_idx": r.act_idx,
                "issue_code": r.issue_code,
                "bill_id": b,
            })
    print(f"  house lobbying bill-mentions: {len(rows):,}", file=sys.stderr)
    bm_house = pd.DataFrame(rows)
    con.register("_bmh", bm_house)
    con.execute("DROP TABLE IF EXISTS bill_mentions_lobby_house")
    con.execute("CREATE TABLE bill_mentions_lobby_house AS SELECT * FROM _bmh")
    con.unregister("_bmh")

    # 3) Press releases → bills (scan body, dedupe per release)
    print("Scanning press releases...", file=sys.stderr)
    df = con.execute("""
        SELECT url, bioguide_id, member_name, party, chamber, release_date, title, body
        FROM press
        WHERE body IS NOT NULL
    """).fetch_df()
    print(f"  {len(df):,} press releases", file=sys.stderr)
    rows = []
    for r in df.itertuples(index=False):
        bills = extract(r.title or "") | extract(r.body or "")
        for b in bills:
            rows.append({
                "url": r.url,
                "bioguide_id": r.bioguide_id,
                "member_name": r.member_name,
                "party": r.party,
                "chamber": r.chamber,
                "release_date": r.release_date,
                "bill_id": b,
            })
    print(f"  press bill-mentions: {len(rows):,}", file=sys.stderr)
    bm_press = pd.DataFrame(rows)
    con.register("_bmp", bm_press)
    con.execute("DROP TABLE IF EXISTS bill_mentions_press")
    con.execute("CREATE TABLE bill_mentions_press AS SELECT * FROM _bmp")
    con.unregister("_bmp")

    # 4) Sanity: top bills by # press releases and by # lobby filings
    print("\nTop 10 bills by lobby filings:", file=sys.stderr)
    for r in con.execute("""
        SELECT bill_id, COUNT(DISTINCT filing_uuid) AS senate_lobby_filings,
               (SELECT COUNT(DISTINCT filing_id) FROM bill_mentions_lobby_house h WHERE h.bill_id = l.bill_id) AS house_lobby_filings
        FROM bill_mentions_lobby l
        GROUP BY 1
        ORDER BY senate_lobby_filings DESC
        LIMIT 10
    """).fetchall():
        print(f"  {r[0]:<12} senate={r[1]:<5} house={r[2]}", file=sys.stderr)

    print("\nTop 10 bills by press releases:", file=sys.stderr)
    for r in con.execute("""
        SELECT bill_id, COUNT(*) AS press_mentions, COUNT(DISTINCT bioguide_id) AS distinct_members
        FROM bill_mentions_press
        GROUP BY 1
        ORDER BY press_mentions DESC
        LIMIT 10
    """).fetchall():
        print(f"  {r[0]:<12} mentions={r[1]:<5} members={r[2]}", file=sys.stderr)

    con.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Extract bill numbers from lobbying descriptions and press releases."""
from __future__ import annotations
import argparse
import re
import time
import duckdb


# Patterns for U.S. bill citations
BILL_RE = re.compile(
    r"(?P<kind>"
    r"H\s*\.?\s*R\s*\.?|"            # H.R., HR, H R
    r"S\s*\.?(?!\w)|"                # S. or S followed by non-word (avoid eg S.S.)
    r"H\s*\.?\s*J\s*\.?\s*Res\s*\.?|" # H.J.Res.
    r"S\s*\.?\s*J\s*\.?\s*Res\s*\.?|"
    r"H\s*\.?\s*Res\s*\.?|"
    r"S\s*\.?\s*Res\s*\.?|"
    r"H\s*\.?\s*Con\s*\.?\s*Res\s*\.?|"
    r"S\s*\.?\s*Con\s*\.?\s*Res\s*\.?"
    r")"
    r"\s*(?P<num>\d{1,5})"
    r"(?!\d)",
    re.IGNORECASE,
)
PUBLAW_RE = re.compile(r"P\s*\.?\s*L\s*\.?|Pub\s*\.?\s*L\s*\.?")  # placeholder
PUBLIC_LAW_RE = re.compile(r"(?:Pub\s*\.?\s*L|P\s*\.?\s*L)\s*\.?\s*(?:No\.?)?\s*(\d{2,3})\s*[-–]\s*(\d{1,4})", re.IGNORECASE)


def _norm_kind(s: str) -> str:
    t = re.sub(r"[\s.]+", "", s).upper()
    # canonical: HR, S, HJRES, SJRES, HRES, SRES, HCONRES, SCONRES
    mapping = {
        "HR": "HR",
        "S": "S",
        "HJRES": "HJRES", "HJR": "HJRES",
        "SJRES": "SJRES", "SJR": "SJRES",
        "HRES": "HRES",
        "SRES": "SRES",
        "HCONRES": "HCONRES", "HCONR": "HCONRES",
        "SCONRES": "SCONRES", "SCONR": "SCONRES",
    }
    return mapping.get(t, t)


def _congress_for_year(y: int) -> int:
    # Each Congress runs two years; the 118th was 2023-2024, 119th is 2025-2026.
    if y is None:
        return None
    base = (y - 2023) // 2
    return 118 + base


def _bill_id(kind: str, num: str, year: int) -> str:
    cong = _congress_for_year(year)
    return f"{cong}-{kind}-{num}" if cong else f"unk-{kind}-{num}"


def _context(text: str, start: int, end: int, span: int = 60) -> str:
    a, b = max(0, start - span), min(len(text), end + span)
    return re.sub(r"\s+", " ", text[a:b]).strip()


def extract(text: str, year: int):
    if not text:
        return []
    seen = {}
    for m in BILL_RE.finditer(text):
        kind = _norm_kind(m.group("kind"))
        num = m.group("num")
        if kind in {"S"} and int(num) > 9999:
            continue
        bid = _bill_id(kind, num, year)
        ctx = _context(text, m.start(), m.end())
        if bid not in seen:
            seen[bid] = {"kind": kind, "num": num, "context": ctx, "occurrences": 1}
        else:
            seen[bid]["occurrences"] += 1
    for m in PUBLIC_LAW_RE.finditer(text):
        cong, sec = m.group(1), m.group(2)
        bid = f"PL-{cong}-{sec}"
        ctx = _context(text, m.start(), m.end())
        if bid not in seen:
            seen[bid] = {"kind": "PL", "num": f"{cong}-{sec}", "context": ctx, "occurrences": 1}
        else:
            seen[bid]["occurrences"] += 1
    return [(bid, v["kind"], v["num"], v["context"], v["occurrences"]) for bid, v in seen.items()]


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()
    con = duckdb.connect(args.db)

    log("Recreating bill_mentions_* tables")
    con.execute("""
        DROP TABLE IF EXISTS bill_mentions_lobbying;
        CREATE TABLE bill_mentions_lobbying (
            source VARCHAR,
            filing_uuid VARCHAR,
            house_file VARCHAR,
            filing_year INTEGER,
            bill_id VARCHAR,
            bill_kind VARCHAR,
            bill_number VARCHAR,
            context VARCHAR,
            occurrences INTEGER
        );
        DROP TABLE IF EXISTS bill_mentions_press;
        CREATE TABLE bill_mentions_press (
            url VARCHAR,
            bioguide_id VARCHAR,
            date DATE,
            filing_year INTEGER,
            bill_id VARCHAR,
            bill_kind VARCHAR,
            bill_number VARCHAR,
            context VARCHAR,
            occurrences INTEGER
        );
    """)

    log("Scanning senate_activities")
    rows = con.execute("""
        SELECT a.filing_uuid, a.description, f.filing_year
        FROM senate_activities a
        JOIN senate_filings f USING (filing_uuid)
        WHERE a.description IS NOT NULL AND length(a.description) > 0
    """).fetchall()
    batch = []
    for fuid, desc, yr in rows:
        for bid, kind, num, ctx, occ in extract(desc, yr):
            batch.append(("senate", fuid, None, yr, bid, kind, num, ctx, occ))
        if len(batch) >= 50000:
            con.executemany("INSERT INTO bill_mentions_lobbying VALUES (?,?,?,?,?,?,?,?,?)", batch)
            batch = []
    if batch:
        con.executemany("INSERT INTO bill_mentions_lobbying VALUES (?,?,?,?,?,?,?,?,?)", batch)
    log(f"  senate rows scanned: {len(rows):,}")

    log("Scanning house_activities")
    rows = con.execute("""
        SELECT a.house_file, a.description, h.filing_year
        FROM house_activities a
        JOIN house_filings h USING (house_file)
        WHERE a.description IS NOT NULL AND length(a.description) > 0
    """).fetchall()
    batch = []
    for hf, desc, yr in rows:
        for bid, kind, num, ctx, occ in extract(desc, yr):
            batch.append(("house", None, hf, yr, bid, kind, num, ctx, occ))
        if len(batch) >= 50000:
            con.executemany("INSERT INTO bill_mentions_lobbying VALUES (?,?,?,?,?,?,?,?,?)", batch)
            batch = []
    if batch:
        con.executemany("INSERT INTO bill_mentions_lobbying VALUES (?,?,?,?,?,?,?,?,?)", batch)
    log(f"  house rows scanned: {len(rows):,}")

    log("Scanning press_releases (streaming)")
    cur = con.execute("""
        SELECT url, bioguide_id, date, text, EXTRACT(YEAR FROM date)::INTEGER AS yr
        FROM press_releases WHERE text IS NOT NULL AND length(text) > 50
    """)
    total = 0
    batch = []
    while True:
        rows = cur.fetchmany(2000)
        if not rows:
            break
        for url, bio, dt, txt, yr in rows:
            mentions = extract(txt, yr or 0)
            for bid, kind, num, ctx, occ in mentions:
                batch.append((url, bio, dt, yr, bid, kind, num, ctx, occ))
        if len(batch) >= 50000:
            con.executemany("INSERT INTO bill_mentions_press VALUES (?,?,?,?,?,?,?,?,?)", batch)
            total += len(batch)
            batch = []
            log(f"  press: {total:,} mentions so far")
    if batch:
        con.executemany("INSERT INTO bill_mentions_press VALUES (?,?,?,?,?,?,?,?,?)", batch)
        total += len(batch)

    log("Indexes")
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_bmlobb_bill ON bill_mentions_lobbying(bill_id);
        CREATE INDEX IF NOT EXISTS idx_bmpress_bill ON bill_mentions_press(bill_id);
        CREATE INDEX IF NOT EXISTS idx_bmpress_date ON bill_mentions_press(date);
        ANALYZE;
    """)
    log(f"Done. press mentions={total:,}")


if __name__ == "__main__":
    main()
